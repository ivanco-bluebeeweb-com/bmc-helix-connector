"""Chat functions for BMC Helix Connector."""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import bmc_helix_client as bc
from app import chat
from schemas import (
    AuditHealthParams, BMCHelixConnection, ChangeRequest, ChangeRequestList,
    ConfigItem, ConfigItemList, ConnectBMCHelixParams, ConnectionList,
    ConnectionRefParams, CreateChangeParams, CreateIncidentParams,
    CreateProblemParams, CreateWorkOrderParams, DeleteResult,
    DisconnectBMCHelixParams, EntryIdParams, GenericCreateParams,
    GenericEntry, GenericEntryList, GenericEntryParams, GenericFormParams,
    GenericUpdateParams, HealthAudit, Incident, IncidentList,
    KnowledgeArticle, KnowledgeArticleList, ListChangesParams, ListCIsParams,
    ListIncidentsParams, ListKnowledgeParams, ListProblemsParams,
    ListWorkOrdersParams, NoParams, Problem, ProblemList, UpdateChangeParams,
    UpdateIncidentParams, UpdateProblemParams, UpdateWorkOrderParams,
    WorkOrder, WorkOrderList,
)

_SECRET_NAME = "bmc_helix_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


def _connection_entity(connection: dict) -> BMCHelixConnection:
    label = connection.get("label") or connection.get("host", "")
    return BMCHelixConnection(
        id=connection.get("id", ""), title=label, label=label,
        host=connection.get("host", ""), connected=True,
    )


def _find_connection(connections: list[dict], connection_id: str) -> dict | None:
    if not connections:
        return None
    if not connection_id:
        return connections[0]
    for c in connections:
        if c.get("id") == connection_id:
            return c
    return None


async def _resolve_client(ctx, connection_id: str) -> tuple[dict, bc.BMCHelixClient]:
    connections = await _load_connections(ctx)
    connection = _find_connection(connections, connection_id)
    if not connection:
        raise bc.BMCHelixError("No BMC Helix instance connected yet. Use connect_bmc_helix first.")
    client = bc.BMCHelixClient(connection["host"], connection["username"], connection["password"])
    return connection, client


@chat.function("connect_bmc_helix", "Connect a BMC Helix ITSM (Remedy AR System) instance via JWT login, after validating connectivity.", action_type="write", chain_callable=True, data_model=BMCHelixConnection, event="bmc-helix-connector.connect_bmc_helix", effects=["bmc_helix.provider.connected"])
async def connect_bmc_helix(ctx, params: ConnectBMCHelixParams) -> ActionResult:
    """Imperal action: connect_bmc_helix."""
    try:
        client = bc.BMCHelixClient(params.host, params.username, params.password)
        await client.ping()
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_CONNECT_FAILED", retryable=exc.retryable)
    connections = await _load_connections(ctx)
    new_id = str(uuid.uuid4())
    record = {"id": new_id, "label": params.label, "host": client.base_url, "username": params.username, "password": params.password}
    connections.append(record)
    await _save_connections(ctx, connections)
    return ActionResult.success(data=_connection_entity(record), summary=f"Connected to {client.base_url}.")


@chat.function("disconnect_bmc_helix", "Disconnect a BMC Helix instance: deletes only the saved credentials. Nothing in BMC Helix itself is changed.", action_type="write", chain_callable=True, data_model=DeleteResult, event="bmc-helix-connector.disconnect_bmc_helix", effects=["bmc_helix.provider.disconnected"])
async def disconnect_bmc_helix(ctx, params: DisconnectBMCHelixParams) -> ActionResult:
    """Imperal action: disconnect_bmc_helix."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error("Connection not found.", code="BMC_HELIX_CONNECTION_NOT_FOUND")
    await _save_connections(ctx, remaining)
    return ActionResult.success(data=DeleteResult(id=params.connection_id), summary="Disconnected.")


@chat.function("list_connections", "List the connected BMC Helix instances.", action_type="read", chain_callable=True, data_model=ConnectionList, event="bmc-helix-connector.list_connections")
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """Imperal action: list_connections."""
    connections = await _load_connections(ctx)
    return ActionResult.success(data=ConnectionList(connections=[_connection_entity(c) for c in connections]))


def _to_incident(item: dict) -> Incident:
    return Incident(
        entry_id=str(item.get("Incident Number", item.get("entry_id", ""))),
        title=str(item.get("Incident Number", "")),
        description=item.get("Description", ""), status=item.get("Status", ""),
        priority=item.get("Priority", ""), raw=item,
    )


@chat.function("list_incidents", "List incidents on the connected BMC Helix instance, optionally filtered by status.", action_type="read", chain_callable=True, data_model=IncidentList, event="bmc-helix-connector.list_incidents")
async def list_incidents(ctx, params: ListIncidentsParams) -> ActionResult:
    """Imperal action: list_incidents."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_incidents(status=params.status, limit=params.limit)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_LIST_INCIDENTS_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=IncidentList(incidents=[_to_incident(i) for i in items]))


