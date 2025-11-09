# scripts/peek_precedent.py (you can just paste into python)
import json
import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="data/chroma")

# Counts
pol = client.get_or_create_collection(
    "PolicyDoc",
    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="BAAI/bge-small-en-v1.5"
    ),
)
prec = client.get_or_create_collection(
    "PrecedentCases",
    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="BAAI/bge-small-en-v1.5"
    ),
)

print("PolicyDoc vectors:", pol.count())
print("PrecedentCases vectors:", prec.count())

# See the top 5 most recent by storing_time if available, otherwise just query
res = prec.query(
    query_texts=["I caught a bad flu last week"], 
    n_results=5, 
    include=["documents","metadatas"]
)
print(json.dumps(res, indent=2))
