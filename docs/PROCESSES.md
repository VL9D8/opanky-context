---
schema_version: 1
document_id: processes
owner: OPANKY
status: active
last_verified_at: 2026-08-14
---

# Processes

## Capture and curation

Keep private capture separate. Curate only public-safe facts with a source, owner, verification date, and confidence. Classify unsupported facts as Unknown, Partial, or Not published.

## Engineering changes

Propagate verified changes to the owning repository and this hub as needed. Correct errors with dated evidence; mark stale state rather than preserving it. Run deterministic validation before accepting a change.

## AI consumption

AI reads `CONTEXT.md`, `context.json`, and the relevant canonical document before proposing changes. AI output is a proposal until backed by a public source, repository evidence, test, or explicit owner confirmation.

## Daily Work to Content

Collect only verified, publication-safe evidence from owning repositories. Apply a privacy review, rank ideas on novelty, specificity, usefulness, evidence, and relevance, then create reviewable drafts. Record only explicit approve, edit, or reject feedback. Publication and scheduling are separate owner-authorized actions; no automatic publisher or learning loop is part of the current workflow.
