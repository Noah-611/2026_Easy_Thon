# 용도: CPU TF-IDF 분류기를 학습하고 규칙·분류기 성능을 평가한다.
"""CPU-only experiment. No external calls or production verdicts."""
import argparse
import csv
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline

from backend.app.config import ROOT
from backend.app.schemas import Message, Status
from backend.app.services.preprocess import normalize
from backend.app.services.rules import RULE_VERSION, baseline_status

DATA = ROOT / "data/evaluation/cases.tsv"
ARTIFACT = ROOT / "artifacts/tfidf.joblib"
LABELS = [s.value for s in Status]


def load_cases():
    with DATA.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader((line for line in handle if not line.startswith("#")), delimiter="\t"))
    seen = set()
    for i, row in enumerate(rows, 1):
        key = normalize(row["text"])
        if key in seen:
            raise ValueError("Duplicate normalized text; review split leakage")
        seen.add(key)
        row["id"] = f"case-{i:03d}"
        if row["status"] not in LABELS:
            raise ValueError("Invalid status")
    if Counter(r["split"] for r in rows) != {"train": 36, "dev": 40, "holdout": 20}:
        raise ValueError("Unexpected split sizes")
    return rows


def fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def train(rows):
    training = [r for r in rows if r["split"] == "train"]
    model = Pipeline([
        ("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(2, 5), sublinear_tf=True)),
        ("classifier", LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=42)),
    ])
    start = perf_counter()
    model.fit([normalize(r["text"]) for r in training], [r["status"] for r in training])
    artifact = {"model": model, "training_hash": fingerprint(training), "train_count": len(training),
                "training_ms": (perf_counter() - start) * 1000, "sklearn": sklearn.__version__}
    ARTIFACT.parent.mkdir(exist_ok=True)
    joblib.dump(artifact, ARTIFACT)
    print(json.dumps({k: v for k, v in artifact.items() if k != "model"}, indent=2))


def evaluate(rows, method, split):
    cases = [r for r in rows if r["split"] == split]
    artifact = None
    if method == "tfidf":
        # Only load the locally generated artifact; pickle files are executable.
        artifact = joblib.load(ARTIFACT)
        if artifact["training_hash"] != fingerprint([r for r in rows if r["split"] == "train"]):
            raise ValueError("Training data changed; retrain before evaluating")
    predictions, timings = [], []
    for row in cases:
        start = perf_counter()
        if method == "rules":
            prediction = baseline_status([Message(id="m1", speaker="발신자", text=row["text"])]).value
        else:
            prediction = str(artifact["model"].predict([normalize(row["text"])])[0])
        timings.append((perf_counter() - start) * 1000)
        predictions.append(prediction)
    actual = [r["status"] for r in cases]
    suspicious = Status.SUSPICIOUS.value
    positive = sum(y == suspicious for y in actual)
    predicted_positive = predictions.count(suspicious)
    tp = sum(y == p == suspicious for y, p in zip(actual, predictions))
    normal = sum(y == Status.NO_CLEAR.value for y in actual)
    normal_fp = sum(y == Status.NO_CLEAR.value and p == suspicious for y, p in zip(actual, predictions))
    report = {
        "method": method, "split": split, "count": len(cases), "data_sha256": fingerprint(rows),
        "synthetic_only": True, "independently_reviewed": False,
        "labels": LABELS, "confusion_matrix": confusion_matrix(actual, predictions, labels=LABELS).tolist(),
        "classification": classification_report(actual, predictions, labels=LABELS, output_dict=True, zero_division=0),
        "risk_recall": {"numerator": tp, "denominator": positive},
        "risk_precision": {"numerator": tp, "denominator": predicted_positive},
        "normal_false_positives": {"numerator": normal_fp, "denominator": normal},
        "needs_context_count": predictions.count(Status.CONTEXT.value),
        "latency_ms": {"p50": float(np.percentile(timings, 50)), "p95": float(np.percentile(timings, 95))},
        "rules_version": RULE_VERSION, "python": platform.python_version(), "sklearn": sklearn.__version__,
        "training_hash": artifact["training_hash"] if artifact else None,
        "errors": [{"id": r["id"], "category": r["category"], "expected": y, "predicted": p}
                   for r, y, p in zip(cases, actual, predictions) if y != p],
        "by_category": {cat: {"correct": sum(y == p for r, y, p in zip(cases, actual, predictions) if r["category"] == cat),
                              "total": sum(r["category"] == cat for r in cases)} for cat in sorted({r["category"] for r in cases})},
    }
    path = ROOT / f"artifacts/{method}-{split}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{method} {split}: macro F1={report['classification']['macro avg']['f1-score']:.3f}; "
          f"risk recall={tp}/{positive}; normal FP={normal_fp}/{normal}; report={path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["train", "evaluate"])
    parser.add_argument("--method", choices=["rules", "tfidf"], default="tfidf")
    parser.add_argument("--split", choices=["dev", "holdout"], default="dev")
    parser.add_argument("--final", action="store_true", help="Explicitly open the frozen synthetic holdout")
    args = parser.parse_args()
    if args.command == "evaluate" and args.split == "holdout" and not args.final:
        parser.error("Holdout requires --final; freeze settings first. Do not tune on these results.")
    rows = load_cases()
    train(rows) if args.command == "train" else evaluate(rows, args.method, args.split)


if __name__ == "__main__":
    main()
