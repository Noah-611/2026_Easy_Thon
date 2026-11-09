// 용도: React 앱과 공통 스타일을 브라우저 문서에 연결한다.
import React from 'react'
import ReactDOM from 'react-dom/client'
import '@fontsource-variable/noto-sans-kr'
import App from './App'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
