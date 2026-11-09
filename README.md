<!-- 용도: 앱 설치, 실행, Gemini 연결과 평가 재현 방법을 안내한다. -->
# ScamCheck MVP

직접 실행하고 종료하는 순서는 **[실행 가이드](RUN_GUIDE.md)** 를 참고한다. 현재 PC에서 다시 켜는 방법과 처음 설치하는 방법을 구분해 정리했다.

한국어 문자·대화의 의심 요구를 원문 인용과 공식 자료로 확인하는 로컬 시연 앱. React + TypeScript + Vite, FastAPI + Pydantic, Gemini REST API를 사용한다. 비교 실험은 CPU 문자 TF-IDF + 로지스틱 회귀이며 GPU는 필요 없다.

현재 입력·가림·수정·동의 화면, 분석/근거 검증, 공식 자료 5개 검색, 결과 화면과 CPU 비교 실험을 구현했다. Gemini 실제 연결과 합성 14건 집중 회귀를 실행하고 [분석 품질 검토](docs/llm-quality-review.md)에 결과·오류·수정 사항을 기록했다. 데스크톱·모바일 크기 브라우저 흐름 12건과 실제 Gemini 화면 분석 1건을 통과해 로컬 시연이 가능하다. 전체 개발·보류 비교와 사용자 사용감 확인은 남아 있다. 키가 없으면 설정 오류를 표시하며 분석 결과를 만들지 않는다.

## 실행

Python 3.12+, uv, Node.js 24를 기준으로 한다. 저장소 루트에서:

```bash
uv sync --locked
cp .env.example .env  # 기존 .env가 있을 때는 덮어쓰지 말 것
```

