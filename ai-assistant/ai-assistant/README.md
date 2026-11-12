# 내 데이터 AI 비서 (My Data AI Assistant)

> "이번 달 매출 어때?"라고 물으면 **내 데이터를 근거로** 답해 주는 AI 비서

일반 ChatGPT는 내 데이터를 모르기 때문에 일반론만 답합니다. 이 서비스는 **일별 매출 시계열 데이터**를 Firestore에 저장·관리하고, 그 데이터를 분석한 **요약(기간·개수·통계·추세)을 GPT 시스템 프롬프트에 주입**해서 내 상황에 맞는 답변을 만듭니다. 대화는 자동 저장되어 언제든 다시 불러올 수 있습니다.

## 배포 URL

| 구분 | URL |
|---|---|
| 프론트엔드 (Vercel) | https://ai-assistant-frontend-delta.vercel.app |
| 백엔드 API (Render) | https://ai-assistant-xqlg.onrender.com |
| Swagger UI | https://ai-assistant-xqlg.onrender.com/docs |

> ⚠️ Render 무료 티어는 15분간 요청이 없으면 잠듭니다. 첫 접속 시 최대 1분 정도 걸릴 수 있으며, 프론트엔드가 `/health`로 서버를 먼저 깨우면서 안내 배너를 띄웁니다.

## 기술 스택

| 영역 | 사용 기술 |
|---|---|
| 백엔드 | Python 3.11, FastAPI, Uvicorn, Pydantic v2 |
| DB | Firebase Firestore (`firebase-admin`) |
| AI | OpenAI Chat Completions API (코디세이 OpenAI 호환 게이트웨이, `gpt-5-mini`, 토큰 상한) |
| 프론트엔드 | HTML / CSS / JavaScript (프레임워크 없음, 그래프도 Canvas 직접 구현) |
| 배포 | Render (백엔드), Vercel (프론트엔드) |
| 테스트 | pytest + FastAPI TestClient (Firestore·OpenAI 가짜 객체 사용) |

## 주요 기능

- **데이터 기반 AI 채팅** — 요약 컨텍스트 주입, 로딩 표시, 이어서 대화하기, 자동 저장
- **데이터 관리(CRUD)** — 추가 / 목록 / 수정 / 삭제, 저장 결과 토스트 + 행 하이라이트
- **대화 기록** — 목록(최근 수정순), 불러오기, 삭제
- **데이터 요약** — 채팅 상단 요약 바 + 데이터 탭 통계 카드
- **보너스(인사이트·UX)** — 추가 지표(표준편차·최근 7일 평균·월별 집계·최근 달 비교), 추세 그래프(7일 이동평균), CSV/JSON 내보내기, 다크 모드

## 프로젝트 구조

```
ai-assistant/
├── backend/
│   ├── main.py                     # 앱 초기화, CORS, 예외 처리, 라우터 등록
│   ├── app/
│   │   ├── config.py               # 환경 변수 로드
│   │   ├── firebase.py             # Firestore 클라이언트 (지연 초기화)
│   │   ├── schemas.py              # Pydantic 요청/응답 모델
│   │   ├── routers/                # HTTP 계층: 경로·상태 코드·에러 변환만 담당
│   │   │   ├── data.py  conversations.py  chat.py
│   │   └── services/               # 비즈니스 로직 계층
│   │       ├── analysis.py         # 시계열 요약 (순수 함수, DB 무관)
│   │       ├── data_service.py     # data 컬렉션 CRUD
│   │       ├── conversation_service.py
│   │       └── chat_service.py     # 프롬프트 생성 + GPT 호출 + 자동 저장
│   ├── scripts/
│   │   ├── generate_sample_data.py # 샘플 데이터(181일) 생성
│   │   ├── analyze_csv.py          # CSV → 요약 JSON 출력 (DB 없이 분석)
│   │   └── seed_firestore.py       # CSV → Firestore 업로드
│   ├── data/sample_sales.csv
│   ├── tests/test_api.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html  style.css  app.js
│   ├── config.js                   # 로컬용 API 주소
│   ├── build.js                    # Vercel 빌드 시 API_BASE_URL → config.js 생성
│   └── vercel.json
└── render.yaml
```

