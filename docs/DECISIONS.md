---
schema_version: 1
document_id: decisions
owner: OPANKY
status: active
last_verified_at: 2026-08-10
---

# Decisions

## D-001

Date: 2026-08-10. Status: accepted. Decision: maintain a dedicated public hub. Reason: cross-project context needs a safe, stable entry point.

## D-002

Date: 2026-08-10. Status: accepted. Decision: use GitHub as durable memory. Reason: accepted changes require reviewable history.

## D-003

Date: 2026-08-10. Status: accepted. Decision: separate source ownership. Reason: project repositories own runtime truth and external systems own original assets.

## D-004

Date: 2026-08-10. Status: accepted. Decision: keep canonical context English-only. Reason: it provides one interoperable public language for humans and AI.

## D-005

Date: 2026-08-10. Status: accepted. Decision: generate project and portfolio views. Reason: `context.json` is the metadata owner and generated views avoid divergence.

## D-006

Date: 2026-08-10. Status: accepted. Decision: enforce a public/private boundary. Reason: public context must not disclose sensitive or unapproved material.

## D-007

Date: 2026-08-10. Status: accepted. Decision: include no license, site, database, vector store, model provider, Pydantic runtime, or paid API in V1. Reason: V1 needs a compact, deterministic public context contract before optional infrastructure.
