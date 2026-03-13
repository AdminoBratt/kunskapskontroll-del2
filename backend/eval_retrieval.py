"""
Retrieval Evaluation Script
============================
Measures MRR, Precision@K, Recall@K and NDCG@K for the four search modes:
  - hybrid
  - hybrid + rerank
  - semantic
  - keyword

Usage:
  1. Fill in GROUND_TRUTH below with your queries and relevant document IDs.
     You can list document IDs from GET http://localhost:8000/documents
  2. Start the backend: uvicorn app.main:app --reload
  3. Run: python eval_retrieval.py
"""

import math
import requests

BASE_URL = "http://localhost:8000"

# =============================================================================
# GROUND TRUTH
# Each entry: { "query": str, "relevant_doc_ids": list[int] }
# Fill in document IDs that are relevant for each query.
# =============================================================================
GROUND_TRUTH = [
    # --- rapport Kunskapskontrolldel2 (doc 105) ---
    {
        "query": "vad är syftet med rapporten",
        "relevant_doc_ids": [105],
    },
    {
        "query": "varför skulle data stanna lokalt",
        "relevant_doc_ids": [105],
    },
    {
        "query": "vilken vektordatabas används",
        "relevant_doc_ids": [105],
    },
    {
        "query": "hur fungerar chunking i systemet",
        "relevant_doc_ids": [105],
    },
    {
        "query": "vad är skillnaden mellan bi-encoder och cross-encoder",
        "relevant_doc_ids": [105],
    },
    {
        "query": "vilka fördelar har reranking",
        "relevant_doc_ids": [105],
    },
    {
        "query": "vilket LLM används och varför",
        "relevant_doc_ids": [105],
    },
    {
        "query": "vilka nackdelar finns med det lokala systemet",
        "relevant_doc_ids": [105],
    },
    {
        "query": "hur extraheras text från PDF-filer",
        "relevant_doc_ids": [105],
    },
    {
        "query": "vad används Tesseract till",
        "relevant_doc_ids": [105],
    },
    {
        "query": "hur är backend byggd",
        "relevant_doc_ids": [105],
    },
    {
        "query": "vad är slutsatsen i rapporten",
        "relevant_doc_ids": [105],
    },
    # --- Projektbeskrivningexamensarbete (doc 106) ---
    {
        "query": "vad handlar examensarbetet om",
        "relevant_doc_ids": [106],
    },
    {
        "query": "vad är frågeställningen i examensarbetet",
        "relevant_doc_ids": [106],
    },
    {
        "query": "vilka utmaningar kan uppstå i projektet",
        "relevant_doc_ids": [106],
    },
    {
        "query": "vilka källor används i examensarbetet",
        "relevant_doc_ids": [106],
    },
    # --- Frågor som berör båda dokumenten ---
    {
        "query": "RAG system med PDF dokument",
        "relevant_doc_ids": [105, 106],
    },
    {
        "query": "frontend i React",
        "relevant_doc_ids": [105, 106],
    },
]

K_VALUES = [1, 3, 5, 10]


# =============================================================================
# Search helpers
# =============================================================================

