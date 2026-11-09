// 용도: 입력·가림 검토·전송 동의·분석 결과의 사용자 화면을 구성한다.
import { useEffect, useRef, useState } from 'react'
import { ArrowRight, ArrowLeft, ShieldCheck, LockKeyhole, MessageSquareText, MessagesSquare, RotateCcw, Check, ScanText, BookOpen, AlertTriangle, Plus, Trash2, LoaderCircle, ExternalLink, ChevronRight } from 'lucide-react'
import type { Analysis, Example, Message, Mode } from './types'
import { statusText, tagText } from './types'
import { analyze } from './lib/api'
import { highlightParts, inputError, parseInput, redactMessages } from './lib/redact'

export default function App() {
  const [step, setStep] = useState(0)
  const [mode, setMode] = useState<Mode>('single_message')
  const [raw, setRaw] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [redacted, setRedacted] = useState(0)
  const [confirmed, setConfirmed] = useState(false)
  const [examples, setExamples] = useState<Example[]>([])
  const [result, setResult] = useState<Analysis | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [configured, setConfigured] = useState<boolean | null>(null)
  const request = useRef<AbortController | null>(null)
  const resultHeading = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/v1/examples', { signal: controller.signal, cache: 'no-store' }).then(r => {
      if (!r.ok) throw new Error()
      return r.json()
    }).then(setExamples).catch(() => { if (!controller.signal.aborted) setError('예시를 불러오지 못했습니다. 백엔드 실행 상태를 확인해 주세요.') })
    fetch('/health', { signal: controller.signal, cache: 'no-store' }).then(r => r.json()).then(d => setConfigured(Boolean(d.analysis_configured))).catch(() => {})
    return () => { controller.abort(); request.current?.abort() }
  }, [])

  useEffect(() => { if (step === 2) resultHeading.current?.focus() }, [step])

  function reset() {
    request.current?.abort(); request.current = null
    setRaw(''); setMessages([]); setResult(null); setError(''); setConfirmed(false); setBusy(false); setStep(0); setRedacted(0)
  }
  function loadExample(example: Example) {
    reset(); setMode(example.input_mode)
    setRaw(example.input_mode === 'single_message' ? example.messages[0].text : example.messages.map(m => `${m.speaker}: ${m.text}`).join('\n'))
  }
  function preview() {
    setError('')
    if (!raw.trim()) { setError('분석할 가상 문구를 입력하거나 예시를 선택해 주세요.'); return }
    if (raw.length > 60000) { setError('입력이 너무 깁니다. 대화를 나누어 입력해 주세요.'); return }
    const clean = redactMessages(parseInput(raw, mode))
    const issue = inputError(clean.messages)
    if (issue) { setError(issue); return }
    setMessages(clean.messages); setRedacted(clean.count); setRaw(''); setConfirmed(false); setStep(1)
  }
  function edit(index: number, field: 'speaker' | 'text', value: string) {
    setMessages(current => current.map((m, i) => i === index ? { ...m, [field]: value } : m)); setConfirmed(false)
  }
  async function submit() {
    if (request.current || !confirmed) return
    setError('')
    const clean = redactMessages(messages)
    if (clean.count > 0) {
      setMessages(clean.messages); setRedacted(n => n + clean.count); setConfirmed(false)
      setError('수정한 내용에서 개인정보 패턴을 다시 가렸습니다. 내용을 검토하고 확인해 주세요.'); return
    }
    const issue = inputError(messages)
    if (issue) { setError(issue); return }
    const controller = new AbortController(); request.current = controller; setBusy(true)
    const timer = setTimeout(() => controller.abort('timeout'), 100000)
    try {
      const response = await analyze(mode, messages, controller.signal)
      if (request.current !== controller) return
      setResult(response); setStep(2)
    } catch (e) {
      if (request.current === controller) setError(controller.signal.aborted ? '요청 시간이 초과되었습니다. 다시 시도해 주세요.' : e instanceof Error ? e.message : '분석에 실패했습니다.')
    } finally {
      clearTimeout(timer)
      if (request.current === controller) { request.current = null; setBusy(false) }
    }
  }

  return <div className="app-shell">
    <header className="site-header">
      <a className="brand" href="#" onClick={e => { e.preventDefault(); reset() }} aria-label="ScamCheck 처음으로"><span className="brand-icon"><ShieldCheck size={23} /></span>ScamCheck<span className="beta">MVP</span></a>
      <span className="header-note"><LockKeyhole size={14} /> 대화 저장 없이, 필요한 만큼만</span>
    </header>
    <main>
      <div className="eyebrow"><span /> 문자·대화 의심 신호 분석</div>
      <section className="intro">
        <div><h1>보내기 전에,<br /><em>한 번 더 확인하세요.</em></h1><p>입금, 앱 설치, 정보 제공을 요구하는 문구.<br className="mobile-break" /> 의심되는 이유를 원문과 함께 살펴보세요.</p></div>
        <div className="intro-mark" aria-hidden="true"><MessageSquareText size={54} strokeWidth={1.2} /><span><ShieldCheck size={27} /></span><i className="dot one" /><i className="dot two" /></div>
      </section>
      <div className="demo-notice"><span className="pill">무료 시연</span><span>가상 문구로 체험해 주세요. Gemini 무료 API의 입력·출력은 서비스 개선에 사용될 수 있습니다.</span><a href="https://ai.google.dev/gemini-api/terms" target="_blank" rel="noreferrer">데이터 정책 <ExternalLink size={12} /></a></div>
      <nav className="steps" aria-label="분석 단계">{['내용 입력', '가림 확인', '분석 결과'].map((name, i) => <div key={name} className={step === i ? 'step active' : step > i ? 'step done' : 'step'} aria-current={step === i ? 'step' : undefined}><span>{step > i ? <Check size={14} /> : `0${i + 1}`}</span>{name}{i < 2 && <ChevronRight size={15} className="step-chevron" />}</div>)}</nav>
      <div className="workspace">
        <section className="main-card">
          <div className="card-heading"><div><span className="section-index">{step === 0 ? '01 / INPUT' : step === 1 ? '02 / REVIEW' : '03 / RESULT'}</span><h2 ref={resultHeading} tabIndex={-1}>{step === 0 ? '어떤 내용을 확인할까요?' : step === 1 ? '전송할 내용을 확인해 주세요' : '문구에서 찾은 신호'}</h2></div><button className="icon-button" onClick={reset} title="입력·결과 모두 삭제" aria-label="입력·결과 모두 삭제"><RotateCcw size={18} /></button></div>
          {error && <div className="error-box" role="alert"><AlertTriangle size={18} /><span>{error}</span></div>}
          {step === 0 && <>
            <div className="mode-tabs" role="group" aria-label="입력 방식"><button aria-pressed={mode === 'single_message'} className={mode === 'single_message' ? 'selected' : ''} onClick={() => setMode('single_message')}><MessageSquareText size={17} />문자 한 건</button><button aria-pressed={mode === 'conversation'} className={mode === 'conversation' ? 'selected' : ''} onClick={() => setMode('conversation')}><MessagesSquare size={17} />대화 여러 건</button></div>
            <label className="field-label" htmlFor="raw">{mode === 'single_message' ? '확인할 문자' : '화자를 구분한 대화'}</label>
            <textarea id="raw" className="raw-input" value={raw} onChange={e => setRaw(e.target.value)} placeholder={mode === 'single_message' ? '가상 문자 내용을 붙여넣어 주세요.\n\n예: 출금하려면 보증금을 먼저 보내주세요.' : '화자: 내용 형식으로 입력해 주세요.\n\n운영자: 출금하려면 보증금을 먼저 보내주세요.\n참여자: 어떤 보증금인가요?'} spellCheck={false} />
            <div className="input-meta"><span>가림 후 화자 포함 10,000자 · 최대 100개 메시지</span><span>{Array.from(raw).length.toLocaleString()}자</span></div>
            <div className="examples"><p>직접 입력하기 전에, 가상 예시로 살펴보세요</p><div>{examples.map(e => <button key={e.id} onClick={() => loadExample(e)} title={e.description}>{e.title}<ArrowRight size={12} /></button>)}</div></div>
            <div className="card-footer"><span><LockKeyhole size={14} /> 다음 단계에서 개인정보를 가려요</span><button className="primary-button" onClick={preview}>가림 내용 확인<ArrowRight size={17} /></button></div>
          </>}
          {step === 1 && <>
            <p className="review-note"><ShieldCheck size={17} />{redacted ? `${redacted}개 개인정보 패턴을 가렸어요.` : '자동으로 가릴 개인정보 패턴을 찾지 못했어요.'} 이름·닉네임과 누락된 정보는 직접 수정해 주세요.</p>
            <fieldset disabled={busy} className="message-editor">{messages.map((m, i) => <div className="message-row" key={m.id}><div className="speaker-row"><span>{String(i + 1).padStart(2, '0')}</span><label className="sr-only" htmlFor={`speaker-${m.id}`}>메시지 {i + 1} 화자</label><input id={`speaker-${m.id}`} value={m.speaker} onChange={e => edit(i, 'speaker', e.target.value)} />{mode === 'conversation' && <button className="icon-button" aria-label={`메시지 ${i + 1} 삭제`} onClick={() => { setMessages(ms => ms.filter((_, j) => i !== j)); setConfirmed(false) }}><Trash2 size={15} /></button>}</div><label className="sr-only" htmlFor={`text-${m.id}`}>메시지 {i + 1} 내용</label><textarea id={`text-${m.id}`} value={m.text} onChange={e => edit(i, 'text', e.target.value)} /></div>)}{mode === 'conversation' && <button className="text-button" onClick={() => { setMessages(ms => [...ms, { id: `m${Math.max(0, ...ms.map(m => Number(m.id.slice(1)))) + 1}`, speaker: '미상', text: '' }]); setConfirmed(false) }}><Plus size={15} />메시지 추가</button>}</fieldset>
            <label className="confirm-box"><input type="checkbox" checked={confirmed} disabled={busy} onChange={e => setConfirmed(e.target.checked)} /><span>실제 개인정보·민감한 대화가 없는 <strong>가상 시연 문구</strong>임을 확인했으며, 위 내용을 외부 AI API로 전송하는 데 동의합니다.</span></label>
            {configured === false && <p className="setup-note">분석하려면 서버의 Gemini 무료 API 키 설정이 필요합니다. 키는 이 화면에 입력하지 마세요.</p>}
            <div className="card-footer"><button className="text-button" disabled={busy} onClick={() => { setRaw(mode === 'single_message' ? messages[0]?.text ?? '' : messages.map(m => `${m.speaker}: ${m.text}`).join('\n')); setStep(0); setError('') }}><ArrowLeft size={15} />내용 다시 입력</button><button className="primary-button" disabled={!confirmed || busy} onClick={submit}>{busy ? <><LoaderCircle className="spin" size={17} />근거를 확인하고 있어요</> : <>의심 신호 분석<ScanText size={17} /></>}</button></div>
            {busy && <p className="busy-note" role="status">문맥과 원문 근거를 확인하고 있습니다. 잠시만 기다려 주세요.</p>}
          </>}
          {step === 2 && result && <>
            <div className={`result-summary ${result.status}`}><span className="result-label"><ShieldCheck size={18} />{statusText[result.status]}</span><p>{result.summary}</p><small>입력된 내용에 한정된 분석이며, 사기 확정이나 안전 보장이 아닙니다.</small></div>
            {result.signals.map(signal => <article className="signal-card" key={signal.id}><h3><span className="signal-dot" />{tagText[signal.tag] ?? signal.tag}</h3>{signal.evidence.map((e, i) => <blockquote key={`${e.message_id}-${i}`}><span>{messages.find(m => m.id === e.message_id)?.speaker ?? '미상'} · {e.message_id}</span>“{e.quote}”</blockquote>)}<p>{signal.reason}</p>{signal.source_explanation && <p className="source-explanation"><BookOpen size={15} />{signal.source_explanation}</p>}</article>)}
            <details className="original"><summary>분석에 사용한 문구와 근거 보기</summary>{messages.map(m => <div key={m.id}><strong>{m.speaker}</strong><p>{highlightParts(m.text, result.signals.flatMap(s => s.evidence.filter(e => e.message_id === m.id).map(e => e.quote))).map((p, i) => p.marked ? <mark key={i}>{p.text}</mark> : <span key={i}>{p.text}</span>)}</p></div>)}</details>
            {!!result.observed_flow.length && <div className="result-section"><h3>대화에서 관찰된 흐름</h3><ol>{result.observed_flow.map((f, i) => <li key={i}>{f.description}</li>)}</ol></div>}
            <div className="result-section"><h3><BookOpen size={17} />관련 공식 자료</h3>{result.sources.length ? result.sources.map(s => <a className="source-card" key={`${s.id}-${s.chunk_id}`} href={s.url} target="_blank" rel="noreferrer"><span><small>{s.publisher} · 확인 {s.checked_at}</small><strong>{s.title}</strong><span>{s.excerpt}</span></span><ExternalLink size={16} /></a>) : <p className="muted">이 분석에 연결할 공식 자료가 충분하지 않습니다.</p>}</div>
            {!!result.questions.length && <div className="result-section"><h3>추가로 확인해 보세요</h3><ul>{result.questions.map((q, i) => <li key={i}>{q}</li>)}</ul></div>}
            {!!result.actions.length && <div className="actions"><h3>다음 행동</h3><ul>{result.actions.map((a, i) => <li key={i}>{a}</li>)}</ul></div>}
            <div className="limitations">{[...result.limitations, ...result.warnings].map((l, i) => <p key={i}>{l}</p>)}</div>
            <button className="primary-button wide" onClick={reset}>내용 지우고 새로 분석<RotateCcw size={16} /></button>
          </>}
        </section>
        <aside className="aside"><div className="guide-card"><div className="guide-icon"><ScanText size={25} /></div><h2>판단의 근거를<br />함께 살펴봅니다.</h2><p>어떤 말을 했는지,<br />실제로 무엇을 요구했는지.</p><div className="guide-item"><span>01</span><div><strong>요구 행위 확인</strong><p>선입금, 인증정보, 앱 설치 등<br />문구 속 요구를 살펴봐요.</p></div></div><div className="guide-item"><span>02</span><div><strong>앞뒤 문맥 구분</strong><p>예방 안내와 실제 요구를<br />구분해 분석해요.</p></div></div><div className="guide-item"><span>03</span><div><strong>원문·출처 연결</strong><p>실제 문장과 관련 자료로<br />확인할 점을 설명해요.</p></div></div></div><div className="privacy-card"><LockKeyhole size={18} /><div><strong>대화는 자동 저장하지 않아요</strong><p>가림은 브라우저에서 먼저 진행합니다. 서버 미저장과 외부 AI의 데이터 정책은 별개예요.</p></div></div></aside>
      </div>
      <footer className="site-footer"><span>ScamCheck · 의심을 근거로 바꾸는 작은 확인</span><span>가상 데이터로 검증 중인 시제품</span></footer>
    </main>
  </div>
}
