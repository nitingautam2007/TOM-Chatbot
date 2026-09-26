"""Phase 7 CLI evaluation runner — intent, emotion, safety, response selection.

Usage (from backend/):
  .venv/Scripts/python -m evaluation.run_phase7
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from evaluation.dataset import (
    CLASSIFICATION,
    EMOTION_CLASSES,
    INTENT_CLASSES,
    SAFETY,
)
from evaluation.metrics import evaluate


def _classify_all():
    from app.services.nlp.service import NLPService

    nlp = NLPService()
    # Warm model once (cold start measured separately by test_eval_performance).
    nlp.classify("warmup hello")
    y_true_i, y_pred_i = [], []
    y_true_e, y_pred_e = [], []
    y_true_l, y_pred_l = [], []
    for ex in CLASSIFICATION:
        result = nlp.classify(ex["text"])
        y_true_i.append(ex["intent"])
        y_pred_i.append(result.intent.label)
        y_true_e.append(ex["emotion"])
        y_pred_e.append(result.emotion.label)
        y_true_l.append(ex["language"])
        # Language detector may return unknown; map for comparison only in report.
        y_pred_l.append(result.language)
    return y_true_i, y_pred_i, y_true_e, y_pred_e, y_true_l, y_pred_l


def _safety_report() -> dict:
    from app.services.safety.service import SafetyService

    svc = SafetyService()
    failures = []
    group_stats: dict[str, dict[str, int]] = {}
    for case in SAFETY:
        result = svc.detect(case["text"])
        g = group_stats.setdefault(
            case["group"], {"n": 0, "requires_ok": 0, "risk_ok": 0}
        )
        g["n"] += 1
        risk_ok = result.risk_level in case["allowed_risks"]
        requires_ok = result.requires_safety_response is case["expected_requires"]
        if risk_ok:
            g["risk_ok"] += 1
        if requires_ok:
            g["requires_ok"] += 1
        if not (risk_ok and requires_ok):
            failures.append(
                {
                    "text": case["text"],
                    "group": case["group"],
                    "expected_requires": case["expected_requires"],
                    "allowed_risks": case["allowed_risks"],
                    "got_risk": result.risk_level,
                    "got_requires": result.requires_safety_response,
                }
            )
    return {
        "cases": len(SAFETY),
        "failures": len(failures),
        "failure_detail": failures,
        "by_group": group_stats,
    }


def _response_false_positives() -> list[dict]:
    """Duration phrases must not become goodbye; real farewells must."""
    from app.services.nlp.service import NLPService
    from app.services.response.selector import ResponseSelector
    from app.services.response.types import ResponseContext
    from app.services.response.library import INTENT_RESPONSES

    def is_goodbye(text: str) -> bool:
        for variants in INTENT_RESPONSES["goodbye"].values():
            if text in variants:
                return True
        return False

    nlp = NLPService()
    selector = ResponseSelector()
    duration = ["long time se", "kaafi time se", "kaafi din se", "bahut time ho gaya"]
    farewells = ["bye", "bye bye", "goodbye", "cya", "ttyl", "gtg"]
    problems: list[dict] = []
    for text in duration:
        r = nlp.classify(text)
        ctx = ResponseContext(
            message=text,
            language=r.language,
            intent=r.intent.label,
            intent_confidence=r.intent.confidence_score,
            emotion=r.emotion.label,
            emotion_confidence=r.emotion.confidence_score,
            recent_messages=(),
        )
        out = selector.generate(ctx)
        if r.intent.label == "goodbye" or is_goodbye(out.text):
            problems.append(
                {"text": text, "intent": r.intent.label, "response": out.text}
            )
    for text in farewells:
        r = nlp.classify(text)
        if r.intent.label != "goodbye":
            problems.append(
                {"text": text, "intent": r.intent.label, "expected": "goodbye"}
            )
    return problems


def main() -> int:
    report: dict = {"dataset_size": len(CLASSIFICATION)}
    t0 = time.perf_counter()
    yi, yp_i, ye, yp_e, yl, yp_l = _classify_all()
    report["intent"] = evaluate(yi, yp_i, labels=list(INTENT_CLASSES))
    report["emotion"] = evaluate(ye, yp_e, labels=list(EMOTION_CLASSES))
    # Language detection: exact match rate (unknown counts as miss unless labeled).
    lang_correct = sum(1 for t, p in zip(yl, yp_l) if t == p)
    report["language"] = {
        "n": len(yl),
        "accuracy": round(lang_correct / len(yl), 4) if yl else 0.0,
        "confusion_pairs_wrong": [
            {"true": t, "pred": p} for t, p in zip(yl, yp_l) if t != p
        ],
    }
    report["safety"] = _safety_report()
    report["response_selection"] = {
        "duration_false_goodbye_problems": _response_false_positives()
    }
    report["wall_seconds"] = round(time.perf_counter() - t0, 3)

    out_path = Path(__file__).resolve().parents[2] / "docs" / "phase7_evaluation_metrics.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    def _line(name: str, m: dict) -> None:
        print(
            f"{name}: n={m['n']} acc={m['accuracy']} "
            f"macroF1={m['macro_f1']} weightedF1={m['weighted_f1']}"
        )

    _line("INTENT", report["intent"])
    _line("EMOTION", report["emotion"])
    print(
        f"LANGUAGE: n={report['language']['n']} acc={report['language']['accuracy']}"
    )
    print(
        f"SAFETY: cases={report['safety']['cases']} "
        f"failures={report['safety']['failures']}"
    )
    print(
        "RESPONSE: duration/farewell problems="
        f"{len(report['response_selection']['duration_false_goodbye_problems'])}"
    )
    print(f"Wrote {out_path}")
    return 0 if report["safety"]["failures"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
