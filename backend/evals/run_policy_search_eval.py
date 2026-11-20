"""Measure how well policy search finds the right chunk.

Uses the real embedding model and the real database, so seed the policies first:
    uv run python -m scripts.seed_policies

Run from the backend folder:
    uv run python -m evals.run_policy_search_eval
    uv run python -m evals.run_policy_search_eval --tag hinglish

Two modes per question:
  F = with the router's intent as a filter (how the agent really searches)
  A = with no filter (the worst case, when the router answers "other")
Rank 1 means the right chunk came first; "-" means it was not in the top 3.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

from app.agent.embeddings import get_embedder
from app.agent.policy_search import search_policies
from app.db.session import SessionLocal
from app.models.policy import Policy
from evals.policy_search_cases import ALL_CASES

RESULTS_DIR = Path(__file__).parent / "results"
TOP_K = 3


def rank_of(hits, expected):
    for position, hit in enumerate(hits, start=1):
        if f"{hit.slug}/{hit.section}" == expected:
            return position
    return None


def describe(hits):
    return ", ".join(f"{h.section} ({h.score:.2f})" for h in hits) or "nothing"


def summarise(name, rows):
    total = len(rows)
    if not total:
        return
    f1 = sum(1 for r in rows if r["filtered_rank"] == 1)
    f3 = sum(1 for r in rows if r["filtered_rank"] is not None)
    a1 = sum(1 for r in rows if r["any_rank"] == 1)
    a3 = sum(1 for r in rows if r["any_rank"] is not None)
    print(f"{name:10} n={total:2}  filtered top-1 {f1:2}/{total}  top-3 {f3:2}/{total}"
          f"   no filter top-1 {a1:2}/{total}  top-3 {a3:2}/{total}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="only run cases with this tag")
    args = parser.parse_args()

    cases = [c for c in ALL_CASES if not args.tag or c.tag == args.tag]
    if not cases:
        print("No cases to run.")
        return 1

    embedder = get_embedder()
    rows = []
    with SessionLocal() as db:
        ready = db.scalar(
            select(func.count()).select_from(Policy).where(
                Policy.is_active.is_(True),
                Policy.embedding_model == embedder.model_name,
            )
        )
        if not ready:
            print(f"No active chunks are embedded with {embedder.model_name}.")
            print("Run: uv run python -m scripts.seed_policies")
            return 1

        print(f"model: {embedder.model_name}   chunks: {ready}   questions: {len(cases)}")
        print("[F<rank> A<rank>]  F = with intent filter, A = no filter, - = not in top 3\n")
        for case in cases:
            filtered = search_policies(db, embedder, case.query, intent=case.intent, limit=TOP_K)
            unfiltered = search_policies(db, embedder, case.query, intent=None, limit=TOP_K)
            row = {
                "id": case.id,
                "tag": case.tag,
                "query": case.query,
                "expected": case.expected,
                "filtered_rank": rank_of(filtered, case.expected),
                "any_rank": rank_of(unfiltered, case.expected),
                "filtered_got": describe(filtered),
            }
            rows.append(row)
            f = row["filtered_rank"] or "-"
            a = row["any_rank"] or "-"
            print(f"[F{f} A{a}] {case.id:9} {case.query[:62]}")

    misses = [r for r in rows if r["filtered_rank"] != 1]
    if misses:
        print("\nNot first with the filter:")
        for r in misses:
            print(f"- {r['id']}: wanted {r['expected']}")
            print(f"    got: {r['filtered_got']}")

    print("\nSummary")
    summarise("ALL", rows)
    for tag in sorted({r["tag"] for r in rows}):
        summarise(tag, [r for r in rows if r["tag"] == tag])

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_model = embedder.model_name.replace("/", "_")
    path = RESULTS_DIR / f"policy_search_{safe_model}_{stamp}.json"
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nsaved {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
