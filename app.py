"""BMC Helix Connector extension declaration.

BMC Helix ITSM runs on the AR System (Remedy) platform. Every ITSM record is a row
in an AR System form, reachable through the generic AR System Data REST API
(/api/arsys/v1/entry/{formName}), with JWT auth via /api/jwt/login.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "bmc-helix-connector",
    version="0.1.0",
    display_name="BMC Helix",
    description=(
        "Connect your own BMC Helix ITSM (Remedy AR System) instance to manage "
        "Incidents, Problems, Changes, Work Orders, Knowledge Articles, and CMDB CIs "
        "through the AR System Data REST API, plus a generic form passthrough."
    ),
    icon="icon.svg",
    capabilities=["bmc_helix:read", "bmc_helix:write"],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="bmc_helix",
    description=(
        "BMC Helix Connector — manage Incidents, Problems, Changes, Work Orders, "
        "Knowledge Articles, and CMDB CIs through the AR System Data REST API."
    ),
)

ext.secret(
    "bmc_helix_connections",
    "JSON list of connected BMC Helix instances and encrypted credentials. Managed only through connect_bmc_helix and disconnect_bmc_helix.",
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=90,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Report whether at least one BMC Helix instance is configured."""
    raw = await ctx.secrets.get("bmc_helix_connections")
    import json
    try:
        connections = json.loads(raw) if raw else []
    except (TypeError, ValueError):
        connections = []
    if not connections:
        return {"healthy": True, "detail": "No BMC Helix instance connected yet."}
    return {"healthy": True, "detail": f"{len(connections)} BMC Helix instance(s) configured."}
