// 용도: 실제 화면에서 가림·동의·결과·수정·오류·초기화 흐름을 테스트 응답으로 검사한다.
import { mkdirSync } from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import type { Analysis, Message } from '../src/types'

const pageErrors = new WeakMap<Page, string[]>()

function response(messages: Message[]): Analysis {
  const quote = messages[0].text
  return {
    request_id: 'browser-test', status: 'suspicious_signals', categories: ['INVESTMENT_SCAM'],
    summary: '출금 전에 보증금 입금을 요구하는 문구입니다.',
    signals: [{ id: 's1', tag: 'WITHDRAWAL_PREPAYMENT', reason: '출금을 조건으로 추가 납부를 요구합니다.',
      evidence: [{ message_id: messages[0].id, quote, occurrences: [{ start: 0, end: Array.from(quote).length }] }],
      source_ids: ['FIU-001'], source_explanation: '공식 자료에서 설명하는 출금 전 추가 납부 요구와 관련됩니다.' }],
    observed_flow: [{ message_ids: [messages[0].id], description: '추가 납부 요구' }],
    questions: ['출금 조건을 공식 채널에서 확인했나요?'], actions: ['추가 납부 전에 공식 채널에서 확인하세요.'],
    limitations: ['브라우저 동작 확인용 테스트 응답입니다.'], warnings: [], analysis_mode: 'rules_llm_rag',
    sources: [{ id: 'FIU-001', chunk_id: 'FIU-001-c1', title: '공식 자료 연결 테스트', publisher: '금융정보분석원',
      url: 'https://www.fsc.go.kr/po010104/87493', checked_at: '2026-11-08', excerpt: '출금 전 추가 납부 요구 관련 자료' }],
  }
}

test.beforeEach(async ({ page }) => {
  const errors: string[] = []
  pageErrors.set(page, errors)
  page.on('pageerror', e => errors.push(e.message))
  // UI tests never reach the real analyze endpoint; live tests opt in separately.
  await page.route('**/api/v1/analyze', route => route.fulfill({ status: 503,
    json: { code: 'TEST_GUARD', message: 'Test route must be specified.', request_id: 'test' } }))
  await page.goto('/')
  await expect(page.getByRole('button', { name: '인증번호 요구', exact: true })).toBeVisible()
})

test.afterEach(async ({ page }) => {
  expect(pageErrors.get(page)).toEqual([])
})

test('가림·수정·동의 후에만 전송하고 결과·원문·출처·초기화를 표시한다', async ({ page }, info) => {
  const sent: { messages: Message[]; redaction_confirmed: boolean; demo_data_confirmed: boolean }[] = []
  await page.route('**/api/v1/analyze', async route => {
    const body = route.request().postDataJSON()
    sent.push(body)
    await route.fulfill({ json: response(body.messages) })
  })
  await page.getByLabel('확인할 문자', { exact: true }).fill('출금하려면 보증금을 먼저 보내세요. 가상 연락처 010-1234-5678 https://example.com/test?token=demo')
  await page.getByRole('button', { name: '가림 내용 확인' }).click()
  const preview = page.getByLabel('메시지 1 내용', { exact: true })
  await expect(preview).toHaveValue(/\[전화1\].*\[링크1\]/)
  expect(sent).toHaveLength(0)
  const submit = page.getByRole('button', { name: '의심 신호 분석', exact: true })
  await expect(submit).toBeDisabled()
  await page.getByRole('checkbox').check()
  await preview.fill((await preview.inputValue()) + ' 확인 부탁해요.')
  await expect(page.getByRole('checkbox')).not.toBeChecked()
  await expect(submit).toBeDisabled()
  await page.getByRole('checkbox').check()
  await submit.click()
  await expect(page.getByRole('heading', { name: '문구에서 찾은 신호' })).toBeVisible()
  expect(sent).toHaveLength(1)
  expect(sent[0].redaction_confirmed && sent[0].demo_data_confirmed).toBe(true)
  const encoded = JSON.stringify(sent[0])
  expect(encoded).not.toContain('010-1234-5678')
  expect(encoded).not.toContain('example.com')
  await expect(page.getByText('의심 신호 발견', { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: '출금 전 추가 납부', exact: true })).toBeVisible()
  await page.getByText('분석에 사용한 문구와 근거 보기', { exact: true }).click()
  await expect(page.locator('.original mark')).toHaveText(sent[0].messages[0].text)
  await expect(page.locator('.original a')).toHaveCount(0)
  await expect(page.getByRole('link', { name: /공식 자료 연결 테스트/ })).toHaveAttribute('href', 'https://www.fsc.go.kr/po010104/87493')
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  mkdirSync('../artifacts/browser', { recursive: true })
  await page.screenshot({ path: `../artifacts/browser/${info.project.name}-result.png`, fullPage: true })
  await page.getByRole('button', { name: '내용 지우고 새로 분석' }).click()
  await expect(page.getByLabel('확인할 문자', { exact: true })).toHaveValue('')
  await expect(page.getByRole('heading', { name: '문구에서 찾은 신호' })).toHaveCount(0)
  await page.screenshot({ path: `../artifacts/browser/${info.project.name}-input.png`, fullPage: true })
})

