# 용도: 입력 계약, 길이·동의 제약과 합성 예시의 유효성을 검사한다.
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.schemas import AnalyzeRequest, CORE_TAGS, Example


def payload(text="문자 내용", **overrides):
    return {"input_mode": "single_message", "redaction_confirmed": True, "demo_data_confirmed": True,
            "messages": [{"id": "m1", "speaker": "미상", "text": text}], **overrides}


def test_multiline_single_message_and_unicode_preserved():
    original = "  😀 안내\n출금하려면 먼저 보내주세요.\n"
    request = AnalyzeRequest.model_validate(payload(original))
    assert request.messages[0].text == original
    assert len(request.messages) == 1


@pytest.mark.parametrize("text", ["", " \n\t", "가" * 10000])
def test_blank_and_total_length_rejected(text):
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(payload(text))


@pytest.mark.parametrize("overrides", [
    {"redaction_confirmed": False},
    {"redaction_confirmed": "true"},
    {"demo_data_confirmed": False},
    {"unexpected": "field"},
    {"messages": []},
    {"input_mode": "invalid"},
])
def test_invalid_contract_rejected(overrides):
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(payload(**overrides))


def test_message_ids_unique_and_single_message_mode_enforced():
    message = payload()["messages"][0]
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(payload(input_mode="conversation", messages=[message, message]))
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(payload(messages=[message, {**message, "id": "m2"}]))


def test_message_limit_and_speaker_validation():
    messages = [{"id": f"m{i+1}", "speaker": "가", "text": "나"} for i in range(101)]
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(payload(input_mode="conversation", messages=messages))
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(payload(messages=[{"id": "m1", "speaker": " ", "text": "나"}]))


def test_six_synthetic_examples_cover_core_signals():
    path = Path(__file__).resolve().parents[2] / "data/examples/demo.json"
    examples = [Example.model_validate(e) for e in json.loads(path.read_text())]
    assert len(examples) == len({e.id for e in examples}) == 6
    assert CORE_TAGS <= {tag for e in examples for tag in e.expected_tags}
    for example in examples:
        AnalyzeRequest(input_mode=example.input_mode, redaction_confirmed=True,
                       demo_data_confirmed=True, messages=example.messages)


def test_evaluation_comments_preserve_frozen_training_split():
    from collections import Counter
    from scripts.baseline import fingerprint, load_cases
    rows = load_cases()
    assert Counter(row["split"] for row in rows) == {"train": 36, "dev": 40, "holdout": 20}
    assert fingerprint([row for row in rows if row["split"] == "train"]) == "a51f16a56243b2800cefbf71a5c803b1aaf99380f1d773b8c098aa6290b06f92"


def test_live_regression_fixtures_have_valid_redacted_inputs():
    from backend.app.services.preprocess import check_redaction
    path = Path(__file__).resolve().parents[2] / "data/evaluation/regression.json"
    cases = json.loads(path.read_text())
    assert len(cases) == len({row["id"] for row in cases}) == 14
    for row in cases:
        request = AnalyzeRequest(input_mode="conversation" if len(row["messages"]) > 1 else "single_message",
                                 redaction_confirmed=True, demo_data_confirmed=True, messages=row["messages"])
        check_redaction(request.messages)
