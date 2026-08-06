# Goal

Automate extension requests with 48h auto-approval plus policy/precedent RAG (workplace pilot)

## Roadmap

### M1 — Test framework + CI
- [ ] Add pytest and write unit tests for app/rules.py (48h rule, deadline_meta) and app/rag.py (policy lookup, normalize_reason, tag_reason)
- [ ] Add tests for app/precedent.py (record + retrieve precedents)
- [ ] Add GitHub Actions CI (pytest on push/PR; repo currently has no CI)
*Definition of done:* `pytest` passes in CI.

### M2 — Fix demo wiring gaps
- [ ] Restore the missing server run command in README.md (the "# Run server" line at README.md:31 is followed by a blank line — the uvicorn command is missing)
- [ ] Implement app/llm.py (currently empty, 0 lines) or remove it from the demo path
- [ ] Populate the /dashboard endpoint (app/main.py currently returns a hardcoded empty items list)
- [ ] Verify the ingest + seed flow (python -m app.ingest_policy, scripts/seed_precedent.py) and document data/ requirements
*Definition of done:* a fresh checkout runs the full demo from README instructions and the dashboard shows real stored precedents.

### M3 — Pilot-readiness for the workplace
- [ ] Move all configuration to env vars (.env.example exists: LLM_BACKEND, VECTOR_BACKEND, endpoints) and document setup
- [ ] Re-run detect-secrets (pre-commit hook + .secrets.baseline exist) and confirm no secrets are committed
- [ ] Decide the LLM path (ollama vs groq) and document RAG tuning knobs (MIN_CONF=0.60, PRECEDENT_WEIGHT=0.35 in app/rag.py)
*Definition of done:* a second person can run the pilot from a clean checkout without asking the author.

### M4 — Evaluate the pilot & decide next step
- [ ] Measure 48h auto-approval coverage and human-in-the-loop review quality on real requests
- [ ] Assess precedent RAG retrieval quality; tune MIN_CONF/PRECEDENT_WEIGHT if needed
- [ ] Decide: extend pilot, productise, or archive — record the decision in the README
*Definition of done:* a written go/no-go decision with evidence.

## Notes

- Workplace-derived demo: keep all docs and commits generic ("our extension requestor offering", "the workplace"); do not name the employer.