@chat.function("get_incident", "Read one incident in full by entry id.", action_type="read", chain_callable=True, data_model=Incident, event="bmc-helix-connector.get_incident")
async def get_incident(ctx, params: EntryIdParams) -> ActionResult:
    """Imperal action: get_incident."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.get_entry("HPD:Help Desk", params.entry_id)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_GET_INCIDENT_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_incident(item))


@chat.function("create_incident", "Create a new incident.", action_type="write", chain_callable=True, data_model=Incident, event="bmc-helix-connector.create_incident", effects=["create:incident"])
async def create_incident(ctx, params: CreateIncidentParams) -> ActionResult:
    """Imperal action: create_incident."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_incident(params.values)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_CREATE_INCIDENT_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_incident(item), summary="Incident created.")


@chat.function("update_incident", "Update selected fields of an existing incident (state, priority). Only given fields change.", action_type="write", chain_callable=True, data_model=Incident, event="bmc-helix-connector.update_incident", effects=["update:incident"])
async def update_incident(ctx, params: UpdateIncidentParams) -> ActionResult:
    """Imperal action: update_incident."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        await client.update_incident(params.entry_id, params.values)
        item = await client.get_entry("HPD:Help Desk", params.entry_id)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_UPDATE_INCIDENT_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_incident(item), summary="Incident updated.")


def _to_problem(item: dict) -> Problem:
    return Problem(
        entry_id=str(item.get("Investigation ID", item.get("entry_id", ""))),
        title=str(item.get("Investigation ID", "")),
        description=item.get("Description", ""), status=item.get("Status", ""), raw=item,
    )


@chat.function("list_problems", "List problems on the connected BMC Helix instance, optionally filtered by status.", action_type="read", chain_callable=True, data_model=ProblemList, event="bmc-helix-connector.list_problems")
async def list_problems(ctx, params: ListProblemsParams) -> ActionResult:
    """Imperal action: list_problems."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_problems(status=params.status, limit=params.limit)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_LIST_PROBLEMS_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=ProblemList(problems=[_to_problem(i) for i in items]))


@chat.function("create_problem", "Create a new problem record.", action_type="write", chain_callable=True, data_model=Problem, event="bmc-helix-connector.create_problem", effects=["create:problem"])
async def create_problem(ctx, params: CreateProblemParams) -> ActionResult:
    """Imperal action: create_problem."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_problem(params.values)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_CREATE_PROBLEM_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_problem(item), summary="Problem created.")


@chat.function("update_problem", "Update selected fields of an existing problem. Only given fields change.", action_type="write", chain_callable=True, data_model=Problem, event="bmc-helix-connector.update_problem", effects=["update:problem"])
async def update_problem(ctx, params: UpdateProblemParams) -> ActionResult:
    """Imperal action: update_problem."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        await client.update_problem(params.entry_id, params.values)
        item = await client.get_entry("PBM:Problem Investigation", params.entry_id)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_UPDATE_PROBLEM_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_problem(item), summary="Problem updated.")


def _to_change(item: dict) -> ChangeRequest:
    return ChangeRequest(
        entry_id=str(item.get("Infrastructure Change ID", item.get("entry_id", ""))),
        title=str(item.get("Infrastructure Change ID", "")),
        description=item.get("Description", ""), status=item.get("Status", ""), raw=item,
    )