## 데이터 선정 및 분석

- **데이터**: 가상의 카페 일별 매출 (`date, value, memo`), 2026-05-01 ~ 2026-10-28, **181개**
  - 완만한 상승 추세 + 요일 효과(금·토 ↑, 월 ↓) + 이벤트(어린이날, 장마, 추석 휴무 등) + 노이즈
  - 본인 데이터로 바꾸려면 같은 형식의 CSV를 `backend/data/`에 두고 `seed_firestore.py`로 업로드, `.env`의 `DATA_LABEL`/`DATA_UNIT`만 바꾸면 됩니다.
- **요약 지표** (`app/services/analysis.py`)
  - 기간, 개수, 합계·평균·최대(날짜)·최소(날짜)·표준편차
  - **추세**: 최근 30일 평균 vs 직전 30일 평균 변화율 → ±3% 기준 상승/하락/유지
  - 최근 7일 평균, 월별 합계·평균, 가장 최근 달의 일평균이 전체 대비 몇 % 인지

`python scripts/analyze_csv.py` 실행 결과(요약):

```json
{
  "period": "2026-05-01 ~ 2026-10-28",
  "count": 181,
  "metrics": { "total": 37362200, "average": 206420.99, "max": 460200, "max_date": "2026-10-09",
               "min": 94500, "min_date": "2026-09-25", "std": 50050.27 },
  "trend": "상승 (최근 30일 평균이 직전 30일 대비 +13.0%)",
  "recent_7_days_average": 246485.71,
  "latest_month": { "month": "2026-10", "average": 252535.71, "vs_overall_daily_avg_pct": 22.34, "...": "..." },
  "monthly": [ "..." ]
}
```

## API

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/data` | 데이터 추가 `{date, value, memo}` |
| GET | `/api/data` | 목록 (날짜 오름차순) |
| PUT | `/api/data/{id}` | 수정 (보낸 필드만 변경) |
| DELETE | `/api/data/{id}` | 삭제 |
| GET | `/api/data/summary` | 요약 (프롬프트 주입용) |
| POST | `/api/data/import-sample` | 샘플 CSV 181개 일괄 등록 (비어 있을 때만, 중복 시 409) |
| POST | `/api/conversations` | 대화 저장 `{title?, messages[]}` |
| GET | `/api/conversations` | 대화 목록 — **messages 미포함** (`message_count`만) |
| GET | `/api/conversations/{id}` | 특정 대화의 전체 messages (불러오기용, 요구사항 A안) |
| DELETE | `/api/conversations/{id}` | 대화 삭제 |
| POST | `/api/chat` | AI 채팅 `{message, conversation_id?}` → `{reply, conversation_id, title}` |
| GET | `/health` | 헬스 체크 (콜드스타트 깨우기) |

### Firestore 컬렉션 설계

```
data/{autoId}           { date: "YYYY-MM-DD", value: number, memo: string, created_at, updated_at? }
conversations/{autoId}  { title, messages: [{role, content, created_at}], created_at, updated_at }
```

`date`를 ISO 문자열로 저장해 문자열 정렬 = 날짜 정렬이 되도록 했습니다. 대화는 한 문서에 messages 배열로 저장합니다(과제 규모에서는 문서 1MB 한도에 충분히 여유가 있음).

### `/api/chat` 동작 흐름 (컨텍스트 주입)

```
사용자 질문 ─▶ POST /api/chat
                 │ 1. data_service.get_summary()  ← /api/data/summary 와 같은 로직
                 │ 2. build_system_prompt(summary) → 시스템 프롬프트에 요약 삽입
                 │ 3. (이어서 대화면) 이전 메시지 최대 10개 + 새 질문과 함께 GPT 호출
                 │ 4. conversations 에 user/assistant 메시지 자동 저장
                 ▼
            { reply, conversation_id }
```

실제로 주입되는 시스템 프롬프트 예시:

```
당신은 사용자의 '일별 매출' 데이터를 분석해 주는 데이터 분석 비서입니다.

