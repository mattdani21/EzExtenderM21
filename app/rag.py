# app/rag.py
from __future__ import annotations
import json, pathlib
import chromadb
from chromadb.utils import embedding_functions

# ========================
# Config
# ========================
CHROMA_DIR = "data/chroma"
POLICY_COLLECTION = "PolicyDoc"          # keep in sync with ingest
MIN_CONF = 0.60                          # similarity-majority must beat this to recommend
PRECEDENT_WEIGHT = 0.35                  # 0..1 (policy gets 1-PRECEDENT_WEIGHT)

# ---- Embeddings
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-small-en-v1.5"
)

# ---- Chroma client & policy collection
_client = chromadb.PersistentClient(path=CHROMA_DIR)
_policy_col = _client.get_or_create_collection(
    POLICY_COLLECTION,
    metadata={"hnsw:space": "cosine"},
    embedding_function=embedding_fn,
)

# ---- Precedent access (vector + aggregates)
try:
    # uses app/precedent.py from earlier step
    from app.precedent import query_precedent as _precedent_query
    from app.precedent import PRECEDENT_JSON as PRECEDENT_PATH
except Exception:
    def _precedent_query(reason_text: str, k: int = 5):
        # safe fallback if precedent module not present
        return []
    PRECEDENT_PATH = pathlib.Path("data/precedent.json")


# ========================
# Helpers
# ========================
def tag_reason(raw: str) -> str:
    s = raw.lower()
    if any(w in s for w in ("bereavement", "passed away", "funeral", "death")):
        return "bereavement"
    if any(w in s for w in ("hospital", "hospitalized", "surgery", "broken wrist", "injury")):
        return "serious_injury"
    if any(w in s for w in ("flu", "cold", "common cold")):
        return "minor_illness"
    if any(w in s for w in ("vacation", "travel", "trip", "holiday")):
        return "travel"
    return "other"


def _load_precedent_stats(tag: str) -> dict:
    """
    precedent.json shape:
    {
      "bereavement": {"allow": 5, "deny": 0},
      "minor_illness": {"allow": 0, "deny": 5},
      ...
    }
    """
    if pathlib.Path(PRECEDENT_PATH).exists():
        try:
            data = json.loads(pathlib.Path(PRECEDENT_PATH).read_text())
            return data.get(tag, {})
        except Exception:
            pass
    return {}


def normalize_reason(t: str) -> str:
    # light synonym expansion to help embedding match
    t = t.lower()
    return (
        t.replace("passed away", "death bereavement")
         .replace("funeral", "death bereavement")
         .replace("grandfather", "family member")
         .replace("flu", "common cold minor illness")
    )


def _to_policy_hits(col, query_text: str, k: int = 5):
    res = col.query(
        query_texts=[query_text],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    docs  = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]

    hits = []
    for doc, meta, dist in zip(docs, metas, dists):
        sim = max(0.0, min(1.0, 1.0 - float(dist)))  # cosine distance -> similarity
        hits.append({
            "document": doc or "",
            "metadata": meta or {},
            "similarity": sim,
            "source": (meta or {}).get("source", "policy"),
        })
    hits.sort(key=lambda h: h["similarity"], reverse=True)
    return hits


def _strong_cue_decision(policy_hits, min_sim: float = 0.58):
    """Fast-path if there are very clear allow/deny phrases in high-sim policy hits."""
    deny_cues  = ("not sufficient", "not valid", "deny", "insufficient", "not acceptable")
    allow_cues = ("bereavement", "death", "immediate family", "hospital", "serious injury", "broken wrist")

    strong_deny = False
    strong_allow = False

    for h in policy_hits:
        sim = h["similarity"]
        label = (h["metadata"].get("label") or "").lower()
        text = h["document"].lower()

        if label == "deny" and sim >= min_sim and any(p in text for p in deny_cues):
            strong_deny = True
        if label == "allow" and sim >= min_sim and any(p in text for p in allow_cues):
            strong_allow = True

    if strong_deny and not strong_allow:
        return {"recommend": "deny", "confidence": max(min_sim, 0.65)}
    if strong_allow and not strong_deny:
        return {"recommend": "approve", "confidence": max(min_sim, 0.65)}
    return None  # no strong cue


