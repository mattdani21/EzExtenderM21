# EzExtender 2.0 — Local Demo

A tiny, end-to-end prototype for extension requests:
- **Rule**: 48-hour window check (auto-approve if >48h away).
- **Policy RAG**: Chroma + BGE embeddings over policy chunks.
- **Precedent RAG**: Stores human decisions as vectors for future retrieval.
- **HITL**: Reviewer approves/denies; decision is logged as **precedent**.

![Architecture](docs/architecture.png)

> 🎥 **Demo**: [docs/demo.mp4](docs/demo.mp4)  
> (If GitHub won’t render, download and play locally.)

---

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional: freeze "now" for the 48h rule demo
export EZ_DEMO_NOW_UTC="2025-11-01T12:00:00Z"

# Ingest policy files (txt/pdf/docx in data/policy_pdfs/)
python -m app.ingest_policy

# Run server
uvicorn app.main:app --reload
# open http://127.0.0.1:8000

Seed sample precedents (optional):
python scripts/seed_precedent.py
