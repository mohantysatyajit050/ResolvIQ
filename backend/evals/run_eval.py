"""Intent router eval. Run from backend/:  uv run python -m evals.run_eval"""
import argparse
import json
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app.agent.errors import LLMError
from app.agent.llm import GroqLLMClient
from app.agent.router import route_complaint
from app.core.config import settings
from evals.intent_cases import CASES

PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2, "urgent": 3}
RESULTS_DIR = Path(__file__).parent / "results"


def run_case(llm, case):
    try:
        result = route_complaint(llm, case["text"])
    except LLMError as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {
        "intent": result.intent.value,
        "priority": result.priority.value,
        "confidence": result.confidence,
        "reason": result.reason,
    }


def score(case, out):
    if "error" in out:
        return {"error": True, "intent_ok": False, "prio_exact": False,
                "prio_near": False, "forbidden": False}
    gap = abs(PRIORITY_ORDER[out["priority"]] - PRIORITY_ORDER[case["priority"]])
    return {
        "error": False,
        "intent_ok": out["intent"] in case["intents"],
        "prio_exact": gap == 0,
        "prio_near": gap <= 1,
        "forbidden": out["priority"] in case["forbid"],
    }


def pct(count, total):
    return f"{100 * count / total:5.1f}%" if total else "  n/a"


def avg(values):
    return f"{statistics.mean(values):.2f}" if values else "n/a"


def table_line(name, group):
    n = len(group)
    s = [row["score"] for row in group]
    print(
        f"{name:<12}{n:>3}  "
        f"{pct(sum(x['intent_ok'] for x in s), n):>7}  "
        f"{pct(sum(x['prio_exact'] for x in s), n):>10}  "
        f"{pct(sum(x['prio_near'] for x in s), n):>9}  "
        f"{sum(x['forbidden'] for x in s):>9}  "
        f"{sum(x['error'] for x in s):>6}"
    )


def report(rows):
    by_tag = defaultdict(list)
    for row in rows:
        by_tag[row["case"]["tag"]].append(row)

    print("\n" + "=" * 70)
    print(f"{'tag':<12}{'n':>3}  {'intent':>7}  {'prio exact':>10}  "
          f"{'prio near':>9}  {'forbidden':>9}  {'errors':>6}")
    for tag, group in by_tag.items():
        table_line(tag, group)
    print("-" * 70)
    table_line("OVERALL", rows)

    answered = [r for r in rows if not r["score"]["error"]]
    confs = [r["output"]["confidence"] for r in answered]
    if confs:
        right = [r["output"]["confidence"] for r in answered if r["score"]["intent_ok"]]
        wrong = [r["output"]["confidence"] for r in answered if not r["score"]["intent_ok"]]
        vague = [r["output"]["confidence"] for r in answered
                 if r["case"]["tag"] in ("mixed", "no_problem", "short")]
        print("\nConfidence check")
        print(f"  min {min(confs):.2f}  max {max(confs):.2f}  distinct values {len(set(confs))}")
        print(f"  average when intent is right:        {avg(right)}")
        print(f"  average when intent is wrong:        {avg(wrong)}")
        print(f"  average on mixed/no_problem/short:   {avg(vague)}")
        if right and vague and statistics.mean(right) - statistics.mean(vague) >= 0.15:
            print("  VERDICT: confidence is lower on vague cases. It carries some signal.")
        else:
            print("  VERDICT: confidence does not separate clear from vague cases. "
                  "Do not use it as a gate yet.")

    bad = [r for r in rows
           if r["score"]["error"] or not r["score"]["intent_ok"] or r["score"]["forbidden"]]
    print(f"\nProblems ({len(bad)}):")
    for r in bad:
        c, o = r["case"], r["output"]
        print(f"- {c['id']} [{c['tag']}] {c['text'][:70]!r}")
        if "error" in o:
            print(f"    error: {o['error']}")
        else:
            never = ",".join(c["forbid"]) or "-"
            print(f"    expected {'/'.join(c['intents'])} + {c['priority']} (never: {never})")
            print(f"    got      {o['intent']} + {o['priority']} @ {o['confidence']}")
            print(f"    reason:  {o['reason']}")
    if any(r["score"]["error"] for r in rows):
        print("\nSome cases had errors (often rate limits). Run again with a higher --delay.")


def save(rows, model, tag):
    RESULTS_DIR.mkdir(exist_ok=True)
    name = model.replace("/", "_") + (f"-{tag}" if tag else "") + ".json"
    payload = {
        "model": model,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": rows,
    }
    (RESULTS_DIR / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nSaved: evals/results/{name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=settings.llm_model)
    parser.add_argument("--delay", type=float, default=8.0,
                        help="seconds to wait between calls (free tier token limit)")
    parser.add_argument("--tag", default=None, help="run only one kind of case")
    args = parser.parse_args()

    cases = [c for c in CASES if args.tag is None or c["tag"] == args.tag]
    if not cases:
        raise SystemExit(f"No cases with tag {args.tag!r}")
    if not settings.llm_api_key:
        raise SystemExit("LLM_API_KEY is not set in backend/.env")

    llm = GroqLLMClient(
        api_key=settings.llm_api_key,
        model=args.model,
        timeout=settings.llm_timeout_seconds,
    )
    print(f"Model: {args.model} | cases: {len(cases)} | delay: {args.delay}s")

    rows = []
    for i, case in enumerate(cases):
        out = run_case(llm, case)
        sc = score(case, out)
        rows.append({"case": case, "output": out, "score": sc})
        mark = "ERR" if sc["error"] else ("ok " if sc["intent_ok"] and not sc["forbidden"] else "BAD")
        print(f"[{i + 1}/{len(cases)}] {mark} {case['id']}")
        if i < len(cases) - 1:
            time.sleep(args.delay)

    report(rows)
    save(rows, args.model, args.tag)


if __name__ == "__main__":
    main()
