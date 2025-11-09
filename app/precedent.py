# app/precedent.py
from __future__ import annotations
import json, uuid, pathlib, time
from typing import Optional, Dict, Any

import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR = "data/chroma"
PRECEDENT_JSON = pathlib.Path("data/precedent.json")
PRECEDENT_COLLECTION = "PrecedentCases"

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-small-en-v1.5"
)

_client = chromadb.PersistentClient(path=CHROMA_DIR)
_prec_col = _client.get_or_create_collection(
    PRECEDENT_COLLECTION,
    metadata={"hnsw:space": "cosine"},
    embedding_function=embedding_fn,
)

def _safe_load_json(p: pathlib.Path):
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}

def _safe_write_json(p: pathlib.Path, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))

def _infer_tag(reason_text: str) -> str:
    s = (reason_text or "").lower()
    if any(w in s for w in ("bereavement","passed away","funeral","death")):
        return "bereavement"
    if any(w in s for w in ("flu","cold","common cold")):
        return "minor_illness"
    if any(w in s for w in ("hospital","injury","broken wrist","surgery")):
        return "serious_injury"
    if any(w in s for w in ("vacation","travel","trip","holiday")):
        return "travel"
    return "other"

def record_precedent(
    *,
    reason_text_raw: str,
    outcome: str,                         # "allow"/"deny" or "approve"/"reject"
    meta: Optional[Dict[str, Any]] = None,
    tag: Optional[str] = None,
    reason_text_norm: Optional[str] = None,
) -> None:
    """
    Store the *raw requestor text* in the vector DB (for similarity),
    keep tag + normalized text as metadata only.
    """
    outcome = (outcome or "").lower().strip()
    if outcome == "approve": outcome = "allow"
    if outcome == "reject":  outcome = "deny"
    if outcome not in ("allow","deny"):
        raise ValueError("outcome must be 'allow' or 'deny'")

    tag = tag or _infer_tag(reason_text_raw)
    ts = int(time.time())

    m = {
        "type": "precedent",
        "outcome": outcome,
        "tag": tag,
        "raw": reason_text_raw,
        "norm": (reason_text_norm or "").strip(),
        "ts": ts,
    }
    if meta: m.update(meta)

    # 👉 Embed the RAW text (this is what you’ll retrieve against)
    _prec_col.add(
        ids=[str(uuid.uuid4())],
        documents=[reason_text_raw],
        metadatas=[m],
    )

    # aggregate counters
    counters = _safe_load_json(PRECEDENT_JSON)
    row = counters.get(tag, {"allow": 0, "deny": 0})
    row[outcome] = int(row.get(outcome, 0)) + 1
    counters[tag] = row
    _safe_write_json(PRECEDENT_JSON, counters)
