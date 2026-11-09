# 용도: 텍스트 정규화와 서버의 잔여 개인정보 패턴 검사를 수행한다.
import re
import unicodedata

from backend.app.errors import AnalysisError
from backend.app.schemas import Message

# Supplemental rejection only. Browser review remains essential.
SENSITIVE = re.compile(
    r"(?<!\d)(?:0(?:1[016789]|2|[3-6][1-5])[- .]?\d{3,4}[- .]?\d{4})(?!\d)"
    r"|(?<!\d)\d{6}[- ]?[1-8]\d{6}(?!\d)"
    r"|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"
    r"|https?://[^\s]+|www\.[^\s]+"
    r"|(?:인증번호|비밀번호|OTP|계좌번호)\s*[:：=]?\s*\d{4,}", re.IGNORECASE
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).lower()


def check_redaction(messages: list[Message]) -> None:
    def residual(text: str) -> bool:
        accounts = re.findall(r"(?<!\d)\d{2,6}-\d{2,6}-\d{2,6}(?:-\d{1,6})?(?!\d)", text)
        return bool(SENSITIVE.search(text)) or any(len(re.sub(r"\D", "", a)) >= 10 for a in accounts)
    if any(residual(m.text) or residual(m.speaker) for m in messages):
        raise AnalysisError("REDACTION_REQUIRED", "연락처·계좌·인증정보 또는 전체 링크가 남아 있습니다. 가림 내용을 다시 확인해 주세요.", 422)


def serialize(messages: list[Message]) -> str:
    return "\n".join(f"{m.id} | {m.speaker}: {m.text}" for m in messages)
