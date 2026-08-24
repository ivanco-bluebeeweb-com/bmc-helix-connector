"""Thin AR System (Remedy) REST client for BMC Helix ITSM.

Auth: JWT via /api/jwt/login. Data: generic Entry API /api/arsys/v1/entry/{formName}.
"""
from __future__ import annotations

from typing import Any

import httpx


class BMCHelixError(RuntimeError):
    """A safe provider-facing error; never includes credentials."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


_FORM_INCIDENT = "HPD:Help Desk"
_FORM_PROBLEM = "PBM:Problem Investigation"
_FORM_CHANGE = "CHG:Infrastructure Change"
_FORM_WORK_ORDER = "WOI:WorkOrder"
_FORM_KNOWLEDGE = "RKM:KnowledgeArticle"
_FORM_CI = "BMC.CORE:BMC_BaseElement"


class BMCHelixClient:
    """REST client for AR System's Data REST API."""

    def __init__(self, host: str, username: str, password: str, *, timeout: float = 30.0):
        url = (host or "").strip().rstrip("/")
        if not url:
            raise BMCHelixError("AR REST host is required, e.g. 'https://acme-restapi.onbmc.com'.")
        if not url.startswith("http"):
            url = f"https://{url}"
        self.base_url = url
        self.username = username or ""
        self.password = password or ""
        self.timeout = timeout
        if not self.username or not self.password:
            raise BMCHelixError("Username and password are both required.")
        self._token: str | None = None

    async def _login(self) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/api/jwt/login",
                    data={"username": self.username, "password": self.password},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            except httpx.TimeoutException:
                raise BMCHelixError("Connection to BMC Helix timed out.", retryable=True)
            except httpx.ConnectError:
                raise BMCHelixError("Could not reach the AR REST host. Check the host URL.", retryable=True)
            if resp.status_code == 401:
                raise BMCHelixError("Invalid username or password.")
            if resp.status_code >= 400:
                raise BMCHelixError(f"Login failed ({resp.status_code}).", retryable=resp.status_code >= 500)
            token = resp.text.strip()
            if not token:
                raise BMCHelixError("Login succeeded but no token was returned.")
            self._token = token
            return token

    async def request(self, method: str, path: str, *, params: dict | None = None, json_body: dict | None = None, _retry: bool = True) -> Any:
        if not self._token:
            await self._login()
        headers = {"Authorization": f"AR-JWT {self._token}", "Accept": "application/json", "Content-Type": "application/json"}
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.request(method, url, headers=headers, params=params, json=json_body)
            except httpx.TimeoutException:
                raise BMCHelixError("Request to BMC Helix timed out.", retryable=True)
            except httpx.ConnectError:
                raise BMCHelixError("Could not reach the AR REST host.", retryable=True)
            if resp.status_code == 401 and _retry:
                self._token = None
                await self._login()
                return await self.request(method, path, params=params, json_body=json_body, _retry=False)
            if resp.status_code == 404:
                raise BMCHelixError("Record or form not found.")
            if resp.status_code >= 400:
                detail = ""
                try:
                    body = resp.json()
                    detail = str(body)[:300]
                except Exception:
                    detail = resp.text[:300]
                raise BMCHelixError(f"BMC Helix API error {resp.status_code}: {detail}", retryable=resp.status_code >= 500)
            if resp.status_code == 204 or not resp.content:
                return {}
            try:
                return resp.json()
            except Exception:
                return {}

    async def ping(self) -> dict:
        await self._login()
        return {"ok": True}

    # ---- generic entry API ----
    async def list_entries(self, form_name: str, *, qualification: str = "", fields: str = "", limit: int = 50) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if qualification:
            params["q"] = qualification
        if fields:
            params["fields"] = f"values({fields})"
        data = await self.request("GET", f"/api/arsys/v1/entry/{form_name}", params=params)
        return data.get("entries", []) if isinstance(data, dict) else []

    async def get_entry(self, form_name: str, entry_id: str) -> dict:
        return await self.request("GET", f"/api/arsys/v1/entry/{form_name}/{entry_id}")

    async def create_entry(self, form_name: str, values: dict) -> dict:
        return await self.request("POST", f"/api/arsys/v1/entry/{form_name}", json_body={"values": values})

    async def update_entry(self, form_name: str, entry_id: str, values: dict) -> dict:
        await self.request("PUT", f"/api/arsys/v1/entry/{form_name}/{entry_id}", json_body={"values": values})
        return await self.get_entry(form_name, entry_id)

    async def delete_entry(self, form_name: str, entry_id: str) -> None:
        await self.request("DELETE", f"/api/arsys/v1/entry/{form_name}/{entry_id}")

    # ---- typed ITSM shortcuts ----
    async def list_incidents(self, *, status: str = "", limit: int = 50) -> list[dict]:
        q = f"'Status' = \"{status}\"" if status else ""
        return await self.list_entries(_FORM_INCIDENT, qualification=q, limit=limit)

    async def get_incident(self, incident_id: str) -> dict:
        return await self.get_entry(_FORM_INCIDENT, incident_id)

    async def create_incident(self, values: dict) -> dict:
        return await self.create_entry(_FORM_INCIDENT, values)

    async def update_incident(self, incident_id: str, values: dict) -> dict:
        return await self.update_entry(_FORM_INCIDENT, incident_id, values)

    async def list_problems(self, *, status: str = "", limit: int = 50) -> list[dict]:
        q = f"'Status' = \"{status}\"" if status else ""
        return await self.list_entries(_FORM_PROBLEM, qualification=q, limit=limit)

    async def create_problem(self, values: dict) -> dict:
        return await self.create_entry(_FORM_PROBLEM, values)

    async def update_problem(self, problem_id: str, values: dict) -> dict:
        return await self.update_entry(_FORM_PROBLEM, problem_id, values)

    async def list_changes(self, *, status: str = "", limit: int = 50) -> list[dict]:
        q = f"'Status' = \"{status}\"" if status else ""
        return await self.list_entries(_FORM_CHANGE, qualification=q, limit=limit)

    async def create_change(self, values: dict) -> dict:
        return await self.create_entry(_FORM_CHANGE, values)

    async def update_change(self, change_id: str, values: dict) -> dict:
        return await self.update_entry(_FORM_CHANGE, change_id, values)

    async def list_work_orders(self, *, status: str = "", limit: int = 50) -> list[dict]:
        q = f"'Status' = \"{status}\"" if status else ""
        return await self.list_entries(_FORM_WORK_ORDER, qualification=q, limit=limit)

    async def create_work_order(self, values: dict) -> dict:
        return await self.create_entry(_FORM_WORK_ORDER, values)

    async def update_work_order(self, wo_id: str, values: dict) -> dict:
        return await self.update_entry(_FORM_WORK_ORDER, wo_id, values)

    async def list_knowledge_articles(self, *, limit: int = 50) -> list[dict]:
        return await self.list_entries(_FORM_KNOWLEDGE, limit=limit)

    async def list_cis(self, *, ci_class: str = "", limit: int = 50) -> list[dict]:
        q = f"'ClassId' = \"{ci_class}\"" if ci_class else ""
        return await self.list_entries(_FORM_CI, qualification=q, limit=limit)