def search_hybrid(query: str, k: int = 10, rerank: bool = False) -> list[dict]:
    payload = {"query": query, "k": k, "rerank": rerank, "rerank_candidates": 50}
    r = requests.post(f"{BASE_URL}/search", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["results"]


def search_semantic(query: str, k: int = 10) -> list[dict]:
    payload = {"query": query, "k": k}
    r = requests.post(f"{BASE_URL}/search/semantic", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["results"]


def search_keyword(query: str, k: int = 10) -> list[dict]:
    payload = {"query": query, "k": k}
    r = requests.post(f"{BASE_URL}/search/keyword", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["results"]


# =============================================================================
# Metric calculations
# =============================================================================

def reciprocal_rank(results: list[dict], relevant_ids: set[int]) -> float:
    for rank, r in enumerate(results, start=1):
        if r["document_id"] in relevant_ids:
            return 1.0 / rank
    return 0.0


def precision_at_k(results: list[dict], relevant_ids: set[int], k: int) -> float:
    top_k = results[:k]
    hits = sum(1 for r in top_k if r["document_id"] in relevant_ids)
    return hits / k


def recall_at_k(results: list[dict], relevant_ids: set[int], k: int) -> float:
    if not relevant_ids:
        return 0.0
    top_k = results[:k]
    hits = sum(1 for r in top_k if r["document_id"] in relevant_ids)
    return hits / len(relevant_ids)


def ndcg_at_k(results: list[dict], relevant_ids: set[int], k: int) -> float:
    top_k = results[:k]
    dcg = sum(
        (1.0 / math.log2(i + 2))
        for i, r in enumerate(top_k)
        if r["document_id"] in relevant_ids
    )
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def coverage(results: list[dict], relevant_ids: set[int]) -> float:
    """Fraction of relevant docs found anywhere in the result list."""
    if not relevant_ids:
        return 0.0
    found = {r["document_id"] for r in results} & relevant_ids
    return len(found) / len(relevant_ids)


# =============================================================================
# Evaluate one search mode across all queries
# =============================================================================

def evaluate_mode(name: str, fetch_fn) -> dict:
    rr_scores, cov_scores = [], []
    pk = {k: [] for k in K_VALUES}
    rk = {k: [] for k in K_VALUES}
    nk = {k: [] for k in K_VALUES}

    for item in GROUND_TRUTH:
        query = item["query"]
        relevant = set(item["relevant_doc_ids"])
        results = fetch_fn(query)

        rr_scores.append(reciprocal_rank(results, relevant))
        cov_scores.append(coverage(results, relevant))
        for k in K_VALUES:
            pk[k].append(precision_at_k(results, relevant, k))
            rk[k].append(recall_at_k(results, relevant, k))
            nk[k].append(ndcg_at_k(results, relevant, k))

    n = len(GROUND_TRUTH)
    return {
        "mode": name,
        "MRR": round(sum(rr_scores) / n, 4),
        "Coverage": round(sum(cov_scores) / n, 4),
        **{f"P@{k}": round(sum(pk[k]) / n, 4) for k in K_VALUES},
        **{f"R@{k}": round(sum(rk[k]) / n, 4) for k in K_VALUES},
        **{f"NDCG@{k}": round(sum(nk[k]) / n, 4) for k in K_VALUES},
    }


# =============================================================================
# Pretty print
# =============================================================================

def print_results(all_results: list[dict]):
    if not all_results:
        return

    col_width = 16
    metrics = [k for k in all_results[0] if k != "mode"]

    # Header
    header = f"{'Metric':<14}" + "".join(f"{r['mode']:>{col_width}}" for r in all_results)
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))

    for metric in metrics:
        row = f"{metric:<14}" + "".join(f"{r[metric]:>{col_width}.4f}" for r in all_results)
        print(row)

    print("=" * len(header))


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    if not GROUND_TRUTH:
        print("ERROR: GROUND_TRUTH is empty. Add queries and relevant_doc_ids first.")
        exit(1)

    print(f"Evaluating {len(GROUND_TRUTH)} queries across 4 search modes...")
    print(f"K values: {K_VALUES}\n")

    modes = [
        ("hybrid",         lambda q: search_hybrid(q, k=10, rerank=False)),
        ("hybrid+rerank",  lambda q: search_hybrid(q, k=10, rerank=True)),
        ("semantic",       lambda q: search_semantic(q, k=10)),
        ("keyword",        lambda q: search_keyword(q, k=10)),
    ]

    results = []
    for name, fn in modes:
        print(f"  Running {name}...", end=" ", flush=True)
        try:
            result = evaluate_mode(name, fn)
            results.append(result)
            print("done")
        except requests.exceptions.ConnectionError:
            print(f"FAILED - backend not running at {BASE_URL}")
            break
        except Exception as e:
            print(f"FAILED - {e}")

    print_results(results)