@chat.function("list_change_requests", "List change requests in the connected BMC Helix instance, optionally filtered by state.", action_type="read", chain_callable=True, data_model=ChangeRequestList, event="bmc-helix-connector.list_change_requests")
async def list_change_requests(ctx, params: ListChangesParams) -> ActionResult:
    """Imperal action: list_change_requests."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_changes(status=params.status, limit=params.limit)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_LIST_CHANGES_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=ChangeRequestList(changes=[_to_change(i) for i in items]))


@chat.function("create_change_request", "Create a new change request.", action_type="write", chain_callable=True, data_model=ChangeRequest, event="bmc-helix-connector.create_change_request", effects=["create:change"])
async def create_change_request(ctx, params: CreateChangeParams) -> ActionResult:
    """Imperal action: create_change_request."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_change(params.values)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_CREATE_CHANGE_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_change(item), summary="Change request created.")


@chat.function("update_change_request", "Update selected fields of an existing change request (state, approval). Only given fields change.", action_type="write", chain_callable=True, data_model=ChangeRequest, event="bmc-helix-connector.update_change_request", effects=["update:change"])
async def update_change_request(ctx, params: UpdateChangeParams) -> ActionResult:
    """Imperal action: update_change_request."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        await client.update_change(params.entry_id, params.values)
        item = await client.get_entry("CHG:Infrastructure Change", params.entry_id)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_UPDATE_CHANGE_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_change(item), summary="Change request updated.")


def _to_work_order(item: dict) -> WorkOrder:
    return WorkOrder(
        entry_id=str(item.get("Work Order ID", item.get("entry_id", ""))),
        title=str(item.get("Work Order ID", "")),
        description=item.get("Description", ""), status=item.get("Status", ""), raw=item,
    )


@chat.function("list_work_orders", "List work orders on the connected BMC Helix instance, optionally filtered by status.", action_type="read", chain_callable=True, data_model=WorkOrderList, event="bmc-helix-connector.list_work_orders")
async def list_work_orders(ctx, params: ListWorkOrdersParams) -> ActionResult:
    """Imperal action: list_work_orders."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_work_orders(status=params.status, limit=params.limit)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_LIST_WORK_ORDERS_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=WorkOrderList(work_orders=[_to_work_order(i) for i in items]))


@chat.function("create_work_order", "Create a new Service Catalog work order.", action_type="write", chain_callable=True, data_model=WorkOrder, event="bmc-helix-connector.create_work_order", effects=["create:work_order"])
async def create_work_order(ctx, params: CreateWorkOrderParams) -> ActionResult:
    """Imperal action: create_work_order."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_work_order(params.values)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_CREATE_WORK_ORDER_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_work_order(item), summary="Work order created.")


@chat.function("update_work_order", "Update selected fields of an existing work order. Only given fields change.", action_type="write", chain_callable=True, data_model=WorkOrder, event="bmc-helix-connector.update_work_order", effects=["update:work_order"])
async def update_work_order(ctx, params: UpdateWorkOrderParams) -> ActionResult:
    """Imperal action: update_work_order."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        await client.update_work_order(params.entry_id, params.values)
        item = await client.get_entry("WOI:WorkOrder", params.entry_id)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_UPDATE_WORK_ORDER_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_to_work_order(item), summary="Work order updated.")


@chat.function("list_knowledge_articles", "List Knowledge articles in the connected BMC Helix instance.", action_type="read", chain_callable=True, data_model=KnowledgeArticleList, event="bmc-helix-connector.list_knowledge_articles")
async def list_knowledge_articles(ctx, params: ListKnowledgeParams) -> ActionResult:
    """Imperal action: list_knowledge_articles."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_knowledge_articles(limit=params.limit)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_LIST_KNOWLEDGE_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=KnowledgeArticleList(articles=[
        KnowledgeArticle(entry_id=str(i.get("entry_id", i.get("Article ID", ""))), title=i.get("Title", str(i.get("Article ID", ""))), raw=i) for i in items
    ]))


@chat.function("list_cmdb_cis", "List Configuration Items (CIs) in the CMDB, optionally filtered by class.", action_type="read", chain_callable=True, data_model=ConfigItemList, event="bmc-helix-connector.list_cmdb_cis")
async def list_cmdb_cis(ctx, params: ListCIsParams) -> ActionResult:
    """Imperal action: list_cmdb_cis."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_cis(ci_class=params.ci_class, limit=params.limit)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_LIST_CIS_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=ConfigItemList(items=[
        ConfigItem(entry_id=str(i.get("entry_id", i.get("InstanceId", ""))), title=i.get("Name", str(i.get("InstanceId", ""))), ci_class=i.get("ClassId", params.ci_class), status=i.get("Status", ""), raw=i) for i in items
    ]))


