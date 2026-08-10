# Contributing

Move research to fact through curation: record the question, dated source, finding, confidence, affected project IDs, accepted destination, and `last_verified_at`. Do not copy articles or chat transcripts into canonical context.

Update `context.json` first and run the renderer; never edit generated views. Include evidence and freshness fields for every material claim. Before a pull request, run:

```powershell
uv run python -m unittest -v
uv run python scripts/render_context.py --check
```

Pull requests explain the changed fact, evidence boundary, affected canonical documents, and validation result. Keep public text English-only and label Partial, Unknown, or Not published rather than guessing.
