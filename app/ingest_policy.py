# app/ingest_policy.py
import re
import os, uuid, pathlib, re
from typing import List, Tuple, Optional

# --- Docling (PDF/DOCX/PPTX/HTML) --------------------------------------------
try:
    from docling.document_converter import DocumentConverter  # docling >= 2.x
except Exception:
    DocumentConverter = None  # we'll still ingest .txt/.md if Docling is missing

# --- Vector DB (Chroma) + Embeddings -----------------------------------------
import chromadb
from chromadb.utils import embedding_functions

DATA_DIR   = pathlib.Path("data/policy_pdfs")   # put your policy files here
CHROMA_DIR = "data/chroma"
COLLECTION = "PolicyDoc"

# Choose a strong but lightweight embedding model (CPU-friendly)
# Options: "BAAI/bge-small-en-v1.5" (better), "sentence-transformers/all-MiniLM-L6-v2" (smaller)
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBED_MODEL
)

# --------------------------- Helpers ------------------------------------------
def _clean(s: str) -> str:
    # light cleanup to help retrieval
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def read_textlike(p: pathlib.Path) -> str:
    if p.suffix.lower() in {".txt", ".md"}:
        return _clean(p.read_text(encoding="utf-8", errors="ignore"))
    return ""

def chunk(text: str, size: int = 1400, overlap: int = 120) -> List[str]:
    # bigger chunks keep the ALLOW/DENY sentence with context
    out, i = [], 0
    while i < len(text):
        piece = text[i:i+size].strip()
        if piece:
            out.append(piece)
        i += max(1, size - overlap)
    return out

def extract_label(snippet: str) -> Optional[str]:
    s = snippet.lower()
    if "allow:" in s: return "allow"
    if "deny:"  in s: return "deny"
    # light heuristics help early accuracy
    if any(k in s for k in ["bereavement", "death", "hospital", "broken wrist"]): return "allow"
    if any(k in s for k in ["flu", "common cold", "vacation", "travel"]): return "deny"
    return None

def convert_with_docling(p: pathlib.Path) -> str:
    if DocumentConverter is None:
        raise RuntimeError("Docling not available. Install with: pip install -U docling")
    conv = DocumentConverter()
    doc = conv.convert(str(p))
    # export to markdown—works well for chunking
    return _clean(doc.document.export_markdown())

RULE_RE = re.compile(r'(?im)^(ALLOW|DENY)\s*:\s*(.*?)(?=\n(?:ALLOW|DENY)\s*:|\Z)')

def extract_atomic_rules(text: str, source_name: str):
    text = _clean(text)
    rules = []
    for m in RULE_RE.finditer(text):
        label = m.group(1).lower().strip()  # "allow" | "deny"
        rule  = m.group(2).strip()
        # keep a short snippet so it’s focused
        snippet = f"{label.upper()}: {rule}"
        rules.append((source_name, snippet, label))
    return rules

def load_corpus() -> List[Tuple[str, str, Optional[str]]]:
    items: List[Tuple[str, str, Optional[str]]] = []
    for p in sorted(DATA_DIR.glob("*")):
        # 1) get text (docling for PDFs/DOCX, fallback for .txt/.md)
        if p.suffix.lower() in {".pdf", ".docx", ".pptx", ".html"}:
            try:
                text = convert_with_docling(p)
            except Exception as e:
                print(f"[warn] Skipping {p.name}: {e}")
                text = ""
        else:
            text = read_textlike(p)

        if not text:
            continue

        # 2) Prefer atomic ALLOW/DENY rules if present
        rules = extract_atomic_rules(text, p.name)
        if rules:
            items.extend(rules)
            continue

        # 3) Otherwise chunk the text (PDFs without clear markers, etc.)
        for c in chunk(text, size=1400, overlap=120):
            items.append((p.name, c, extract_label(c)))  # keep your heuristic fallback

    return items

# --------------------------- Main --------------------------------------------
def run():
    os.makedirs(DATA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection(
        COLLECTION,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_fn,   # ✅ use strong embeddings
    )

    # Clear for iterative dev (optional)
    try:
        if col.count() > 0:
            col.delete(where={})
    except Exception:
        pass

    rows = load_corpus()
    if not rows:
        print(f"No policy files found in {DATA_DIR}. Add .txt/.pdf/etc and rerun.")
        return

    ids, docs, metas = [], [], []
    for src, text, label in rows:
        ids.append(str(uuid.uuid4()))
        docs.append(text)
        metas.append({"source": src, "label": label})

    col.add(ids=ids, documents=docs, metadatas=metas)
    print(
        f"Ingested {len(ids)} policy chunks into '{COLLECTION}' at {CHROMA_DIR} "
        f"(embeddings='{EMBED_MODEL}')"
    )

if __name__ == "__main__":
    run()