[사용자 데이터 요약]
- 데이터 기간: 2026-05-01 ~ 2026-10-28
- 총 레코드: 181개
- 주요 지표: 합계 37,362,200원, 일평균 206,421원, 최대 460,200원(2026-10-09), 최소 94,500원(2026-09-25), 표준편차 50,050원
- 최근 트렌드: 상승 (최근 30일 평균이 직전 30일 대비 +13.0%)
- 최근 7일 평균: 246,486원
- 가장 최근 달: 2026-10 — 28일 기록, 합계 7,071,000원, 일평균 252,536원 (전체 일평균 대비 +22.3%)
- 월별 집계: 2026-05: 합계 5,317,000원, ... 2026-10: 합계 7,071,000원, 일평균 252,536원
[답변 규칙] 요약에 근거해 답하고 없는 수치는 지어내지 않기, 원 단위·천 단위 쉼표, 3~5문장
```

## 로컬 실행 방법

### 0) 사전 준비
1. **Firebase**: 콘솔에서 프로젝트 생성 → *Firestore Database* 만들기 → *프로젝트 설정 › 서비스 계정 › 새 비공개 키 생성* → JSON 파일을 `backend/serviceAccountKey.json`으로 저장 (`.gitignore`에 포함됨)
2. **OpenAI**: API 키 발급 (사용량 한도 설정 권장)

### 1) 백엔드
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # 값 채우기
python scripts/seed_firestore.py --reset   # 샘플 데이터 181개 업로드 (최초 1회)
uvicorn main:app --reload          # http://localhost:8000/docs
```

### 2) 프론트엔드
```bash
cd frontend
python -m http.server 5500         # http://localhost:5500
```
`frontend/config.js`의 기본 API 주소가 `http://localhost:8000`입니다. (VS Code Live Server도 5500 포트라 그대로 사용 가능)

### 3) 테스트
```bash
cd backend && pip install pytest && python -m pytest -q
```
Firestore/OpenAI를 가짜 객체로 바꿔 CRUD, 입력 검증, 컨텍스트 주입, 대화 자동 저장, 설정 오류 시 CORS 헤더 유지까지 검증합니다 (실제 키·과금 없음).

## 환경 변수

### 백엔드 (Render)
| 이름 | 필수 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | OpenAI API 키 |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | ✅ | 서비스 계정 키 **JSON 전체 문자열** (로컬은 파일 경로도 가능) |
| `ALLOWED_ORIGINS` | ✅ | CORS 허용 도메인, 쉼표 구분. 예: `https://my-app.vercel.app,http://localhost:5500` |
| `OPENAI_BASE_URL` | | OpenAI 호환 게이트웨이 주소. 예: `https://copa.codyssey.kr/v1` |
| `OPENAI_MODEL` | | 기본 `gpt-5-mini` |
| `OPENAI_MAX_TOKENS` | | 응답 토큰 상한 (gpt-5 계열은 최소 2000 적용) |
| `ALLOWED_ORIGIN_REGEX` | | Vercel 프리뷰 도메인 허용용 정규식 |
| `DATA_LABEL` / `DATA_UNIT` | | 기본 `일별 매출` / `원` |
| `CHAT_HISTORY_LIMIT` | | GPT에 함께 보낼 이전 메시지 수, 기본 `10` |

### 프론트엔드 (Vercel)
| 이름 | 필수 | 설명 |
|---|---|---|
| `API_BASE_URL` | ✅ | 백엔드 주소. 예: `https://my-api.onrender.com` |

## 배포

### 백엔드 → Render
1. GitHub에 저장소 푸시 (`.env`, 키 파일이 올라가지 않았는지 확인)
2. Render › **New › Web Service** › 저장소 선택
   - Root Directory: `ai-assistant/ai-assistant/backend` (이 저장소 기준 경로)
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Instance Type: Free
3. Environment에 위 백엔드 환경 변수 입력 (`PYTHON_VERSION=3.11.9`, 코디세이 키 사용 시 `OPENAI_BASE_URL=https://copa.codyssey.kr/v1`)
   - `FIREBASE_SERVICE_ACCOUNT_JSON`에는 키 파일 내용을 통째로 붙여넣기
