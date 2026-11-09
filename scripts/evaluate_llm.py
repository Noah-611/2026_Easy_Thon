# 용도: 합성 평가·회귀 사례를 실제 LLM에 보내 지표와 결과를 기록한다.
"""Explicit opt-in live evaluation of synthetic fixtures; never runs during tests."""
import argparse
import asyncio
import json
from time import perf_counter

from sklearn.metrics import classification_report
import numpy as np

from backend.app.config import ROOT, settings
from backend.app.errors import AnalysisError
from backend.app.schemas import AnalyzeRequest
from backend.app.services.analysis import analyze
from backend.app.services.llm import GeminiClient
from backend.app.services.retrieval import KnowledgeBase
from scripts.baseline import LABELS, fingerprint, load_cases


async def run(args):
    config = settings()
    if not config.llm_api_key.get_secret_value():
        raise SystemExit("LLM_API_KEY is missing. No requests made; evaluation is incomplete.")
    rows = (json.loads((ROOT / "data/evaluation/regression.json").read_text(encoding="utf-8"))
            if args.suite == "regression" else load_cases())
    cases = rows if args.suite == "regression" else [r for r in rows if r["split"] == args.split]
    suite = "regression" if args.suite == "regression" else args.split
    if args.case_id:
        selected = set(args.case_id)
        if not selected.issubset({row["id"] for row in cases}):
            raise SystemExit("Unknown case ID; no API requests made.")
        cases = [row for row in cases if row["id"] in selected]
        suite += "-selected"
    kb = KnowledgeBase() if args.rag else None
    knowledge_hash = fingerprint([(ROOT / f"data/knowledge/{name}").read_text(encoding="utf-8")
                                  for name in ["sources.json", "chunks.jsonl"]]) if args.rag else None
    results = []
    destination = ROOT / f"artifacts/llm{'-rag' if args.rag else ''}-{suite}.json"
    prompt_hash = fingerprint([(ROOT / f"backend/app/prompts/{p}.txt").read_text(encoding="utf-8")
                               for p in (["detect", "explain"] if args.rag else ["detect"])])
    if args.resume and destination.exists():
        previous = json.loads(destination.read_text(encoding="utf-8"))
        if (previous["model"] != config.llm_model or previous["provider"] != config.llm_provider
                or previous["dataset_sha256"] != fingerprint(rows)
                or previous.get("selected_case_ids", [row["id"] for row in cases]) != [row["id"] for row in cases]
                or previous.get("knowledge_sha256", knowledge_hash) != knowledge_hash
                or previous.get("prompt_sha256", prompt_hash) != prompt_hash):
            raise SystemExit("Resume metadata differs; keep the previous report and start a separate run.")
        results = previous["results"]
    done = {item["id"] for item in results}
    for row in cases:
        if row["id"] in done:
            continue
        client = GeminiClient(config)
        messages = row.get("messages", [{"id": "m1", "speaker": "발신자", "text": row.get("text", "")}])
        request = AnalyzeRequest(input_mode="single_message" if len(messages) == 1 else "conversation",
                                 redaction_confirmed=True, demo_data_confirmed=True, messages=messages)
        started = perf_counter()
        item = {"id": row["id"], "expected": row["status"], "category": row["category"]}
        item["expected_tags"] = row.get("expected_tags", [row["tag"]] if row.get("tag", "-") != "-" else [])
        item["failed_attempts"] = []
        try:
            for attempt in range(2):
                try:
                    result = await analyze(request, row["id"], config, kb, client)
                    break
                except AnalysisError as error:
                    item["failed_attempts"].append(error.code)
                    if error.code != "PROVIDER_BUSY" or attempt:
                        raise
                    await asyncio.sleep(15)
            item.update(predicted=result.status.value, result=result.model_dump(mode="json"))
            item["expected_tags_present"] = set(item["expected_tags"]).issubset({s.tag.value for s in result.signals})
        except AnalysisError as error:
            item.update(predicted="ERROR", error_code=error.code)
        item.update(elapsed_ms=(perf_counter() - started) * 1000, calls=client.calls,
                    input_tokens=client.input_tokens, output_tokens=client.output_tokens)
        results.append(item)
        # Local synthetic fixtures only. Never use this output mechanism for user conversations.
        actual = [r["expected"] for r in results]
        predicted = [r["predicted"] for r in results]
        tp = sum(y == p == "suspicious_signals" for y, p in zip(actual, predicted))
        report = {"method": "rules_llm_rag" if args.rag else "rules_llm", "split": suite,
                  "provider": config.llm_provider, "model": config.llm_model,
                  "prompt_sha256": prompt_hash,
                  "knowledge_sha256": knowledge_hash,
                  "dataset_sha256": fingerprint(rows), "synthetic_only": True,
                  "selected_case_ids": [row["id"] for row in cases],
                  "completed": len(results), "planned": len(cases), "results": results,
                  "failures": sum(r["predicted"] == "ERROR" for r in results),
                  "failed_attempts": sum(len(r["failed_attempts"]) for r in results),
                  "risk_recall": {"numerator": tp, "denominator": actual.count("suspicious_signals")},
                  "risk_precision": {"numerator": tp, "denominator": predicted.count("suspicious_signals")},
                  "normal_false_positives": {"numerator": sum(y == "no_clear_signals" and p == "suspicious_signals" for y, p in zip(actual, predicted)), "denominator": actual.count("no_clear_signals")},
                  "expected_tags_passed": sum(r.get("expected_tags_present", False) for r in results),
                  "latency_ms": {"p50": float(np.percentile([r["elapsed_ms"] for r in results], 50)), "p95": float(np.percentile([r["elapsed_ms"] for r in results], 95))},
                  "classification_including_failed_requests": classification_report(
                      [r["expected"] for r in results], [r["predicted"] for r in results],
                      labels=LABELS, output_dict=True, zero_division=0),
                  "semantic_review": "pending; exact quotes and valid IDs do not prove correct interpretation"}
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{row['id']}: {item['predicted']}", flush=True)
        if item.get("error_code") in {"PROVIDER_QUOTA", "LLM_NOT_CONFIGURED", "PROVIDER_UNAVAILABLE"}:
            raise SystemExit("Provider unavailable/quota reached. Partial report saved; no further calls.")
        if row is not cases[-1]:
            await asyncio.sleep(args.interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "holdout"], default="dev")
    parser.add_argument("--suite", choices=["evaluation", "regression"], default="evaluation")
    parser.add_argument("--case-id", action="append", help="Recheck selected case IDs in a separate report; preserves the original run")
    parser.add_argument("--rag", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Keep completed rows, including errors, and continue the same configuration")
    parser.add_argument("--allow-api-calls", action="store_true")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--interval", type=float, default=15)
    args = parser.parse_args()
    if not args.allow_api_calls:
        parser.error("Pass --allow-api-calls to explicitly send synthetic fixtures to the configured provider")
    if args.interval < 0 or args.interval > 60:
        parser.error("interval must be between 0 and 60 seconds")
    if args.suite == "evaluation" and args.split == "holdout" and not args.final:
        parser.error("Freeze prompts/settings before opening holdout with --final")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
