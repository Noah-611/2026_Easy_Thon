<!-- 용도: 사용자가 ScamCheck MVP를 직접 준비·실행·사용·종료하고 문제를 확인하는 절차를 안내한다. -->
# ScamCheck MVP 실행 가이드

현재 프로젝트 위치는 `/home/eunsu/projects/ScamDetector`다. 아래 명령은 Linux 또는 WSL의 Bash 터미널 기준이다. 다른 위치에 저장소를 받았다면 `cd` 경로만 바꾸면 된다.

## 1. 지금 다시 실행하기

현재 PC에는 의존성이 설치되어 있고 `.env`도 만들어져 있다. **터미널 두 개를 열어** 다음 명령을 각각 실행한다. 가상환경을 따로 활성화할 필요는 없다.

### 터미널 1 — 백엔드

```bash
cd /home/eunsu/projects/ScamDetector
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

`Uvicorn running on http://127.0.0.1:8000`이 나오면 정상이다. 이 터미널은 실행한 채로 둔다.

### 터미널 2 — 프런트엔드

```bash
cd /home/eunsu/projects/ScamDetector/frontend
npm run dev
```

`Local: http://127.0.0.1:5173/`이 나오면 정상이다. 이 터미널도 실행한 채로 둔다.

### 브라우저 접속

