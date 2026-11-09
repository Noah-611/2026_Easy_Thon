# 용도: 실제 호출 없이 평가 오류의 분모 포함과 중단 결과 재개 동작을 검사한다.
import json
from types import SimpleNamespace

from backend.app.config import Settings
from backend.app.errors import AnalysisError
from backend.app.schemas import Status
from scripts import evaluate_llm


async def test_evaluation_retains_errors_and_resume_does_not_rerun_them(tmp_path, monkeypatch):
    (tmp_path / "data/evaluation").mkdir(parents=True)
    (tmp_path / "backend/app/prompts").mkdir(parents=True)
    (tmp_path / "backend/app/prompts/detect.txt").write_text("test prompt")
    cases = [{"id": "risk", "category": "PHISHING", "status": "suspicious_signals",
              "expected_tags": ["CREDENTIAL_REQUEST"],
              "messages": [{"id": "m1", "speaker": "미상", "text": "인증번호를 알려주세요."}]},
             {"id": "normal", "category": "NORMAL", "status": "no_clear_signals",
              "expected_tags": [], "messages": [{"id": "m1", "speaker": "친구", "text": "반가워."}]}]
    (tmp_path / "data/evaluation/regression.json").write_text(json.dumps(cases))
    monkeypatch.setattr(evaluate_llm, "ROOT", tmp_path)
    monkeypatch.setattr(evaluate_llm, "settings", lambda: Settings(llm_api_key="test-key", _env_file=None))
    calls = []

    async def analyze(_request, request_id, *_args):
        calls.append(request_id)
        if request_id == "risk":
            raise AnalysisError("INVALID_EVIDENCE", "test")
        return SimpleNamespace(status=Status.NO_CLEAR, signals=[], model_dump=lambda **_: {})

    monkeypatch.setattr(evaluate_llm, "analyze", analyze)
    args = SimpleNamespace(suite="regression", split="dev", case_id=None, rag=False, resume=False, interval=0)
    await evaluate_llm.run(args)
    destination = tmp_path / "artifacts/llm-regression.json"
    report = json.loads(destination.read_text())
    assert report["completed"] == report["planned"] == 2
    assert report["failures"] == report["failed_attempts"] == 1
    assert report["risk_recall"] == {"numerator": 0, "denominator": 1}
    assert report["normal_false_positives"] == {"numerator": 0, "denominator": 1}
    assert report["results"][0]["predicted"] == "ERROR"
    args.resume = True
    await evaluate_llm.run(args)
    assert calls == ["risk", "normal"]
    assert json.loads(destination.read_text()) == report