@chat.function("list_table", "List records from any AR System form by name -- a generic passthrough for forms not covered by typed wrappers, e.g. custom Helix modules.", action_type="read", chain_callable=True, data_model=GenericEntryList, event="bmc-helix-connector.list_table")
async def list_table(ctx, params: GenericFormParams) -> ActionResult:
    """Imperal action: list_table."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_entries(params.form_name, qualification=params.qualification, limit=params.limit)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_LIST_TABLE_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=GenericEntryList(entries=[
        GenericEntry(entry_id=str(i.get("entry_id", "")), title=str(i.get("entry_id", "")), raw=i) for i in items
    ]))


@chat.function("get_record", "Read one record from any AR System form by entry id.", action_type="read", chain_callable=True, data_model=GenericEntry, event="bmc-helix-connector.get_record")
async def get_record(ctx, params: GenericEntryParams) -> ActionResult:
    """Imperal action: get_record."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.get_entry(params.form_name, params.entry_id)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_GET_RECORD_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=GenericEntry(entry_id=params.entry_id, title=params.entry_id, raw=item))


@chat.function("create_record", "Create a new record on any AR System form -- a generic passthrough for forms not covered by typed wrappers.", action_type="write", chain_callable=True, data_model=GenericEntry, event="bmc-helix-connector.create_record", effects=["create:record"])
async def create_record(ctx, params: GenericCreateParams) -> ActionResult:
    """Imperal action: create_record."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_entry(params.form_name, params.values)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_CREATE_RECORD_FAILED", retryable=exc.retryable)
    entry_id = str(item.get("entry_id", ""))
    return ActionResult.success(data=GenericEntry(entry_id=entry_id, title=entry_id, raw=item), summary="Record created.")


@chat.function("update_record", "Update selected fields of an existing record on any AR System form. Only given fields change.", action_type="write", chain_callable=True, data_model=GenericEntry, event="bmc-helix-connector.update_record", effects=["update:record"])
async def update_record(ctx, params: GenericUpdateParams) -> ActionResult:
    """Imperal action: update_record."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        await client.update_entry(params.form_name, params.entry_id, params.values)
        item = await client.get_entry(params.form_name, params.entry_id)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_UPDATE_RECORD_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=GenericEntry(entry_id=params.entry_id, title=params.entry_id, raw=item), summary="Record updated.")


@chat.function("delete_record", "Permanently delete a record from any AR System form by entry id. Cannot be undone.", action_type="write", chain_callable=True, data_model=DeleteResult, event="bmc-helix-connector.delete_record", effects=["delete:record"])
async def delete_record(ctx, params: GenericEntryParams) -> ActionResult:
    """Imperal action: delete_record."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        await client.delete_entry(params.form_name, params.entry_id)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_DELETE_RECORD_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=DeleteResult(id=params.entry_id), summary="Record deleted.")


@chat.function("audit_instance_health", "Build one aggregated health report across the connected BMC Helix instance: open incidents/problems/changes/work orders.", action_type="read", chain_callable=True, data_model=HealthAudit, event="bmc-helix-connector.audit_instance_health")
async def audit_instance_health(ctx, params: AuditHealthParams) -> ActionResult:
    """Imperal action: audit_instance_health."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        incidents = await client.list_incidents(limit=100)
        problems = await client.list_problems(limit=100)
        changes = await client.list_changes(limit=100)
        work_orders = await client.list_work_orders(limit=100)
    except bc.BMCHelixError as exc:
        return ActionResult.error(str(exc), code="BMC_HELIX_AUDIT_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=HealthAudit(
        open_incident_count=len(incidents), open_problem_count=len(problems),
        open_change_count=len(changes), open_work_order_count=len(work_orders),
    ), summary=f"{len(incidents)} incident(s), {len(problems)} problem(s), {len(changes)} change(s), {len(work_orders)} work order(s) open.")
