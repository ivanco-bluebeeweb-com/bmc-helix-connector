# BMC Helix Connector — Connector Discovery

**Discovery date:** 2026-08-24
**Release scope:** maximum functionality against the publicly documented BMC Helix ITSM
(Remedy AR System) REST API (per standing "максимальный функционал" instruction).
**Related task:** BBW Imperal Apps #2440.

## 1. What BMC Helix ITSM actually is

BMC Helix ITSM (formerly Remedy ITSM) runs on the **AR System (Action Request System)**
platform. Every ITSM record — Incident, Problem, Change, Work Order, Knowledge Article,
CI — is a row in an **AR System form** (e.g. `HPD:Help Desk` for incidents,
`CHG:Infrastructure Change` for changes, `PBM:Problem Investigation` for problems,
`AST:BMC Asset` / `BMC.CORE:BMC_BaseElement` for CMDB CIs). Like ServiceNow's Table API,
AR System exposes a **generic Data REST API** that can read/write any form by name,
giving forward compatibility with any BMC Helix module/customization without per-form
code, plus dedicated ITSM People/CI endpoints.

## 2. Chosen integration surface

**AR System REST API** (`/api/arsys/v1/*` on the Innovation Suite / Mid Tier host):
- **Auth**: `POST /api/jwt/login` (form-encoded username/password) → JWT token used as
  `Authorization: AR-JWT <token>` on every subsequent call. Token has a TTL and must be
  refreshed (`PUT /api/jwt/login`) or re-obtained.
- **Generic Entry API**: `/api/arsys/v1/entry/{formName}` — GET (list with qualification
  query `q=`), POST (create), and `/api/arsys/v1/entry/{formName}/{entryId}` — GET
  (read one), PUT (update), DELETE (delete). This is the ServiceNow-Table-API-equivalent
  generic surface, targeting: `HPD:Help Desk` (incidents), `CHG:Infrastructure Change`
  (changes), `PBM:Problem Investigation` (problems), `WOI:WorkOrder` (work orders),
  `RKM:KnowledgeArticle` (knowledge), `BMC.CORE:BMC_BaseElement` (CMDB CIs).
- **Attachments**: multipart entry creation for forms with attachment fields.
- **Qualification language**: AR System's own query syntax (e.g. `'Status' = "New"`) is
  used as the `q` parameter, analogous to ServiceNow's `sysparm_query`.

Not in scope for v1 (Tier 2/future): Smart IT UI-specific endpoints, Innovation Studio
custom app forms beyond the generic entry passthrough, Digital Workplace catalog.

## 3. Auth model

**JWT via username/password** (AR System's standard REST auth) — the realistic default
for a service account, since OAuth2/SSO integration varies heavily per BMC Helix SaaS
tenant configuration and is not uniformly documented across on-prem/cloud editions.

## 4. Field mapping notes

AR System field names are typically human-readable strings in quotes (e.g. `'Summary'`,
'Status', 'Priority') rather than ServiceNow's snake_case system names — the generic
table passthrough accepts raw field dictionaries so any tenant's actual field names work
without hardcoding assumptions.
