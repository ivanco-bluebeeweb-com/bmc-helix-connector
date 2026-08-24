"""BMC Helix Connector panels."""
from __future__ import annotations

from imperal_sdk import ui

import handlers as h
from app import ext


def _field(label: str, node: ui.UINode) -> ui.UINode:
    return ui.Stack(direction="v", gap=1, align="stretch", children=[
        ui.Text(label, variant="label"),
        node,
    ])


@ext.panel("bmc_helix_sidebar", slot="left", title="BMC Helix")
async def bmc_helix_sidebar(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Text("Connect your BMC Helix instance", variant="subtitle"),
            ui.Form(action="connect_bmc_helix", submit_label="Connect", children=[
                _field("Instance label", ui.Input(param_name="label", placeholder="Acme Production")),
                _field("AR REST host", ui.Input(param_name="host", placeholder="https://acme-restapi.onbmc.com")),
                _field("Username", ui.Input(param_name="username", placeholder="integration.user")),
                _field("Password", ui.Input(param_name="password", placeholder="AR System password")),
            ]),
            ui.Button("Where do I find my AR REST host?", variant="ghost", size="sm", icon="HelpCircle",
                      on_click=ui.Call("__panel__bmc_helix_connect_help")),
        ])
    conn = connections[0]
    label = conn.get("label") or conn.get("host", "")
    return ui.Stack(direction="v", gap=2, align="stretch", children=[
        ui.Text(label, variant="subtitle"),
        ui.Divider(),
        ui.Button("Incidents", variant="ghost", full_width=True, on_click=ui.Call("__panel__bmc_helix_center", view="incidents")),
        ui.Button("Problems", variant="ghost", full_width=True, on_click=ui.Call("__panel__bmc_helix_center", view="problems")),
        ui.Button("Changes", variant="ghost", full_width=True, on_click=ui.Call("__panel__bmc_helix_center", view="changes")),
        ui.Button("Work orders", variant="ghost", full_width=True, on_click=ui.Call("__panel__bmc_helix_center", view="work_orders")),
        ui.Button("Knowledge", variant="ghost", full_width=True, on_click=ui.Call("__panel__bmc_helix_center", view="knowledge")),
        ui.Button("CMDB", variant="ghost", full_width=True, on_click=ui.Call("__panel__bmc_helix_center", view="cmdb")),
        ui.Button("Generic form", variant="ghost", full_width=True, on_click=ui.Call("__panel__bmc_helix_center", view="generic")),
        ui.Divider(),
        ui.Button("App settings", variant="ghost", full_width=True, icon="Settings", on_click=ui.Call("__panel__bmc_helix_settings")),
    ])


@ext.panel("bmc_helix_connect_help", slot="center", title="Connecting BMC Helix", icon="HelpCircle", center_overlay=True)
async def bmc_helix_connect_help(ctx, **kwargs) -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Header(text="Where do I find my AR REST host?", level=2),
        ui.Text("SaaS BMC Helix tenants typically use a host like 'https://<tenant>-restapi.onbmc.com'. On-premise AR System deployments use 'https://<host>:<port>' where the port is your Mid Tier/Innovation Suite REST port (often 8443 or 443).", variant="body"),
        ui.Text("Use an integration account's username and password -- the connector performs a real JWT login (/api/jwt/login) before saving anything, so you'll know immediately if the credentials are wrong.", variant="body"),
        ui.Callout(text="Credentials are stored encrypted and used only to call your AR System REST API on your behalf. JWT tokens expire and are refreshed automatically.", type="info"),
    ])


@ext.panel("bmc_helix_center", slot="center", title="BMC Helix", icon="Ticket", center_overlay=True)
async def bmc_helix_center(ctx, view: str = "incidents", **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Text("Connect a BMC Helix instance first.", variant="body")

    if view == "problems":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Problems", level=2),
            ui.Form(action="list_problems", submit_label="List problems", children=[
                _field("Status filter", ui.Input(param_name="status", placeholder="e.g. Under Investigation")),
            ]),
            ui.Divider(),
            ui.Text("Create problem", variant="subtitle"),
            ui.Form(action="create_problem", submit_label="Create", children=[
                _field("Field values (JSON)", ui.Input(param_name="values", placeholder='{"Description": "Recurring VPN drops"}')),
            ]),
        ])

    if view == "changes":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Change requests", level=2),
            ui.Form(action="list_change_requests", submit_label="List changes", children=[
                _field("Status filter", ui.Input(param_name="status", placeholder="e.g. Scheduled")),
            ]),
            ui.Divider(),
            ui.Text("Create change request", variant="subtitle"),
            ui.Form(action="create_change_request", submit_label="Create", children=[
                _field("Field values (JSON)", ui.Input(param_name="values", placeholder='{"Description": "Upgrade firewall firmware"}')),
            ]),
        ])

    if view == "work_orders":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Work orders", level=2),
            ui.Form(action="list_work_orders", submit_label="List work orders", children=[
                _field("Status filter", ui.Input(param_name="status", placeholder="e.g. Assigned")),
            ]),
            ui.Divider(),
            ui.Text("Create work order", variant="subtitle"),
            ui.Form(action="create_work_order", submit_label="Create", children=[
                _field("Field values (JSON)", ui.Input(param_name="values", placeholder='{"Description": "Provision new laptop"}')),
            ]),
        ])

    if view == "knowledge":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Knowledge articles", level=2),
            ui.Form(action="list_knowledge_articles", submit_label="List articles", children=[]),
        ])

    if view == "cmdb":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="CMDB configuration items", level=2),
            ui.Form(action="list_cmdb_cis", submit_label="List CIs", children=[
                _field("CI class filter", ui.Input(param_name="ci_class", placeholder="e.g. BMC_COMPUTERSYSTEM")),
            ]),
        ])

    if view == "generic":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Generic AR System form access", level=2),
            ui.Form(action="list_table", submit_label="List records", children=[
                _field("Form name", ui.Input(param_name="form_name", placeholder="HPD:Help Desk")),
                _field("Qualification query (optional)", ui.Input(param_name="qualification", placeholder="'Status' = \"New\"")),
            ]),
        ])

    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Header(text="Incidents", level=2),
        ui.Form(action="list_incidents", submit_label="List incidents", children=[
            _field("Status filter", ui.Input(param_name="status", placeholder="e.g. New")),
        ]),
        ui.Divider(),
        ui.Text("Create incident", variant="subtitle"),
        ui.Form(action="create_incident", submit_label="Create", children=[
            _field("Field values (JSON)", ui.Input(param_name="values", placeholder='{"Description": "Email server down", "Impact": "2-Significant/Large"}')),
        ]),
    ])
