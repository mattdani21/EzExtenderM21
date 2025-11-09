# EzExtender 2.0 — Local Demo

A tiny, end-to-end prototype for an extension to our extension requestor offering:
- **Rule**: 48-hour window check (auto-approve if >48h away).
- **Policy RAG**: Chroma + BGE embeddings over policy chunks for this demo.
- **Precedent RAG**: Stores human decisions as vectors for future retrieval.
- **HITL**: Reviewer approves/denies; decision is logged as **precedent**.

![Architecture](architecture.mmd)

<img width="600" height="107" alt="image" src="https://github.com/user-attachments/assets/ce513d11-cc70-4c7d-988a-087268cd6120" />

> 🎬 **Demo Video:**  
> [▶️ Watch EzExtender 2.0 in action on Google Drive](https://drive.google.com/file/d/1Wqei50mk8jdLufhPrHjLBDUVJH1ghB9n/view?usp=sharing)


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
 # open http://127.0.0.1:8000

Seed sample precedents (optional):
python scripts/seed_precedent.py