test('다화자 예시의 메시지를 삭제·추가·수정할 수 있다', async ({ page }) => {
  await page.getByRole('button', { name: '리딩방 출금 상담', exact: true }).click()
  await expect(page.getByRole('button', { name: '대화 여러 건', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('button', { name: '가림 내용 확인' }).click()
  await expect(page.getByRole('textbox', { name: /메시지 \d+ 내용/ })).toHaveCount(3)
  await page.getByRole('button', { name: '메시지 2 삭제', exact: true }).click()
  await page.getByRole('button', { name: '메시지 추가', exact: true }).click()
  await page.getByLabel('메시지 3 화자', { exact: true }).fill('참여자')
  await page.getByLabel('메시지 3 내용', { exact: true }).fill('추가 입금은 하지 않겠습니다.')
  await page.getByRole('button', { name: '내용 다시 입력' }).click()
  await expect(page.getByLabel('화자를 구분한 대화', { exact: true })).toHaveValue(/참여자: 추가 입금은 하지 않겠습니다\./)
})

test('검토 중 추가한 개인정보는 다시 가리고 기존 가림 번호와 구분한다', async ({ page }) => {
  const sent: string[] = []
  page.on('request', request => { if (request.url().endsWith('/api/v1/analyze')) sent.push(request.url()) })
  await page.getByLabel('확인할 문자', { exact: true }).fill('가상 연락처 010-1234-5678에서 출금 전 보증금을 요구했어요.')
  await page.getByRole('button', { name: '가림 내용 확인' }).click()
  const input = page.getByLabel('메시지 1 내용', { exact: true })
  await input.fill((await input.inputValue()) + ' 다른 가상 연락처 010-9876-5432')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: '의심 신호 분석', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('개인정보 패턴을 다시 가렸습니다')
  await expect(input).toHaveValue(/\[전화1\].*\[전화2\]/)
  await expect(page.getByRole('checkbox')).not.toBeChecked()
  expect(sent).toHaveLength(0)
})

test('한도 오류는 결과로 위장하지 않고 수정 가능한 입력을 유지한다', async ({ page }) => {
  await page.route('**/api/v1/analyze', route => route.fulfill({ status: 429,
    json: { code: 'PROVIDER_QUOTA', message: '무료 API 호출 한도에 도달했습니다.', request_id: 'test' } }))
  await page.getByRole('button', { name: '인증번호 요구', exact: true }).click()
  await page.getByRole('button', { name: '가림 내용 확인' }).click()
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: '의심 신호 분석', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('무료 API 호출 한도')
  await expect(page.getByRole('heading', { name: '문구에서 찾은 신호' })).toHaveCount(0)
  await expect(page.getByLabel('메시지 1 내용', { exact: true })).toBeEditable()
  await expect(page.getByRole('button', { name: '의심 신호 분석', exact: true })).toBeEnabled()
})

test('빈 입력과 길이 초과를 전송 전에 안내한다', async ({ page }) => {
  await page.getByRole('button', { name: '가림 내용 확인' }).click()
  await expect(page.getByRole('alert')).toContainText('가상 문구를 입력')
  await page.getByLabel('확인할 문자', { exact: true }).fill('가'.repeat(10_001))
  await page.getByRole('button', { name: '가림 내용 확인' }).click()
  await expect(page.getByRole('alert')).toContainText('10,000자')
})

test('분석 도중 초기화하면 늦은 응답이 결과를 복구하지 않는다', async ({ page }) => {
  let release!: () => void
  let finished!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  const completed = new Promise<void>(resolve => { finished = resolve })
  await page.route('**/api/v1/analyze', async route => {
    const body = route.request().postDataJSON()
    await gate
    try { await route.fulfill({ json: response(body.messages) }) } catch { /* Request was cancelled by reset. */ }
    finally { finished() }
  })
  await page.getByRole('button', { name: '인증번호 요구', exact: true }).click()
  await page.getByRole('button', { name: '가림 내용 확인' }).click()
  await page.getByRole('checkbox').check()
  const outgoing = page.waitForRequest('**/api/v1/analyze')
  await page.getByRole('button', { name: '의심 신호 분석', exact: true }).click()
  await outgoing
  await expect(page.getByRole('button', { name: '근거를 확인하고 있어요' })).toBeDisabled()
  await page.getByRole('button', { name: '입력·결과 모두 삭제', exact: true }).click()
  release()
  await completed
  await expect(page.getByLabel('확인할 문자', { exact: true })).toHaveValue('')
  await expect(page.getByRole('heading', { name: '문구에서 찾은 신호' })).toHaveCount(0)
})
