# 용도: 모델의 인용·메시지 ID·관찰 순서를 원문과 대조한다.
from backend.app.errors import evidence_error
from backend.app.schemas import (
    AnalysisDraft, AnalyzeRequest, CORE_TAGS, Evidence, Signal, Span, Status,
)


def occurrences(text: str, quote: str) -> list[Span]:
    positions = []
    cursor = 0
    while (index := text.find(quote, cursor)) != -1:
        positions.append(Span(start=index, end=index + len(quote)))
        cursor = index + 1
    return positions


def validate_evidence(draft: AnalysisDraft, request: AnalyzeRequest) -> tuple[list[Signal], list[str]]:
    messages = {m.id: m.text for m in request.messages}
    order = {m.id: i for i, m in enumerate(request.messages)}
    signals = []
    for i, signal in enumerate(draft.signals):
        evidence = []
        for entry in signal.evidence:
            text = messages.get(entry.message_id)
            if text is None or not entry.quote.strip() or entry.quote not in text:
                raise evidence_error()
            evidence.append(Evidence(**entry.model_dump(), occurrences=occurrences(text, entry.quote)))
        signals.append(Signal(id=f"s{i+1}", tag=signal.tag, evidence=evidence, reason=signal.reason))
    for flow in draft.observed_flow:
        if any(mid not in messages for mid in flow.message_ids):
            raise evidence_error()
        indices = [order[mid] for mid in flow.message_ids]
        if indices != sorted(set(indices)):
            raise evidence_error()
    if draft.status == Status.NO_CLEAR and signals:
        raise evidence_error()
    if draft.status == Status.SUSPICIOUS and not any(s.tag in CORE_TAGS for s in signals):
        raise evidence_error()
    return signals, []
