<!-- 용도: 프로젝트 파일별 역할과 첫 줄 주석을 넣을 수 없는 형식을 설명한다. -->
# 파일 용도 안내

프로젝트가 관리하는 소스·문서·설정 파일의 첫 줄에 용도 주석을 추가했다. `.env`도 키 값을 출력하지 않고 설명 줄만 추가했다. 의존성 설치 폴더, `.git`, 캐시, 빌드 결과와 자동 생성 실험 산출물은 수정 대상에서 제외했다.

JSON·JSONL은 표준 형식에 주석이 없다. 아래 파일은 첫 줄에 주석을 넣으면 파싱·설치가 깨질 수 있어 원래 형식을 유지하고 여기서 용도를 설명한다. TSV의 첫 줄 `#` 설명은 평가 로더가 건너뛴다. `uv.lock`은 TOML 형식이라 주석이 유효하지만 도구가 재생성하면 사라질 수 있다.

| 파일 | 용도 |
|---|---|
| `.gitignore` | 비밀 설정, 의존성, 빌드 결과와 실험 산출물을 Git에서 제외한다. |
| `.env.example` | Gemini 연결과 로컬 서버 제한에 필요한 환경변수 예시를 제공한다. |
| `.env` (Git 제외) | 로컬 Gemini 비밀 키와 서버 실행 설정을 보관한다. |
| `pyproject.toml` | Python 의존성과 개발 도구 및 테스트 설정을 정의한다. |
| `uv.lock` | 재현 가능한 Python 의존성 버전과 배포 파일 정보를 고정한다. |
| `README.md` | 앱 설치, 실행, Gemini 연결과 평가 재현 방법을 안내한다. |
| `RUN_GUIDE.md` | 사용자가 MVP를 직접 준비·실행·사용·종료하고 문제를 확인하는 절차를 안내한다. |
| `Phishing_Scam_Text_Analyzer_PLAN.md` | MVP 범위, 분석 방식, 완료 기준과 개발 현황을 정리한다. |
| `docs/decision-criteria.md` | 의심 신호, 판단 곤란, 뚜렷한 신호 없음의 판정 기준을 정의한다. |
| `docs/evaluation-results.md` | 합성 데이터 비교 실험 결과와 검증 한계를 기록한다. |
| `docs/llm-quality-review.md` | 실제 Gemini 문맥 분석의 집중 회귀 결과, 의미 검토와 수정 내역을 기록한다. |
| `docs/source-review.md` | 원문 근거·공식 출처 연결의 실제 검증 결과와 실패 시 동작을 기록한다. |
| `docs/browser-review.md` | 로컬 MVP의 실제 브라우저 흐름 검사, 수정 사항과 사용자 확인 방법을 기록한다. |
| `data/knowledge/README.md` | 공식 자료의 출처, 인용 범위와 재사용 주의사항을 설명한다. |
| `data/evaluation/README.md` | 합성 학습·평가 데이터의 분할, 구성과 한계를 설명한다. |
| `data/evaluation/cases.tsv` | CPU 분류기와 LLM 비교용 합성 학습·개발·보류 사례를 제공한다. |
| `scripts/__init__.py` | 학습·평가·연결 확인 스크립트를 Python 모듈로 실행하게 한다. |
| `scripts/baseline.py` | CPU TF-IDF 분류기를 학습하고 규칙·분류기 성능을 평가한다. |
| `scripts/check_gemini.py` | 가상 예시 한 건으로 실제 Gemini 연결과 응답·인용을 검증한다. |
| `scripts/evaluate_llm.py` | 합성 평가·회귀 사례를 실제 LLM에 보내 지표와 결과를 기록한다. |
| `backend/__init__.py` | 백엔드 코드를 Python 패키지로 구성한다. |
| `backend/app/__init__.py` | FastAPI 애플리케이션 모듈을 Python 패키지로 구성한다. |
| `backend/app/config.py` | 로컬 환경변수를 읽고 서버·Gemini 설정을 검증한다. |
| `backend/app/errors.py` | 사용자에게 안전하게 전달할 API 오류 코드와 메시지를 정의한다. |
| `backend/app/main.py` | 분석·예시·상태 API와 요청 크기·횟수 및 개인정보 보호 처리를 제공한다. |
| `backend/app/schemas.py` | 입력, 분석 근거, 출처와 응답의 공통 데이터 계약을 검증한다. |
| `backend/app/prompts/detect.txt` | LLM이 실제 요구와 예방·부정·인용을 구분하도록 지시한다. |
| `backend/app/prompts/explain.txt` | 검색된 공식 자료만 사용해 분석 근거를 설명하도록 지시한다. |
| `backend/app/services/__init__.py` | 분석 처리 서비스들을 Python 패키지로 구성한다. |
| `backend/app/services/analysis.py` | 문맥 분석, 원문 검증, 공식 자료 검색과 출처 설명을 연결한다. |
| `backend/app/services/evidence.py` | 모델의 인용·메시지 ID·관찰 순서를 원문과 대조한다. |
| `backend/app/services/llm.py` | Gemini REST 호출, 생성 스키마 변환과 응답 검증을 수행한다. |
| `backend/app/services/preprocess.py` | 텍스트 정규화와 서버의 잔여 개인정보 패턴 검사를 수행한다. |
| `backend/app/services/retrieval.py` | 검토된 공식 자료에서 태그와 TF-IDF로 관련 문서 조각을 찾는다. |
| `backend/app/services/rules.py` | 의심 행위 후보와 비교 실험용 규칙 상태 판정을 생성한다. |
| `backend/tests/test_analysis.py` | 원문·출처 검증과 모델 오류 및 Gemini 스키마 호환성을 검사한다. |
| `backend/tests/test_api.py` | 상태·예시 API, 비밀정보 보호, 입력 오류와 요청 한도를 검사한다. |
| `backend/tests/test_contracts.py` | 입력 계약, 길이·동의 제약과 합성 예시의 유효성을 검사한다. |
| `backend/tests/test_evaluation.py` | 실제 호출 없이 평가 오류의 분모 포함과 중단 결과 재개 동작을 검사한다. |
| `frontend/vite.config.ts` | 프런트엔드 빌드, 로컬 API 프록시와 테스트 환경을 설정한다. |
| `frontend/playwright.config.ts` | 로컬 앱의 데스크톱·모바일 브라우저 흐름 검사를 설정한다. |
| `frontend/e2e/flow.spec.ts` | 가림·동의·결과·수정·오류·초기화 흐름을 브라우저에서 검사한다. |
| `frontend/e2e/live.spec.ts` | 명시적 활성화 시 실제 Gemini 분석을 브라우저 결과 화면까지 검사한다. |
| `frontend/public/fonts/OFL.txt` | 앱에 포함된 Noto Sans KR 글꼴의 저작권과 라이선스를 제공한다. |
| `frontend/index.html` | 한국어 분석 앱의 HTML 진입 문서와 React 마운트 지점을 제공한다. |
| `frontend/src/App.tsx` | 입력·가림 검토·전송 동의·분석 결과의 사용자 화면을 구성한다. |
| `frontend/src/main.tsx` | React 앱과 공통 스타일을 브라우저 문서에 연결한다. |
| `frontend/src/styles.css` | 분석 화면의 색상, 배치, 반응형 동작과 접근성 스타일을 정의한다. |
| `frontend/src/types.ts` | 화면에서 사용하는 API 타입과 상태·태그 표시 문구를 정의한다. |
| `frontend/src/lib/api.ts` | 가림과 합성 데이터 동의가 포함된 분석 요청을 서버에 전송한다. |
| `frontend/src/lib/redact.ts` | 브라우저 개인정보 가림, 대화 파싱과 원문 인용 강조를 수행한다. |
| `frontend/src/lib/redact.test.ts` | 개인정보 가림, 입력 제한과 유니코드 인용 강조를 검사한다. |
| `frontend/package.json` | Node 패키지 정보와 실행·빌드·테스트 명령을 정의한다. |
| `frontend/package-lock.json` | 재현 가능한 Node 의존성 버전과 무결성 정보를 고정한다. |
| `frontend/tsconfig.json` | 프런트엔드 TypeScript 타입 검사와 모듈 설정을 정의한다. |
| `data/examples/demo.json` | 사용자가 선택할 수 있는 합성 시연 예시 6개를 제공한다. |
| `data/knowledge/sources.json` | 검토된 공식 자료의 제목·기관·URL·검토일을 제공한다. |
| `data/knowledge/chunks.jsonl` | 공식 자료 검색에 사용할 짧은 인용과 행위 태그를 제공한다. |
| `data/evaluation/regression.json` | 맥락·부정·예방·다화자·공격 문구의 합성 회귀 사례를 제공한다. |
