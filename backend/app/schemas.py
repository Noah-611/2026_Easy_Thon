# 용도: 입력, 분석 근거, 출처와 응답의 공통 데이터 계약을 검증한다.
"""Shared public contracts. Offsets are server-computed Unicode code-point indices."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Status(StrEnum):
    SUSPICIOUS = "suspicious_signals"
    CONTEXT = "needs_context"
    NO_CLEAR = "no_clear_signals"


class Category(StrEnum):
    PHISHING = "PHISHING"
    LOAN = "LOAN_SCAM"
    INVESTMENT = "INVESTMENT_SCAM"
    OTHER = "OTHER_SCAM"


class Tag(StrEnum):
    ADVANCE = "ADVANCE_PAYMENT"
    CREDENTIAL = "CREDENTIAL_REQUEST"
    APP = "EXTERNAL_APP"
    GUARANTEE = "GUARANTEED_RETURN"
    WITHDRAWAL = "WITHDRAWAL_PREPAYMENT"
    IMPERSONATION = "IMPERSONATION_CLAIM"
    URGENCY = "URGENCY_PRESSURE"
    OFF_PLATFORM = "OFF_PLATFORM_PAYMENT"
    LINK = "LINK_OR_INFO_REQUEST"


CORE_TAGS = {Tag.ADVANCE, Tag.CREDENTIAL, Tag.APP, Tag.GUARANTEE, Tag.WITHDRAWAL}
MessageId = Annotated[str, Field(pattern=r"^m[1-9][0-9]{0,3}$")]
ShortText = Annotated[str, Field(min_length=1, max_length=500)]


class Message(StrictModel):
    id: MessageId
    speaker: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=10000)

    @field_validator("speaker", "text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("blank text")
        return value  # Preserve the exact text for evidence matching.


class AnalyzeRequest(StrictModel):
    input_mode: Literal["single_message", "conversation"]
    redaction_confirmed: Literal[True]
    demo_data_confirmed: Literal[True]
    messages: list[Message] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def check_messages(self):
        if len({m.id for m in self.messages}) != len(self.messages):
            raise ValueError("duplicate message IDs")
        if self.input_mode == "single_message" and len(self.messages) != 1:
            raise ValueError("single_message requires exactly one message")
        if sum(len(m.text) + len(m.speaker) for m in self.messages) > 10000:
            raise ValueError("input exceeds 10000 characters including speakers")
        return self


class EvidenceDraft(StrictModel):
    message_id: MessageId
    quote: str = Field(min_length=1, max_length=1500)


class SignalDraft(StrictModel):
    tag: Tag
    evidence: list[EvidenceDraft] = Field(min_length=1, max_length=8)
    reason: ShortText


class Flow(StrictModel):
    message_ids: list[MessageId] = Field(min_length=1, max_length=100)
    description: ShortText


class AnalysisDraft(StrictModel):
    status: Status
    categories: list[Category] = Field(max_length=4)
    summary: ShortText
    signals: list[SignalDraft] = Field(max_length=12)
    observed_flow: list[Flow] = Field(max_length=10)
    questions: list[ShortText] = Field(max_length=5)
    limitations: list[ShortText] = Field(max_length=5)


class Span(StrictModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)


class Evidence(EvidenceDraft):
    occurrences: list[Span]


class Signal(StrictModel):
    id: str
    tag: Tag
    evidence: list[Evidence]
    reason: str
    source_ids: list[str] = Field(default_factory=list)
    source_explanation: str | None = None


class Source(StrictModel):
    id: str
    chunk_id: str
    title: str
    publisher: str
    url: str
    checked_at: str
    excerpt: str


class SourceExplanation(StrictModel):
    signal_id: str
    source_id: str
    chunk_id: str
    explanation: ShortText


class ExplanationDraft(StrictModel):
    explanations: list[SourceExplanation] = Field(max_length=12)


class AnalysisResponse(StrictModel):
    request_id: str
    schema_version: Literal["1.0"] = "1.0"
    status: Status
    categories: list[Category]
    summary: str
    signals: list[Signal]
    observed_flow: list[Flow]
    questions: list[str]
    actions: list[str]
    sources: list[Source]
    limitations: list[str]
    analysis_mode: Literal["rules_llm", "rules_llm_rag"]
    warnings: list[str]


class Example(StrictModel):
    id: str
    title: str
    description: str
    input_mode: Literal["single_message", "conversation"]
    messages: list[Message]
    expected_status: Status
    expected_tags: list[Tag]
    rationale: str


class ErrorResponse(StrictModel):
    code: str
    message: str
    request_id: str
