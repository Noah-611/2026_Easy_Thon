// 용도: 개인정보 가림, 입력 제한과 유니코드 인용 강조를 검사한다.
import { describe, expect, it } from 'vitest'
import { redactMessages, parseInput, inputError, highlightParts } from './redact'

describe('redaction before network', () => {
  it('preserves existing token IDs and gives edited identities distinct numbers across messages', () => {
    const result = redactMessages([
      { id: 'm1', speaker: '[전화3]', text: '[전화1] 새 번호 010-9876-5432' },
      { id: 'm2', speaker: '미상', text: '같은 새 번호 01098765432' },
    ])
    expect(result.messages[0].text).toBe('[전화1] 새 번호 [전화4]')
    expect(result.messages[1].text).toBe('같은 새 번호 [전화4]')
    expect(result.messages[0].speaker).toBe('[전화3]')
  })
  it('masks identities consistently across speakers and text without changing amounts', () => {
    const result = redactMessages([
      { id: 'm1', speaker: '010-1234-5678', text: '01012345678 계좌 110-123-456789 보증금 20만 원, 수익률 20%, 2026-11-09' },
      { id: 'm2', speaker: '미상', text: '110-123-456789' },
    ])
    expect(result.messages[0].speaker).toBe('[전화1]')
    expect(result.messages[0].text).toContain('[전화1]')
    expect(result.messages[0].text).toContain('보증금 20만 원, 수익률 20%')
    expect(result.messages[0].text).toContain('2026-11-09')
    expect(result.messages[1].text).toBe('[계좌1]')
  })
  it('masks URL secrets, email, resident IDs and authentication values', () => {
    const value = redactMessages([{ id: 'm1', speaker: '미상', text: 'a@example.com https://example.com/a?token=secret 900101-1234567 인증번호: 123456' }]).messages[0].text
    for (const secret of ['a@example.com', 'example.com', 'secret', '900101', '123456']) expect(value).not.toContain(secret)
  })
  it('preserves multiline single text and conversation speakers', () => {
    expect(parseInput('첫째\n둘째', 'single_message')).toHaveLength(1)
    expect(parseInput('상담원: 첫째\n이어서\n고객: 둘째', 'conversation')).toEqual([
      { id: 'm1', speaker: '상담원', text: '첫째\n이어서' }, { id: 'm2', speaker: '고객', text: '둘째' },
    ])
  })
  it('rejects empty and over-limit inputs instead of truncating', () => {
    expect(inputError([{ id: 'm1', speaker: '미상', text: ' ' }])).not.toBeNull()
    expect(inputError([{ id: 'm1', speaker: '미상', text: '가'.repeat(10000) }])).not.toBeNull()
  })
  it('highlights every occurrence with emoji and merges overlaps', () => {
    const parts = highlightParts('😀 보증금 먼저 보증금', ['보증금', '보증금 먼저'])
    expect(parts.filter(p => p.marked).map(p => p.text)).toEqual(['보증금 먼저', '보증금'])
    expect(parts.map(p => p.text).join('')).toBe('😀 보증금 먼저 보증금')
  })
})
