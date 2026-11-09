# 용도: 의심 행위 후보와 비교 실험용 규칙 상태 판정을 생성한다.
"""Candidate extraction, not a production verdict. Baseline is evaluation-only."""
import re

from backend.app.schemas import Message, Status, Tag
from backend.app.services.preprocess import normalize

RULE_VERSION = "rules-v1"


def candidates(messages: list[Message]) -> list[dict]:
    found = []
    for message in messages:
        text = normalize(message.text)
        tags: list[Tag] = []
        payment = re.search(r"입금|송금|보내|납부|납입|충전|지불", text)
        if "출금" in text and re.search(r"세금|보증금|해제비|수수료|인증비", text) and payment:
            tags.append(Tag.WITHDRAWAL)
        if re.search(r"선입금|선납|선결제|보증료|신용점수.{0,12}(?:비용|수수료)", text) or (
            re.search(r"먼저|전에|선행", text) and payment and re.search(r"대출|보상|수익|부업|당첨|환급", text)
        ):
            tags.append(Tag.ADVANCE)
        if re.search(r"인증번호|비밀번호|otp|보안카드", text) and re.search(r"알려|공유|전달|보내|입력", text):
            tags.append(Tag.CREDENTIAL)
        if re.search(r"apk|원격제어|설치파일|외부앱", text) and re.search(r"설치|다운로드|실행", text):
            tags.append(Tag.APP)
        if re.search(r"원금|수익|수익률", text) and re.search(r"보장|확정|무조건|100%", text):
            tags.append(Tag.GUARANTEE)
        if re.search(r"오늘안|지금당장|마감|즉시", text):
            tags.append(Tag.URGENCY)
        for tag in tags:
            found.append({"message_id": message.id, "tag": tag.value, "quote": message.text})
    return found[:100]


def baseline_status(messages: list[Message]) -> Status:
    # Intentionally fixed before holdout evaluation. Misses are reported, not hidden.
    from backend.app.schemas import CORE_TAGS
    active = [m for m in messages if not re.search(
        r"조심|주의|예방|사기입니다|알려주지|보장하지|보장은하지|거절|하지마세요",
        normalize(m.text),
    )]
    if any(Tag(c["tag"]) in CORE_TAGS for c in candidates(active)):
        return Status.SUSPICIOUS
    if any(re.search(r"보증금|처리됩니다|참여하세요|입금해주세요", normalize(m.text)) for m in active):
        return Status.CONTEXT
    return Status.NO_CLEAR
