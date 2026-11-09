// 용도: 프런트엔드 빌드, 로컬 API 프록시와 테스트 환경을 설정한다.
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, proxy: { '/api': 'http://127.0.0.1:8000', '/health': 'http://127.0.0.1:8000' } },
  test: { environment: 'node', include: ['src/**/*.test.ts'] },
})