# ========================
# Main entry (updated to show only top policy hit)
# ========================
def policy_lookup(reason_text: str, k: int = 5) -> dict:
    """
    Blends:
      - Policy evidence (labels in metadatas: 'allow'/'deny')
      - Precedent nearest cases (outcome in metadatas: 'allow'/'deny')
    Returns a standardized payload for the UI, showing only the single
    best policy hit as 'evidence', and aggregate precedent stats separately.
    """
    tag = tag_reason(reason_text)
    q = normalize_reason(reason_text)

    # 1) Policy RAG
    policy_hits = _to_policy_hits(_policy_col, q, k=k)

    # Strong-cue fast path (optional but useful)
    strong = _strong_cue_decision(policy_hits)

    # 2) Precedent RAG (nearest past cases)
    precedent_hits = _precedent_query(q, k=5)  # [{'document','metadata':{'outcome':...}, 'similarity':...}, ...]

    # 3) Score aggregation (policy + precedent, similarity-weighted)
    pol_allow = sum(h["similarity"] for h in policy_hits if (h["metadata"].get("label") or "").lower() == "allow")
    pol_deny  = sum(h["similarity"] for h in policy_hits if (h["metadata"].get("label")  or "").lower() == "deny")

    pre_allow = sum(h["similarity"] for h in precedent_hits if (h["metadata"].get("outcome") or "").lower() == "allow")
    pre_deny  = sum(h["similarity"] for h in precedent_hits if (h["metadata"].get("outcome")  or "").lower() == "deny")

    allow_score = (1.0 - PRECEDENT_WEIGHT) * pol_allow + PRECEDENT_WEIGHT * pre_allow
    deny_score  = (1.0 - PRECEDENT_WEIGHT) * pol_deny  + PRECEDENT_WEIGHT * pre_deny
    total = allow_score + deny_score
    conf  = (max(allow_score, deny_score) / total) if total > 0 else 0.0

    # 4) Final decision
    if strong:
        conf = max(conf, strong["confidence"])
        recommend = strong["recommend"]
    else:
        recommend = None if conf < MIN_CONF or total <= 1e-9 else ("approve" if allow_score >= deny_score else "deny")

    # 5) Evidence formatting — ✅ ONLY THE TOP POLICY HIT
    evidence = []
    if policy_hits:
        h = policy_hits[0]  # top-1
        evidence.append({
            "source": h.get("source", "policy"),
            "label":  (h["metadata"].get("label") or None),
            "similarity": round(h["similarity"], 3),
            "snippet": (h["document"][:300] + ("..." if len(h["document"]) > 300 else "")),
        })
    # (No precedent hits added here; precedent appears only in the 'precedent' section below.)

    # 6) Aggregate precedent stats for this tag
    stats = _load_precedent_stats(tag)
    total_cases = int(stats.get("allow", 0)) + int(stats.get("deny", 0))
    allow_rate = (int(stats.get("allow", 0)) / total_cases) if total_cases else 0.0

    payload = {
        "decision": "recommendation" if recommend else "needs_review",
        "via": "policy_rag" if recommend else "policy_rag_low_conf",
        "recommend": recommend,
        "confidence": round(float(conf), 3),
        "explanation": (
            "Policy + precedent similarity blend with similarity-weighted voting."
            if recommend else
            "Evidence not decisive; escalate to reviewer."
        ),
        "evidence": evidence,  # ← single best policy clause only
        "precedent": {
            "tag": tag,
            "stats": stats,                       # e.g. {"allow":5,"deny":0}
            "allow_rate": round(allow_rate, 3),   # 0..1
            "hint": (
                "Historically approved in similar cases." if allow_rate >= 0.6 else
                "Historically denied in similar cases." if allow_rate <= 0.4 else
                "Mixed precedent."
            ),
        },
    }
    return payload