**[http://127.0.0.1:5173](http://127.0.0.1:5173)** 을 연다.

WSL을 사용한다면 두 서버 명령은 WSL 터미널에서 실행하고 Windows 브라우저에서 위 주소를 연다. 현재 서버는 이 PC에서 사용하는 로컬 시연용이며 휴대폰이나 다른 PC에 공개하지 않는다. 실제 Gemini 분석에는 인터넷 연결이 필요하다.

## 2. 시연 순서

1. **인증번호 요구** 예시 버튼을 누른다.
2. **가림 내용 확인**을 누른다.
3. 전송할 화자·문구를 검토한다. 수정하면 동의를 다시 해야 한다.
4. 실제 개인정보가 없는 가상 문구라는 확인란을 선택한다.
5. **의심 신호 분석**을 누르고 결과를 기다린다.
6. 의심 상태·인증정보 요구 태그·원문 인용·이유를 확인한다.
7. **분석에 사용한 문구와 근거 보기**를 펼쳐 강조된 원문을 확인한다.
8. **내용 지우고 새로 분석**으로 초기화한다.

이후 **리딩방 출금 상담**, **사기 예방 안내**를 차례로 확인한다. 전자는 여러 화자의 요구와 출금 전 추가 납부를, 후자는 예방 문구를 실제 요구로 잘못 해석하지 않는지 살펴보는 예시다.

현재 무료 시연은 **저장소의 가상 예시 또는 직접 만든 합성 문구**로 진행한다. 실제 개인정보·민감한 대화를 입력하지 않는다. 공식 자료는 관련 자료를 찾고 설명 검증까지 통과했을 때만 표시된다. 자료가 없거나 설명 생성에 실패해도 검증된 분류·원문·이유는 유지된다.

## 3. 서버 종료하기

1. 프런트엔드를 실행한 터미널에서 **Ctrl+C**를 누른다.
2. 백엔드를 실행한 터미널에서도 **Ctrl+C**를 누른다.
3. 백엔드에 `Application shutdown complete`가 표시되고 두 터미널 모두 명령 입력 상태로 돌아오면 종료된 것이다.

브라우저 탭만 닫으면 서버는 계속 실행된다. 다음에 사용할 때는 1절의 두 명령을 다시 실행하면 된다.

## 4. 새 PC 또는 처음 받은 저장소에서 준비하기

검증한 기준은 Python 3.12, uv, Node.js 24와 npm이다. 필요한 도구가 설치되어 있는지 `python3 --version`, `uv --version`, `node --version`, `npm --version`으로 확인한다. 현재 PC에서는 이미 설치한 의존성을 매번 다시 설치할 필요가 없다.

저장소 루트에서 Python 환경을 준비한다.

```bash
cd /home/eunsu/projects/ScamDetector
uv sync --locked --python 3.12
```

프런트엔드 의존성을 준비한다.

```bash
cd /home/eunsu/projects/ScamDetector/frontend
npm ci
```

`.env`가 없는 경우에만 예시 파일을 복사한다. 아래 명령은 기존 `.env`를 덮어쓰지 않는다.

```bash
cd /home/eunsu/projects/ScamDetector
test -f .env || cp .env.example .env
```

편집기로 `.env`를 열고 다음 항목을 설정한다. 키는 채팅·Git에 넣지 않는다. `.env`는 Git 제외 대상이라 새로 받은 저장소에는 없으며, `.env.example`에는 키가 비어 있다.

```dotenv
LLM_API_KEY=발급받은_Gemini_API_키
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.1-flash-lite
```

API 키를 설정한 뒤 1절 순서대로 서버를 실행한다. `.env`를 수정했다면 백엔드를 Ctrl+C로 종료하고 다시 실행한다. 요금제·무료 구간과 가상 데이터 사용 조건은 [README](README.md)의 안내를 참고한다.

## 5. 문제가 생겼을 때

| 증상 | 확인할 내용 |
|---|---|
| 화면 주소가 열리지 않음 | 터미널 2에서 `npm run dev`가 실행 중인지, 표시된 주소가 5173인지 확인한다. |
| 예시를 불러오지 못함 / 서버 연결 실패 | 터미널 1의 백엔드가 8000에서 실행 중인지 확인한다. 두 서버가 모두 필요하다. |
| Gemini 키 설정이 필요하다는 안내 | 프로젝트 루트의 `.env`에 `LLM_API_KEY`를 넣고 백엔드를 재시작한다. |
| 무료 API 한도 오류 | 반복 클릭을 멈추고 제공자 한도가 갱신된 뒤 다시 시도한다. 서버 재시작은 Gemini 한도를 초기화하지 않는다. |
| AI 서비스 혼잡 / 분석 시간 초과 | 입력을 유지한 상태에서 잠시 뒤 다시 시도한다. 실패를 안전 판정으로 해석하지 않는다. |
| 공식 자료가 없다는 안내 | 충분히 관련된 자료가 없거나 설명 검증에 실패한 경우다. 표시된 원문 근거와 이유를 확인한다. |
| 주소·포트를 이미 사용 중이라는 오류 | 앞서 실행한 서버 터미널이 남아 있는지 확인하고 해당 터미널에서 Ctrl+C로 종료한다. |
| `.venv/bin/python`이 없음 | 저장소 루트에서 `uv sync --locked --python 3.12`를 실행한다. |
| `vite`를 찾을 수 없음 | `frontend/`에서 `npm ci`를 실행한다. |

백엔드 상태는 브라우저의 **[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)** 에서 확인할 수 있다. `status: "ok"`는 서버가 켜져 있다는 뜻이고, `analysis_configured: true`는 키·제공자 설정이 있다는 뜻이다. 실제 API 연결 성공 여부는 분석 요청으로 확인한다.

포트를 임의로 변경하면 프런트엔드 프록시와 CORS 설정도 맞춰야 하므로 기본값 8000·5173을 사용한다. 일반 시연은 `npm run dev`로 실행한다. `npm run build`는 배포 파일 생성·검사용이며 서버를 켜는 명령이 아니다.

## 6. 선택 사항 — 검사 명령

서버 실행 없이도 자동 단위 검사와 빌드를 실행할 수 있다.

```bash
cd /home/eunsu/projects/ScamDetector
.venv/bin/python -m pytest -q
cd frontend
npm test
npm run build
```

브라우저 자동 검사는 별도 Chromium 준비와 실행 중인 두 서버가 필요하다. 실제 Gemini 호출을 포함한 검사와 화면 테스트 응답 검사는 [화면 점검 기록](docs/browser-review.md)의 재현 절차를 따른다. 일반 사용·시연에는 Playwright 설치가 필요 없다.
