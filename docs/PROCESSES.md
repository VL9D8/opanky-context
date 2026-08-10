---
schema_version: 1
document_id: processes
owner: OPANKY
status: active
last_verified_at: 2026-08-10
---

# Processes

## Capture and curation

Keep private capture separate. Curate only public-safe facts with a source, owner, verification date, and confidence. Classify unsupported facts as Unknown, Partial, or Not published.

## Engineering changes

Propagate verified changes to the owning repository and this hub as needed. Correct errors with dated evidence; mark stale state rather than preserving it. Run deterministic validation before accepting a change.

## AI consumption

AI reads `CONTEXT.md`, `context.json`, and the relevant canonical document before proposing changes. AI output is a proposal until backed by a public source, repository evidence, test, or explicit owner confirmation.
