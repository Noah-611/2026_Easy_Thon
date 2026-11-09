// 용도: 브라우저 개인정보 가림, 대화 파싱과 원문 인용 강조를 수행한다.
import type { Message, Mode } from '../types'

// No network, storage, or analytics. One map per preview preserves repeated identities.
export function redactMessages(messages: Message[]): { messages: Message[]; count: number } {
  const replacements = new Map<string, string>()
  const counters = new Map<string, number>()
  let count = 0
  // Edits may introduce new identities after a previous preview. Reserve all
  // existing token numbers so different values cannot be assigned the same ID.
  for (const message of messages) {
    for (const text of [message.speaker, message.text]) {
      for (const match of text.matchAll(/\[(전화|계좌|주민번호|이메일|링크|인증정보)(\d{1,6})\]/g)) {
        counters.set(match[1], Math.max(counters.get(match[1]) ?? 0, Number(match[2])))
      }
    }
  }
  function token(kind: string, value: string) {
    const canonical = ['전화', '계좌', '주민번호'].includes(kind) ? value.replace(/\D/g, '') : value
    const key = `${kind}:${canonical}`
    if (!replacements.has(key)) {
      const next = (counters.get(kind) ?? 0) + 1
      counters.set(kind, next)
      replacements.set(key, `[${kind}${next}]`)
    }
    count++
    return replacements.get(key)!
  }
  function redact(text: string) {
    return text
      .replace(/[\w.+-]+@[\w.-]+\.[a-z]{2,}/gi, m => token('이메일', m))
      .replace(/(?:https?:\/\/|www\.)[^\s<>"']+/gi, m => token('링크', m))
      .replace(/\b(?:[a-z0-9-]+\.)+(?:com|net|org|kr|io|co|me)(?:[/?#][^\s<>"']*)?/gi, m => token('링크', m))
      .replace(/(?<!\d)\d{6}[- ]?[1-8]\d{6}(?!\d)/g, m => token('주민번호', m))
      .replace(/(?<!\d)(?:\+82[- .]?0?|0)(?:1[016789]|2|[3-6][1-5])[- .]?\d{3,4}[- .]?\d{4}(?!\d)/g, m => token('전화', m.replace(/^\+82[- .]?0?/, '0')))
      .replace(/(?<!\d)\d{2,6}-\d{2,6}-\d{2,6}(?:-\d{1,6})?(?!\d)/g, m => m.replace(/\D/g, '').length >= 10 ? token('계좌', m) : m)
      .replace(/((?:계좌(?:번호)?|입금계좌)\s*[:：=]?\s*)(\d{10,16})(?!\d)/g, (_, label: string, value: string) => label + token('계좌', value))
      .replace(/((?:인증번호|비밀번호|OTP)\s*[:：=]?\s*)([a-zA-Z0-9!@#$%^&*._-]{4,})/gi, (_, label: string, value: string) => label + token('인증정보', value))
  }
  return { messages: messages.map(m => ({ ...m, speaker: redact(m.speaker), text: redact(m.text) })), count }
}

export function parseInput(text: string, mode: Mode): Message[] {
  if (mode === 'single_message') return [{ id: 'm1', speaker: '발신자', text }]
  const result: Message[] = []
  for (const line of text.split('\n')) {
    if (!line.trim()) continue
    const match = /^(?!https?:)([^:\n]{1,80}):\s?(.*)$/.exec(line)
    if (match) result.push({ id: '', speaker: match[1].trim() || '미상', text: match[2] })
    else if (result.length) result[result.length - 1].text += '\n' + line
    else result.push({ id: '', speaker: '미상', text: line })
  }
  return result.map((m, i) => ({ ...m, id: `m${i + 1}` }))
}

export function inputError(messages: Message[]): string | null {
  if (!messages.length || messages.some(m => !m.text.trim() || !m.speaker.trim())) return '화자와 메시지 내용을 입력해 주세요.'
  if (messages.length > 100) return '메시지는 최대 100개입니다. 대화를 나누어 입력해 주세요.'
  if (messages.some(m => Array.from(m.speaker).length > 80)) return '화자 이름은 80자 이내로 입력해 주세요.'
  if (messages.reduce((n, m) => n + Array.from(m.text + m.speaker).length, 0) > 10000) return '가림 후 화자를 포함해 10,000자까지 분석할 수 있습니다. 내용을 나누어 입력해 주세요.'
  return null
}

// Find by literal strings, not Python offsets; emoji and repeated quotes remain correct.
export function highlightParts(text: string, quotes: string[]): { text: string; marked: boolean }[] {
  const intervals: [number, number][] = []
  for (const quote of new Set(quotes.filter(Boolean))) {
    let at = text.indexOf(quote)
    while (at >= 0) { intervals.push([at, at + quote.length]); at = text.indexOf(quote, at + 1) }
  }
  intervals.sort((a, b) => a[0] - b[0])
  const merged: [number, number][] = []
  for (const span of intervals) {
    const last = merged.at(-1)
    if (last && span[0] <= last[1]) last[1] = Math.max(last[1], span[1])
    else merged.push([...span])
  }
  let cursor = 0
  const parts: { text: string; marked: boolean }[] = []
  for (const [start, end] of merged) {
    if (start > cursor) parts.push({ text: text.slice(cursor, start), marked: false })
    parts.push({ text: text.slice(start, end), marked: true }); cursor = end
  }
  if (cursor < text.length) parts.push({ text: text.slice(cursor), marked: false })
  return parts
}
