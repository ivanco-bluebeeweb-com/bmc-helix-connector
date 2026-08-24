"""Pydantic input contracts and SDL result entities for BMC Helix Connector."""
from __future__ import annotations

from imperal_sdk import sdl
from pydantic import BaseModel, Field


class NoParams(BaseModel):
    pass


class ConnectionRefParams(BaseModel):
    connection_id: str = Field("", description="Optional saved BMC Helix connection ID. Omit to use the first connected instance.")


class ConnectBMCHelixParams(BaseModel):
    label: str = Field("", description="Friendly instance label, e.g. 'Acme Production'.")
    host: str = Field(..., description="AR REST host, e.g. 'https://acme-restapi.onbmc.com' (SaaS) or 'https://host:port' (on-prem).")
    username: str = Field(..., description="AR System username.")
    password: str = Field(..., description="AR System password.")


class DisconnectBMCHelixParams(ConnectionRefParams):
    connection_id: str = Field(..., description="Saved BMC Helix connection ID to remove from Imperal.")


class EntryIdParams(ConnectionRefParams):
    entry_id: str = Field(..., description="AR System entry id (the form's primary key value, e.g. Incident Number).")


class ListIncidentsParams(ConnectionRefParams):
    status: str = Field("", description="Optional status filter, e.g. 'New', 'In Progress', 'Resolved'.")
    limit: int = Field(50, description="Max records to return.")


class CreateIncidentParams(ConnectionRefParams):
    values: dict = Field(..., description="AR System field name/value pairs for the new incident, e.g. {'Description': '...', 'Impact': '4-Minor/Localized'}.")


class UpdateIncidentParams(EntryIdParams):
    values: dict = Field(..., description="AR System field name/value pairs to update, e.g. {'Status': 'Resolved'}.")


class ListProblemsParams(ConnectionRefParams):
    status: str = Field("", description="Optional status filter.")
    limit: int = Field(50, description="Max records to return.")


class CreateProblemParams(ConnectionRefParams):
    values: dict = Field(..., description="AR System field name/value pairs for the new problem investigation.")


class UpdateProblemParams(EntryIdParams):
    values: dict = Field(..., description="AR System field name/value pairs to update.")


class ListChangesParams(ConnectionRefParams):
    status: str = Field("", description="Optional status filter, e.g. 'Draft', 'Request For Authorization', 'Implementation'.")
    limit: int = Field(50, description="Max records to return.")


class CreateChangeParams(ConnectionRefParams):
    values: dict = Field(..., description="AR System field name/value pairs for the new change request.")


class UpdateChangeParams(EntryIdParams):
    values: dict = Field(..., description="AR System field name/value pairs to update.")


class ListWorkOrdersParams(ConnectionRefParams):
    status: str = Field("", description="Optional status filter.")
    limit: int = Field(50, description="Max records to return.")


class CreateWorkOrderParams(ConnectionRefParams):
    values: dict = Field(..., description="AR System field name/value pairs for the new work order.")


class UpdateWorkOrderParams(EntryIdParams):
    values: dict = Field(..., description="AR System field name/value pairs to update.")


class ListKnowledgeParams(ConnectionRefParams):
    limit: int = Field(50, description="Max records to return.")


class ListCIsParams(ConnectionRefParams):
    ci_class: str = Field("", description="Optional CI class filter, e.g. 'BMC_COMPUTERSYSTEM'.")
    limit: int = Field(50, description="Max records to return.")


class GenericFormParams(ConnectionRefParams):
    form_name: str = Field(..., description="Exact AR System form name, e.g. 'HPD:Help Desk'.")
    qualification: str = Field("", description="Optional AR System qualification query, e.g. '\\'Status\\' = \"New\"'.")
    limit: int = Field(50, description="Max records to return.")


class GenericEntryParams(ConnectionRefParams):
    form_name: str = Field(..., description="Exact AR System form name.")
    entry_id: str = Field(..., description="Entry id (request id).")


class GenericCreateParams(ConnectionRefParams):
    form_name: str = Field(..., description="Exact AR System form name.")
    values: dict = Field(..., description="Field name/value pairs for the new entry.")


class GenericUpdateParams(GenericEntryParams):
    values: dict = Field(..., description="Field name/value pairs to update.")


class AuditHealthParams(ConnectionRefParams):
    pass


class BMCHelixConnection(sdl.Entity):
    id: str
    title: str
    label: str
    host: str
    connected: bool = True


class ConnectionList(sdl.Entity):
    connections: list[BMCHelixConnection] = []


class DeleteResult(sdl.Entity):
    id: str
    deleted: bool = True


class Incident(sdl.Entity):
    entry_id: str
    title: str
    description: str = ""
    status: str = ""
    priority: str = ""
    raw: dict = {}


class IncidentList(sdl.Entity):
    incidents: list[Incident] = []


class Problem(sdl.Entity):
    entry_id: str
    title: str
    description: str = ""
    status: str = ""
    raw: dict = {}


class ProblemList(sdl.Entity):
    problems: list[Problem] = []


class ChangeRequest(sdl.Entity):
    entry_id: str
    title: str
    description: str = ""
    status: str = ""
    raw: dict = {}


class ChangeRequestList(sdl.Entity):
    changes: list[ChangeRequest] = []


class WorkOrder(sdl.Entity):
    entry_id: str
    title: str
    description: str = ""
    status: str = ""
    raw: dict = {}


class WorkOrderList(sdl.Entity):
    work_orders: list[WorkOrder] = []


class KnowledgeArticle(sdl.Entity):
    entry_id: str
    title: str
    raw: dict = {}


class KnowledgeArticleList(sdl.Entity):
    articles: list[KnowledgeArticle] = []


class ConfigItem(sdl.Entity):
    entry_id: str
    title: str
    ci_class: str = ""
    status: str = ""
    raw: dict = {}


class ConfigItemList(sdl.Entity):
    items: list[ConfigItem] = []


class GenericEntry(sdl.Entity):
    entry_id: str
    title: str
    raw: dict = {}


class GenericEntryList(sdl.Entity):
    entries: list[GenericEntry] = []


class HealthAudit(sdl.Entity):
    id: str = "audit"
    title: str = "BMC Helix health audit"
    open_incident_count: int = 0
    open_problem_count: int = 0
    open_change_count: int = 0
    open_work_order_count: int = 0
    raw: dict = {}
