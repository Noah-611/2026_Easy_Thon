// 용도: 가림과 합성 데이터 동의가 포함된 분석 요청을 서버에 전송한다.
import type { Analysis, Message, Mode } from '../types'

export async function analyze(mode: Mode, messages: Message[], signal: AbortSignal): Promise<Analysis> {
  let response: Response
  try {
    response = await fetch('/api/v1/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, cache: 'no-store', signal,
      body: JSON.stringify({ input_mode: mode, redaction_confirmed: true, demo_data_confirmed: true, messages }),
    })
  } catch (error) {
    if (signal.aborted) throw error
    throw new Error('서버에 연결하지 못했습니다. 백엔드 실행 상태를 확인해 주세요.')
  }
  let data
  try { data = await response.json() } catch { throw new Error('서버 응답을 읽지 못했습니다. 다시 시도해 주세요.') }
  if (!response.ok) throw new Error(typeof data.message === 'string' ? data.message : '분석 요청에 실패했습니다.')
  return data as Analysis
}
