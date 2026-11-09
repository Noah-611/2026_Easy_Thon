# 용도: 가상 예시 한 건으로 실제 Gemini 연결과 응답·인용을 검증한다.
"""Send one repository-owned synthetic example and validate the live response."""
import asyncio
import json
from time import perf_counter

import httpx

from backend.app.config import ROOT, settings
from backend.app.errors import AnalysisError
from backend.app.schemas import AnalysisDraft, AnalyzeRequest
from backend.app.services.evidence import validate_evidence
from backend.app.services.llm import GeminiClient
from backend.app.services.rules import candidates


class DiagnosticTransport(httpx.AsyncHTTPTransport):
    """Expose only fixed diagnostic flags, never upstream bodies or credentials."""
    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        if response.status_code >= 400:
            await response.aread()
            try:
                error = response.json().get("error", {})
                message = str(error.get("message", "")).lower()
                print(json.dumps({"http_status": response.status_code,
                                  "invalid_key": "api key not valid" in message or "api_key_invalid" in message,
                                  "model_not_found": "not found" in message and "model" in message,
                                  "schema_error": "schema" in message or "generation_config" in message,
                                  "permission_error": "permission" in message or "leaked" in message,
                                  "quota_error": "quota" in message or "resource_exhausted" in message,
                                  "service_disabled": "disabled" in message or "has not been used" in message}))
            except (ValueError, TypeError, AttributeError):
                print(json.dumps({"http_status": response.status_code}))
        return response


async def run() -> int:
    config = settings()
    if not config.llm_api_key.get_secret_value():
        print("LLM_API_KEY is missing. No requests made.")
        return 1
    example = json.loads((ROOT / "data/examples/demo.json").read_text(encoding="utf-8"))[0]
    request = AnalyzeRequest(input_mode=example["input_mode"], messages=example["messages"],
                             redaction_confirmed=True, demo_data_confirmed=True)
    client = GeminiClient(config, DiagnosticTransport())
    started = perf_counter()
    try:
        async with asyncio.timeout(config.llm_timeout_seconds * 2):
            draft = await client.generate(AnalysisDraft, "detect", {
                "messages": [m.model_dump() for m in request.messages],
                "rule_candidates": candidates(request.messages),
            })
        signals, _ = validate_evidence(draft, request)
    except (AnalysisError, TimeoutError) as error:
        print(json.dumps({"ok": False, "model": config.llm_model,
                          "error_code": error.code if isinstance(error, AnalysisError) else "MODEL_TIMEOUT",
                          "calls": client.calls}, ensure_ascii=False))
        return 1
    matches = draft.status.value == example["expected_status"] and set(example["expected_tags"]).issubset(
        {signal.tag.value for signal in signals})
    print(json.dumps({"ok": matches, "model": config.llm_model, "fixture": example["id"],
                      "status": draft.status.value, "tags": [signal.tag.value for signal in signals],
                      "schema_valid": True, "evidence_valid": True, "expected_result_matches": matches,
                      "elapsed_ms": round((perf_counter() - started) * 1000), "calls": client.calls,
                      "input_tokens": client.input_tokens, "output_tokens": client.output_tokens},
                     ensure_ascii=False, indent=2))
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
