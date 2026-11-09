# 용도: 문맥 분석, 원문 검증, 공식 자료 검색과 출처 설명을 연결한다.
import asyncio
import logging
from time import perf_counter

from backend.app.config import Settings
from backend.app.errors import AnalysisError
from backend.app.schemas import AnalysisDraft, AnalysisResponse, AnalyzeRequest, ExplanationDraft, Status
from backend.app.services.evidence import validate_evidence
from backend.app.services.llm import GeminiClient
from backend.app.services.preprocess import check_redaction
from backend.app.services.retrieval import KnowledgeBase
from backend.app.services.rules import candidates

logger = logging.getLogger("scamcheck.metrics")


async def analyze(request: AnalyzeRequest, request_id: str, config: Settings,
                  knowledge: KnowledgeBase | None, client: GeminiClient | None = None) -> AnalysisResponse:
    check_redaction(request.messages)
    if sum(len(m.text) + len(m.speaker) for m in request.messages) > config.max_input_chars:
        raise AnalysisError("INPUT_TOO_LONG", "입력이 너무 깁니다. 내용을 나누어 분석해 주세요.", 422)
    client = client or GeminiClient(config)
    started = perf_counter()
    try:
        # Detection is essential; optional source generation shares the remaining
        # request time and must never discard an already verified detection.
        async with asyncio.timeout(config.llm_timeout_seconds * 2):
            draft = await client.generate(AnalysisDraft, "detect", {
                "messages": [m.model_dump() for m in request.messages], "rule_candidates": candidates(request.messages),
            })
        signals, warnings = validate_evidence(draft, request)
        sources = []
        limitations = list(draft.limitations)
        mode = "rules_llm"
        retrieved = []
        if knowledge and signals:
            try:
                retrieved = knowledge.retrieve(signals)
            except (ValueError, OSError):
                warnings.append("공식 자료 검색에 실패하여 문맥 분석만 제공합니다.")
        if retrieved:
            try:
                remaining = max(0, config.llm_timeout_seconds * 2 - (perf_counter() - started))
                async with asyncio.timeout(min(config.llm_timeout_seconds, remaining)):
                    explanation = await client.generate(ExplanationDraft, "explain", {
                        "signals": [s.model_dump() for s in signals], "retrieved_chunks": retrieved,
                    })
                allowed = {(c["signal_id"], c["source_id"], c["chunk_id"]): c for c in retrieved}
                if any((e.signal_id, e.source_id, e.chunk_id) not in allowed for e in explanation.explanations):
                    raise ValueError("unretrieved citation")
                # Validate every source before attaching any links to signals.
                prepared = [(e, knowledge.public_source(allowed[(e.signal_id, e.source_id, e.chunk_id)]))
                            for e in explanation.explanations]
                by_id = {s.id: s for s in signals}
                for e, source in prepared:
                    signal = by_id[e.signal_id]
                    if e.source_id not in signal.source_ids:
                        signal.source_ids.append(e.source_id)
                    signal.source_explanation = e.explanation
                    if (source.id, source.chunk_id) not in {(s.id, s.chunk_id) for s in sources}:
                        sources.append(source)
                if sources:
                    mode = "rules_llm_rag"
            except (AnalysisError, ValueError, TimeoutError):
                warnings.append("공식 자료 설명을 검증하지 못해 출처 연결을 생략했습니다.")
        if not sources:
            limitations.append("관련 공식 근거 연결 부족: 이 결과에는 공식 자료가 연결되지 않았습니다.")
        limitations.append("텍스트만으로 발신자 신원·계좌 소유자·앱 악성 여부를 확인할 수 없습니다.")
        actions = ["입금·설치·정보 제공 전, 직접 찾은 공식 채널로 요청 내용을 확인하세요."] if draft.status != Status.NO_CLEAR else ["이 결과는 안전을 보장하지 않습니다. 발신자와 요청 목적을 별도로 확인하세요."]
        return AnalysisResponse(
            request_id=request_id, status=draft.status, categories=draft.categories,
            summary=draft.summary, signals=signals, observed_flow=draft.observed_flow,
            questions=draft.questions, actions=actions, sources=sources, limitations=limitations,
            analysis_mode=mode, warnings=warnings,
        )
    except TimeoutError:
        raise AnalysisError("MODEL_TIMEOUT", "분석 시간이 초과되었습니다. 잠시 뒤 다시 시도해 주세요.", 504) from None
    finally:
        # No text, model responses, source payloads, or credentials in logs.
        logger.info("request_id=%s elapsed_ms=%d calls=%d input_tokens=%d output_tokens=%d",
                    request_id, (perf_counter() - started) * 1000, client.calls, client.input_tokens, client.output_tokens)
