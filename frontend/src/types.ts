// 용도: 화면에서 사용하는 API 타입과 상태·태그 표시 문구를 정의한다.
export type Status = 'suspicious_signals' | 'needs_context' | 'no_clear_signals'
export type Mode = 'single_message' | 'conversation'
export type Message = { id: string; speaker: string; text: string }
export type Example = { id: string; title: string; description: string; input_mode: Mode; messages: Message[] }
export type Signal = {
  id: string; tag: string; reason: string; source_ids: string[]; source_explanation: string | null
  evidence: { message_id: string; quote: string; occurrences: { start: number; end: number }[] }[]
}
export type Analysis = {
  request_id: string; status: Status; categories: string[]; summary: string; signals: Signal[]
  observed_flow: { message_ids: string[]; description: string }[]
  questions: string[]; actions: string[]; limitations: string[]; warnings: string[]
  analysis_mode: 'rules_llm' | 'rules_llm_rag'
  sources: { id: string; chunk_id: string; title: string; publisher: string; url: string; checked_at: string; excerpt: string }[]
}

export const statusText: Record<Status, string> = {
  suspicious_signals: '의심 신호 발견', needs_context: '추가 맥락 필요', no_clear_signals: '뚜렷한 의심 신호 미발견',
}
export const tagText: Record<string, string> = {
  ADVANCE_PAYMENT: '선입금 요구', WITHDRAWAL_PREPAYMENT: '출금 전 추가 납부', CREDENTIAL_REQUEST: '인증정보 요구',
  EXTERNAL_APP: '외부 앱 설치', GUARANTEED_RETURN: '수익 보장 주장', IMPERSONATION_CLAIM: '신원 주장',
  URGENCY_PRESSURE: '긴급성 압박', OFF_PLATFORM_PAYMENT: '별도 계좌 입금', LINK_OR_INFO_REQUEST: '링크·정보 입력',
}
