# 용도: 분석·예시·상태 API와 요청 크기·횟수 및 개인정보 보호 처리를 제공한다.
import json
from collections import deque
from datetime import UTC, datetime
from functools import lru_cache
from time import monotonic
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from backend.app.config import ROOT, Settings, settings
from backend.app.errors import AnalysisError
from backend.app.schemas import AnalysisResponse, AnalyzeRequest, Example
from backend.app.services.analysis import analyze
from backend.app.services.retrieval import KnowledgeBase

app = FastAPI(title="ScamCheck", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings().allowed_origins,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


class Budget:
    """Single-process local demo cap. No IP or message storage."""
    def __init__(self):
        self.recent = deque()
        self.day = ""
        self.daily = 0

    def consume(self, config: Settings):
        now = monotonic()
        while self.recent and self.recent[0] <= now - 60:
            self.recent.popleft()
        day = datetime.now(UTC).date().isoformat()
        if self.day != day:
            self.day, self.daily = day, 0
        if len(self.recent) >= config.max_requests_per_minute or self.daily >= config.max_requests_per_day:
            raise AnalysisError("RATE_LIMITED", "시연 서버의 요청 한도에 도달했습니다. 잠시 뒤 또는 다음 날 다시 시도해 주세요.", 429)
        self.recent.append(now)
        self.daily += 1


budget = Budget()


@lru_cache
def knowledge() -> KnowledgeBase | None:
    try:
        return KnowledgeBase()
    except (OSError, ValueError, KeyError):
        return None


def error_response(request: Request, status: int, code: str, message: str):
    return JSONResponse(status_code=status, content={"code": code, "message": message,
                         "request_id": getattr(request.state, "request_id", "unknown")},
                        headers={"Cache-Control": "no-store"})


@app.middleware("http")
async def privacy_and_size(request: Request, call_next):
    request.state.request_id = uuid4().hex
    if request.method == "POST":
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 131072:
                return error_response(request, 422, "REQUEST_TOO_LARGE", "요청이 너무 큽니다. 내용을 나누어 입력해 주세요.")
            chunks.append(chunk)
        request._body = b"".join(chunks)
    try:
        response = await call_next(request)
    except Exception:
        # Do not expose exception repr, which may contain request or model contents.
        return error_response(request, 500, "INTERNAL_ERROR", "요청을 처리하지 못했습니다. 다시 시도해 주세요.")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(RequestValidationError)
async def invalid_input(request: Request, _error):
    return error_response(request, 422, "INVALID_INPUT", "입력 형식·길이·메시지 수와 가림·가상 데이터 확인을 점검해 주세요.")


@app.exception_handler(AnalysisError)
async def analysis_error(request: Request, error: AnalysisError):
    return error_response(request, error.status, error.code, error.message)


@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException):
    return error_response(request, error.status_code, "HTTP_ERROR", "요청 경로와 방식을 확인해 주세요.")


@app.get("/health")
async def health(config: Settings = Depends(settings)):
    kb = knowledge()
    return {"status": "ok", "analysis_configured": config.llm_provider == "gemini" and bool(config.llm_api_key.get_secret_value()),
            "provider": config.llm_provider, "synthetic_demo_only": True, "knowledge_sources": len(kb.sources) if kb else 0}


@app.get("/api/v1/examples", response_model=list[Example])
async def examples():
    return json.loads((ROOT / "data/examples/demo.json").read_text())


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
async def analyze_endpoint(payload: AnalyzeRequest, request: Request, config: Settings = Depends(settings)):
    if not config.llm_api_key.get_secret_value():
        raise AnalysisError("LLM_NOT_CONFIGURED", "Gemini API 키가 설정되지 않았습니다. 로컬 .env의 LLM_API_KEY를 설정해 주세요.", 503)
    budget.consume(config)
    return await analyze(payload, request.state.request_id, config, knowledge())
