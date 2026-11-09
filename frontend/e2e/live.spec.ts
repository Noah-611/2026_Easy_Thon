// 용도: 명시적으로 활성화할 때만 브라우저에서 실제 Gemini 분석과 원문 결과 표시를 검사한다.
import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'

test('실제 Gemini 예시 분석을 화면까지 연결한다', async ({ page }, info) => {
  test.skip(process.env.SCAMCHECK_LIVE_E2E !== '1' || info.project.name !== 'desktop', 'Explicit live API opt-in required; desktop only.')
  test.setTimeout(120_000)
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto('/')
  await page.getByRole('button', { name: '인증번호 요구', exact: true }).click()
  await page.getByRole('button', { name: '가림 내용 확인' }).click()
  await page.getByRole('checkbox').check()
  const pending = page.waitForResponse(r => r.url().endsWith('/api/v1/analyze') && r.request().method() === 'POST', { timeout: 100_000 })
  await page.getByRole('button', { name: '의심 신호 분석', exact: true }).click()
  const api = await pending
  const data = await api.json()
  expect(api.status(), `API status=${api.status()}, code=${data.code ?? 'none'}`).toBe(200)
  expect(data.status).toBe('suspicious_signals')
  await expect(page.getByRole('heading', { name: '문구에서 찾은 신호' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '인증정보 요구', exact: true })).toBeVisible()
  await page.getByText('분석에 사용한 문구와 근거 보기', { exact: true }).click()
  await expect(page.locator('.original mark').first()).toBeVisible()
  expect(errors).toEqual([])
  mkdirSync('../artifacts/browser', { recursive: true })
  await page.screenshot({ path: '../artifacts/browser/live-gemini-result.png', fullPage: true })
  await page.getByRole('button', { name: '내용 지우고 새로 분석' }).click()
  await expect(page.getByLabel('확인할 문자', { exact: true })).toHaveValue('')
})
