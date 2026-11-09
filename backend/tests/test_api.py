# 용도: 상태·예시 API, 비밀정보 보호, 입력 오류와 요청 한도를 검사한다.
import httpx
import pytest

from backend.app.config import Settings, settings
from backend.app.main import app, Budget


@pytest.fixture
async def client():
    app.dependency_overrides[settings] = lambda: Settings(llm_api_key="", _env_file=None)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def test_health_and_examples_work_without_api_key(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["analysis_configured"] is False
    assert response.json()["knowledge_sources"] == 5
    assert response.headers["cache-control"] == "no-store"
    examples = await client.get("/api/v1/examples")
    assert len(examples.json()) == 6


async def test_missing_key_is_error_not_safe_result(client):
    response = await client.post("/api/v1/analyze", json={
        "input_mode": "single_message", "redaction_confirmed": True, "demo_data_confirmed": True,
        "messages": [{"id": "m1", "speaker": "미상", "text": "분석 예시"}],
    })
    assert response.status_code == 503
    assert response.json()["code"] == "LLM_NOT_CONFIGURED"
    assert set(response.json()) == {"code", "message", "request_id"}


async def test_validation_does_not_echo_user_input(client):
    response = await client.post("/api/v1/analyze", json={"private": "sensitive-user-secret"})
    assert response.status_code == 422
    assert "sensitive-user-secret" not in response.text
    assert set(response.json()) == {"code", "message", "request_id"}


async def test_oversized_body_rejected_without_echo(client):
    response = await client.post("/api/v1/analyze", content=b"x" * 140000)
    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_TOO_LARGE"


def test_request_budget_is_bounded():
    from backend.app.errors import AnalysisError
    budget = Budget()
    config = Settings(max_requests_per_minute=1, _env_file=None)
    budget.consume(config)
    with pytest.raises(AnalysisError) as info:
        budget.consume(config)
    assert info.value.status == 429


async def test_analysis_endpoint_returns_verified_contract(client, monkeypatch):
    import backend.app.main as main_module
    from backend.app.services.analysis import analyze
    from backend.app.schemas import AnalysisResponse
    from backend.tests.test_analysis import FakeClient, request
    app.dependency_overrides[settings] = lambda: Settings(llm_api_key="test-only-key", _env_file=None)
    async def fixture_analysis(payload, request_id, config, knowledge):
        return await analyze(payload, request_id, config, knowledge, FakeClient())
    monkeypatch.setattr(main_module, "analyze", fixture_analysis)
    response = await client.post("/api/v1/analyze", json=request().model_dump(mode="json"))
    assert response.status_code == 200
    result = AnalysisResponse.model_validate(response.json())
    assert response.headers["x-request-id"] == result.request_id
    assert result.analysis_mode == "rules_llm_rag"
    evidence = result.signals[0].evidence[0]
    for span in evidence.occurrences:
        assert request().messages[0].text[span.start:span.end] == evidence.quote
    assert result.signals[0].source_ids == [result.sources[0].id]


async def test_invalid_evidence_endpoint_returns_error_without_analysis(client, monkeypatch):
    import backend.app.main as main_module
    from backend.app.services.analysis import analyze
    from backend.tests.test_analysis import FakeClient, request
    app.dependency_overrides[settings] = lambda: Settings(llm_api_key="test-only-key", _env_file=None)
    async def fixture_analysis(payload, request_id, config, knowledge):
        return await analyze(payload, request_id, config, knowledge, FakeClient())
    monkeypatch.setattr(main_module, "analyze", fixture_analysis)
    response = await client.post("/api/v1/analyze", json=request("원문에 없는 인용을 생성하는 테스트").model_dump(mode="json"))
    assert response.status_code == 502
    assert response.json()["code"] == "INVALID_EVIDENCE"
    assert set(response.json()) == {"code", "message", "request_id"}
