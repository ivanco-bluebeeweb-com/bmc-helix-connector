# BMC Helix Connector — Preparation

**Version:** 0.1.0 (planning)
**Date:** 2026-08-24
**Related task:** BBW Imperal Apps #2440
**Scope decision:** maximum feasible capability against the publicly documented AR
System REST API underlying BMC Helix ITSM (per standing "максимальный функционал"
instruction).

## 1. App passport

**Name:** BMC Helix Connector
**One-line purpose:** Connect your own BMC Helix ITSM (Remedy AR System) instance to
manage Incidents, Problems, Changes, Work Orders, Knowledge Articles, and CMDB CIs
through the AR System Data REST API, plus a generic form passthrough for anything else
your instance exposes.

**What it is not:**
- Not a Smart IT / Digital Workplace UI replacement — no UI-specific workflow.
- Not an Innovation Studio custom-app builder — generic form CRUD only.
- Does not model every AR System form with typed schemas — ITSM's Tier-1 forms get
  typed wrappers; everything else is reachable through the honest generic passthrough.

## 2. Human problem

> An IT service desk agent, ITSM admin, or ops engineer at a company running BMC Helix
> ITSM needs a fast way to look up, create, and update incidents/problems/changes/work
> orders without opening the Remedy/Smart IT UI — especially for quick triage, bulk
> status updates, or pulling a health snapshot for a stand-up.

### Personas
| Persona | Trigger | Value |
|---|---|---|
| Service desk agent | "What's the status of INC000012345?" | Instant lookup without switching to Smart IT UI |
| ITSM admin | Needs to bulk-update a batch of stale incidents | Bulk wrapper over generic Entry API |
| Ops engineer | Wants a daily health snapshot (open P1s by status) | audit_instance_health value-add report |
| Change manager | Needs to see change requests awaiting approval | list_changes filtered by status |

## 3. Auth & connection model

JWT via username/password against `/api/jwt/login` on the tenant's AR REST host —
the realistic default service-account flow for AR System.

## 4. Tiered scope

**Tier 1 (this release):** connect/disconnect, Incidents (list/get/create/update),
Problems (list/create/update), Changes (list/create/update), Work Orders
(list/create/update), Knowledge Articles (list), CMDB CIs (list), generic form
passthrough (list/get/create/update/delete), audit_instance_health.

**Tier 2 (future):** attachments, approval-chain actions, Smart IT-specific process
templates, Innovation Studio custom forms beyond generic passthrough.

## 5. Non-goals

Does not attempt SSO/OAuth2 (varies too much per BMC Helix SaaS tenant to standardize
safely); does not manage AR System admin config (forms, workflows, permissions).
