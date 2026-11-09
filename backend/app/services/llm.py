# 용도: Gemini REST 호출, 생성 스키마 변환과 응답 검증을 수행한다.
import json
from pathlib import Path
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from backend.app.config import Settings
from backend.app.errors import AnalysisError

T = TypeVar("T", bound=BaseModel)
PROMPTS = Path(__file__).resolve().parents[1] / "prompts"


def provider_schema(schema: type[BaseModel]) -> dict:
    # Gemini supports a JSON Schema subset and rejects overly complex grammars.
    # Leave length/count bounds to local Pydantic validation. Nested maxItems
    # bounds multiply the constrained-decoding grammar size.
    def clean(value):
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()
                    if key not in {"pattern", "minLength", "maxLength", "minItems", "maxItems"}}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value
    return clean(schema.model_json_schema())


class GeminiClient:
    """No SDK retries, no tools, no URL fetching, no automatic provider fallback."""

    def __init__(self, config: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.config = config
        self.transport = transport
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    async def generate(self, schema: type[T], prompt: str, payload: dict) -> T:
        key = self.config.llm_api_key.get_secret_value()
        if self.config.llm_provider != "gemini" or not key:
            raise AnalysisError("LLM_NOT_CONFIGURED", "Gemini API 키가 설정되지 않았습니다. 로컬 .env의 LLM_API_KEY를 설정해 주세요.", 503)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.llm_model}:generateContent"
        system = (PROMPTS / f"{prompt}.txt").read_text()
        async with httpx.AsyncClient(timeout=self.config.llm_timeout_seconds, transport=self.transport,
                                    follow_redirects=False) as client:
            for attempt in range(2):
                body = {
                    "systemInstruction": {"parts": [{"text": system + ("\n이전 출력은 스키마 검증에 실패했다. 스키마에 맞는 JSON만 반환하라." if attempt else "")}]},
                    "contents": [{"role": "user", "parts": [{"text": json.dumps(payload, ensure_ascii=False)}]}],
                    "generationConfig": {"responseMimeType": "application/json",
                                         "responseJsonSchema": provider_schema(schema),
                                         "maxOutputTokens": 8000},
                }
                self.calls += 1
                try:
                    response = await client.post(url, json=body, headers={"x-goog-api-key": key})
                except httpx.TimeoutException:
                    raise AnalysisError("MODEL_TIMEOUT", "분석 시간이 초과되었습니다. 잠시 뒤 다시 시도해 주세요.", 504) from None
                except httpx.HTTPError:
                    raise AnalysisError("PROVIDER_UNAVAILABLE", "AI 서비스에 연결할 수 없습니다. 잠시 뒤 다시 시도해 주세요.", 503) from None
                if response.status_code == 429:
                    raise AnalysisError("PROVIDER_QUOTA", "무료 API 호출 한도에 도달했습니다. 잠시 뒤 또는 한도 갱신 후 시도해 주세요.", 429)
                if response.status_code == 503:
                    raise AnalysisError("PROVIDER_BUSY", "AI 서비스가 혼잡합니다. 잠시 뒤 다시 시도해 주세요.", 503)
                if response.status_code >= 400:
                    raise AnalysisError("PROVIDER_UNAVAILABLE", "AI 서비스 설정이나 사용 가능 상태를 확인해 주세요.", 503)
                try:
                    data = response.json()
                    usage = data.get("usageMetadata", {})
                    self.input_tokens += int(usage.get("promptTokenCount", 0))
                    self.output_tokens += int(usage.get("candidatesTokenCount", 0)) + int(usage.get("thoughtsTokenCount", 0))
                    candidate = data["candidates"][0]
                    if candidate.get("finishReason") != "STOP":
                        raise ValueError("incomplete response")
                    text = "".join(p.get("text", "") for p in candidate["content"]["parts"] if not p.get("thought"))
                    return schema.model_validate_json(text)
                except (KeyError, IndexError, TypeError, ValueError, ValidationError):
                    if attempt:
                        raise AnalysisError("INVALID_MODEL_RESPONSE", "AI 응답을 검증하지 못했습니다. 다시 분석해 주세요.") from None
        raise AnalysisError("INVALID_MODEL_RESPONSE", "AI 응답을 검증하지 못했습니다.")