`.env`의 `LLM_API_KEY`를 로컬 편집기로 설정한다. 키를 채팅·Git·`VITE_` 환경변수에 넣지 않는다. [Google AI Studio](https://aistudio.google.com/api-keys)에서 키를 만들고 프로젝트의 요금제와 모델 사용 가능 여부를 확인한다. 기본 모델은 `gemini-3.1-flash-lite`이며 `LLM_MODEL`로 바꿀 수 있다. 무료로 시연하려면 결제가 활성화되지 않은 프로젝트를 사용하고 [공식 가격표](https://ai.google.dev/gemini-api/docs/pricing)에서 해당 모델의 무료 구간을 확인한다. 무료 한도는 계정·모델에 따라 달라질 수 있다. 429 응답은 한도 오류로 표시한다.

**무료 Gemini 전송은 실제 개인정보·민감 대화가 없는 합성 예시로 제한한다.** [Gemini API 약관](https://ai.google.dev/gemini-api/terms)에 따라 무료 서비스 입력이 서비스 개선 및 사람 검토에 사용될 수 있다. 가림 기능은 완전한 익명화를 보장하지 않는다. UI와 API 모두 가림 확인 및 합성 데이터 확인을 요구한다.

터미널 1:

```bash
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

터미널 2:

```bash
cd frontend
npm ci
npm run dev
```

`http://127.0.0.1:5173`에서 예시 선택 → 가림 미리보기·수정 → 합성 데이터 전송 확인 → 분석 순서로 이용한다. 키 없이도 예시·가림 화면을 사용할 수 있다. Vite가 `/api`와 `/health`를 백엔드로 전달한다. 한글 글꼴은 앱에 포함되어 로컬 서버에서 제공된다. 공개 배포용 인증·영속 요청 한도는 아직 없다.

## 분석 경로

1. 브라우저에서 전화·계좌·주민번호·인증정보·링크 패턴을 가린 뒤 사용자가 직접 수정한다.
2. 서버 입력 검증과 잔여 패턴 검사 → 규칙 후보 추출 → 전체 문맥 LLM 분석.
3. 메시지 ID와 인용의 정확한 원문 일치·발생 위치·메시지 순서를 검증한다.
4. 태그와 별도 검색용 TF-IDF로 공식 문서 조각을 찾고 두 번째 LLM 호출로 설명한다.
5. 검색에서 반환한 출처 ID만 허용한다. 설명 검증 실패 시 출처 연결을 생략하고 경고한다.

출처가 실제로 존재하고 인용이 일치해도 해석이 올바르다는 보장은 없다. 문맥·이유·출처 관련성은 실제 모델 응답을 사람이 검토해야 한다. 사용자 링크를 열거나 대화를 저장하지 않는다. 입력은 외부 Gemini로 전송된다. 분당 10건·하루 100건 기본 요청 제한은 단일 서버 메모리 기준이며 재시작하면 초기화된다. 요청 하나에 JSON 재시도 포함 최대 4회 API 호출이 가능하므로 이 제한은 과금 상한이 아니다.

## CPU 실험 및 검증

소스·문서·설정 파일의 첫 줄에는 파일 용도 주석이 있다. JSON·JSONL 등 주석을 지원하지 않는 파일은 [파일 용도 안내](docs/file-purposes.md)에 설명했다. `.env`의 설명 주석은 비밀 키에 영향을 주지 않는다.

키 설정 후 연결만 확인하려면 `uv run python -m scripts.check_gemini`를 실행한다. 저장소의 가상 예시 한 건을 실제 Gemini에 전송하고 상태·태그·응답 형식·인용을 검사한다. 키와 원문 응답은 출력하지 않는다. 성공 1건은 전체 분석 품질을 입증하지 않는다.

Gemini 생성 스키마에서는 문자열 패턴·길이와 중첩 배열 개수 제약을 제외하고 서버 Pydantic 검증에서 계속 강제한다. 중첩 배열 상한을 포함한 원래 스키마는 실제 요청에서 HTTP 400으로 거절됐고, 상한을 제외한 요청은 통과했다. 공식 문서도 [복잡한 스키마의 거절 가능성](https://ai.google.dev/gemini-api/docs/structured-output)을 안내한다.

```bash
uv run python -m scripts.baseline train
uv run python -m scripts.baseline evaluate --method rules --split dev
uv run python -m scripts.baseline evaluate --method tfidf --split dev
# 설정 고정 후에만 보류 평가를 연다.
uv run python -m scripts.baseline evaluate --method rules --split holdout --final
uv run python -m scripts.baseline evaluate --method tfidf --split holdout --final
uv run pytest -q
cd frontend
npm test
npm run build
```

학습 36건과 평가 60건은 별도 합성 문장이다. 설정과 분할은 고정했고 결과를 보고 튜닝하지 않았다. 자세한 한계는 [데이터 설명](data/evaluation/README.md), 측정 결과는 [초기 평가 기록](docs/evaluation-results.md)을 참고한다. 모델과 전체 분류 지표·혼동행렬·실패 ID·추론 지연은 `artifacts/`에 생성한다. 외부에서 받은 joblib/pickle 모델은 실행될 수 있으므로 로드하지 않는다.

키 설정 후 다음 명령은 **실제 외부 호출**을 한다. 무료 한도에 걸리면 중단하고 부분 결과를 저장한다. 이 스크립트는 저장소의 합성 평가 자료 전용이며 사용자가 입력한 대화를 저장하는 기능이 아니다.

```bash
uv run python -m scripts.evaluate_llm --split dev --allow-api-calls
# 다화자·예방·부정·공격·난독화 등 집중 회귀 14건
uv run python -m scripts.evaluate_llm --suite regression --allow-api-calls
# 중단된 결과와 오류를 보존하고 남은 사례만 이어서 확인
uv run python -m scripts.evaluate_llm --suite regression --allow-api-calls --resume
# 검색·설명까지 포함한 별도 서비스 평가
uv run python -m scripts.evaluate_llm --split dev --rag --allow-api-calls
```

LLM 평가의 API 오류는 `ERROR`로 기록하고 누락 없이 분모에 포함한다. 평가 스크립트는 모델 혼잡(503)에 한해 15초 후 한 번 더 시도하고 실패한 시도도 기록한다. 서비스 API는 자동으로 혼잡 재시도를 하지 않는다. 무료 한도·설정·연결 오류는 평가를 중단한다. `--resume`는 기존 오류까지 보존하며 설정·데이터·프롬프트가 같을 때만 남은 사례를 이어간다. 보류 평가는 `--split holdout --final`로 진행한다. 전체 LLM 개발·보류 비교는 아직 미완료이며 집중 회귀 결과와 구분한다. CPU 분류기는 UI 분석을 대신하지 않는다. 향후 API 없이 제공하려면 더 큰 검토 데이터, 정상 사례 오탐 개선, 규칙 근거·공식 검색·검토된 설명 템플릿을 함께 평가해야 한다.

## 화면 검사와 시연

백엔드와 프런트엔드를 켠 상태에서 `frontend/`의 `npm run test:e2e -- flow.spec.ts`로 화면 흐름을 검사한다. 최초에는 `npx playwright install --with-deps chromium`으로 브라우저와 필요한 시스템 라이브러리를 준비한다. 기본 화면 검사는 Gemini에 요청하지 않는다. 실제 API 화면 검사는 `SCAMCHECK_LIVE_E2E=1 npm run test:e2e -- live.spec.ts --project=desktop`으로 명시적으로 실행한다. [화면 점검 기록](docs/browser-review.md)에 검사 범위·수정 사항·환경별 재현 방법을 정리했다.

오늘 저녁 시연의 완료 기준은 가상 예시 입력 → 가림·수정 → 세 상태 분류 → 원문 근거·이유 표시다. 공식 자료는 충분히 관련 있을 때 연결하며, 설명 생성 실패나 시간 초과가 나도 검증된 핵심 결과를 유지한다. [근거·출처 검증 기록](docs/source-review.md)에 실제 7건 검사와 수정 후 4건 재검사를 정리했다.

- 대출 선입금, 투자 출금 전 추가 납부, 예방 문구 예시를 차례로 분석한다.
- 불완전한 요청은 추가 맥락을 묻는지 확인한다.
- 키 누락·한도·타임아웃·없는 인용은 안전 판정으로 표시되지 않는지 확인한다.
- 일부 다화자·부정·공격·공식 자료 설명과 핵심 브라우저 흐름은 검증했다. 최종 설정의 전체 개발·보류 비교, 사용자 사용감 확인과 독립 라벨 검토가 남아 있다.

공식 자료 출처·검토일·재사용 주의는 `data/knowledge/`에 기록했다. 앱은 사기 확정이나 안전 보장을 제공하지 않는다.
