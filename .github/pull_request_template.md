## Context change

- Affected project/document IDs:
- Source or owner confirmation:
- `last_verified_at`:
- Classification: fact / decision / roadmap / research / correction

## Public boundary

- [ ] No secrets, private contacts, raw chats, local paths, confidential briefs, or unpublished assets are included.
- [ ] Generated views were produced from `context.json`, not edited manually.
- [ ] Unknown or partial claims remain explicitly labeled.

## Verification

- [ ] `uv run python -m unittest discover -s tests -p "test_*.py" -v`
- [ ] `uv run python scripts/render_context.py --check`
- [ ] `uv run python scripts/validate_context.py`