4. 배포 후 https://ai-assistant-xqlg.onrender.com/docs 확인 → `POST /api/data/import-sample` 실행으로 샘플 데이터 181개 등록

(또는 저장소 루트의 `render.yaml`로 Blueprint 배포)

### 프론트엔드 → Vercel
1. Vercel › **Add New › Project** › 같은 저장소 선택
2. Root Directory: `ai-assistant/ai-assistant/frontend` (Framework Preset: Other — `vercel.json`이 빌드 설정을 지정)
3. Environment Variables: `API_BASE_URL=https://ai-assistant-xqlg.onrender.com`
4. Deploy → 발급된 Vercel 도메인을 Render의 `ALLOWED_ORIGINS`에 추가하고 백엔드 재배포

> 바닐라 JS는 브라우저에서 환경 변수를 읽을 수 없기 때문에, `build.js`가 빌드 시점에 `API_BASE_URL`을 읽어 `config.js`를 생성합니다. 프레임워크·번들러는 쓰지 않습니다.

## 설계 메모 (과제 목표 정리)

- **시계열 요약을 서비스에 활용하는 흐름** — 원본 181행을 매번 GPT에 넣으면 토큰·비용이 커지고 계산 실수도 생깁니다. 서버가 통계·추세를 정확히 **미리 계산**하고, GPT는 그 결과를 **해석·설명**하는 역할만 맡깁니다.
- **라우터/서비스 분리 기준** — 라우터는 HTTP(경로, 상태 코드, 에러 → HTTPException)만, 서비스는 비즈니스 로직(Firestore 접근, 요약, 프롬프트)만 담당합니다. 그래서 `analysis.py`를 API와 CLI 스크립트가 같이 쓰고, 테스트에서 DB만 갈아끼울 수 있습니다.
- **Pydantic 검증** — 잘못된 날짜, 음수 값, 200자 초과 메모, 빈 메시지 등을 라우터 진입 전에 422로 걸러 DB 오염과 불필요한 GPT 호출(비용)을 막습니다. 같은 모델이 Swagger 문서의 스키마가 됩니다.
- **Firestore CRUD** — 자동 ID 문서 생성(`document().set`), 정렬 조회(`order_by().stream`), 존재 확인 후 부분 수정(`update`)·삭제, 없는 ID는 404.
- **컨텍스트 주입 원리** — 모델은 학습하지 않은 내 데이터를 모르므로, 매 요청마다 최신 요약을 system 메시지로 넣어 "답변의 근거"를 제공합니다. 데이터를 수정하면 다음 질문부터 바로 반영됩니다. 요약에 없는 수치는 지어내지 말라는 규칙도 함께 넣었습니다.
- **CORS / 환경 변수 / 키 관리** — 프론트(Vercel)와 백엔드(Render)의 도메인이 달라 브라우저가 CORS 허용을 요구하며, 허용 도메인을 명시해야 다른 사이트의 무단 호출을 줄일 수 있습니다. 키가 코드·GitHub에 올라가면 도용·과금 위험이 있으므로 환경 변수로만 주입하고, 로컬과 배포 환경에서 다른 값을 쓸 수 있게 합니다.

## 비용·운영 주의
- 응답 토큰 상한(`OPENAI_MAX_TOKENS`), 이전 대화 최대 10개만 전송, 기본 모델 `gpt-5-mini`
- 테스트는 가짜 GPT로 먼저 검증 → 실제 키는 마지막에 몇 번만 호출
- OpenAI 대시보드에서 월 사용 한도 설정 권장
- 서버 내부 오류 상세는 로그에만 남기고 클라이언트에는 일반 메시지만 반환

## 제출 스크린샷

> 배포 후 직접 캡처해 `docs/screenshots/`에 넣어 주세요.

| 화면 | 파일 |
|---|---|
| 데이터 요약이 보이는 채팅 화면 (질문+답변) | ![chat](docs/screenshots/chat.png) |
| 데이터 관리 화면 (추가/수정/삭제 중 1개 동작) | ![data](docs/screenshots/data.png) |
| 대화 기록 화면 (불러오기 동작) | ![history](docs/screenshots/history.png) |
| Swagger UI | ![swagger](docs/screenshots/swagger.png) |
