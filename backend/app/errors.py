# 용도: 사용자에게 안전하게 전달할 API 오류 코드와 메시지를 정의한다.
class AnalysisError(Exception):
    """Only these reviewed messages may cross the API boundary."""

    def __init__(self, code: str, message: str, status: int = 502):
        super().__init__(code)
        self.code, self.message, self.status = code, message, status


def evidence_error():
    return AnalysisError("INVALID_EVIDENCE", "원문과 일치하는 분석 근거를 확인하지 못했습니다. 다시 분석해 주세요.")
