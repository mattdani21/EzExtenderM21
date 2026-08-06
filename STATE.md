# State

**Status:** Dormant demo (last commit 2025-11-09). No open issues; no CI; no tests. Workplace-derived — docs use generic terms only.

## Current state (by inspection, not execution)

- FastAPI app (app/main.py): index form, POST /request (48h auto-approval if >48h away, else RAG), POST /review human-in-the-loop flow that stores precedents.
- app/rules.py (48h rule + deadline_meta), app/rag.py (Chroma + BGE embeddings, policy + precedent collections), app/precedent.py, app/ingest_policy.py all present.
- Architecture documented (architecture.mmd) and README links a demo video (Google Drive).
- pre-commit detect-secrets hook with .secrets.baseline; requirements.txt and .env.example present.

## Broken / incomplete

- README.md:31–32: the "Run server" section is missing the actual command — the line after "# Run server" is blank, so a fresh reader cannot start the server from the README.
- app/llm.py is empty (0 lines) — the LLM path configured via .env.example (ollama/groq) is unimplemented.
- GET /dashboard returns a hardcoded empty items list (app/main.py).
- No tests, no CI.

## Blockers

- No test/CI safety net.
- LLM integration unimplemented (app/llm.py empty).
- Local setup is heavy: Chroma + sentence-transformers (BAAI/bge-small-en-v1.5) + optional Ollama; ingest data requirements undocumented.

## Test command

None (add pytest in M1).

## Run command

`uvicorn app.main:app --reload` (FastAPI convention per README quick start intent; the command line itself is currently missing from README.md — fixed in M2)
