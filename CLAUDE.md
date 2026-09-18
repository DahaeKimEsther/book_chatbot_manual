# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 이 리포지토리에서 코드 작업을 할 때 참고해야 할 지침을 제공합니다.

## 언어 및 커뮤니케이션 규칙

- **기본 응답 언어**: 한국어
- **코드 주석**: 한국어로 작성
- **커밋 메시지**: 한국어로 작성
- **문서화**: 한국어로 작성
- **변수명/함수명**: 영어 (코드 표준 준수)

## 프로젝트 개요

**book_chatbot**은 LangGraph와 OpenAI를 기반으로 한 다중 에이전트 기반의 책 검색 및 추천 챗봇입니다. 주요 기능:
- 책 검색 (알라딘 API, 네이버 책 API 활용)
- 책 추천 (키워드 생성을 통한 추천)
- 독서 메모 기록 (책 정보 + 읽은 페이지 + 감상 구조화 추출)
- 다중 의도 분류 및 순차적 라우팅
- PostgreSQL 기반 상태 지속성

## 아키텍처

### 핵심 컴포넌트

**두 가지 병렬 에이전트 아키텍처:**

1. **`src/book_chatbot/graph.py` — LangGraph StateGraph** (다중 의도 라우팅)
   - 단일 사용자 메시지에서 여러 의도를 분류
   - 각 의도를 전문 핸들러로 순차적으로 라우팅
   - `ToolNode`와 `tools_condition`을 통한 조건부 라우팅 사용
   - 지원 의도: book_search, book_recommendation, introduce_features
   - `add_messages` 리듀서를 통해 도구 결과가 state.messages에 자동 누적
   - PostgreSQL에 상태를 체크포인트하여 지속성/재개 지원

2. **`src/book_chatbot/agent.py` — LangChain Agents** (도구 조율)
   - `book_search_agent`: 키워드 추출 및 검색 도구 호출
   - `book_keyword_recommend_agent`: 키워드를 통한 추천 생성
   - `book_memo_agent`: 책 메타데이터 + 읽은 페이지 + 감상을 구조화된 `BookMemoRecord`로 추출
   - `supervisor_agent`: 세 가지 에이전트를 조율하는 상위 오케스트레이터
   - 에이전트 호출을 래핑하는 고수준 도구 정의 (`book_search`, `book_recommendation`, `book_memo`)

### 도구 계층 (`src/book_chatbot/tool.py`)

- **`basic_book_search`**: 알라딘 API 래퍼; 제목, 저자, 출판사, 링크, ISBN, 출판일 반환
- **`price_description_book_search`**: 네이버 API 래퍼; 할인 가격 및 책 설명 반환
- **`keyword_generator`**: 추천을 위한 LLM 기반 키워드 추출
- **`book_memo_analyzer`**: 자유 형식 텍스트에서 읽은 페이지 + 감상 LLM 기반 추출

### UI 계층

**`streamlit/app.py`** — 진입점; .env 로드, 인증 상태에 따라 분기
**`streamlit/chat.py`** — 에이전트를 사용하는 채팅 인터페이스
**`streamlit/login.py`** — 사용자 인증
**`streamlit/db.py`** — PostgreSQL 사용자/세션 관리

### 스키마 (`src/book_chatbot/schema.py`, `src/book_chatbot/tool_schema.py`)

- `OverallState`: 그래프 상태용 TypedDict (messages, classification, remaining_intents, draft_response, search_results)
- `IntentClassifications`: 의도 목록 (하위 쿼리 포함)
- `BookMemoRecord`: 책 메타데이터(제목, 저자, 출판사, ISBN) + 메모 데이터(읽은 페이지, 감상)를 결합한 Pydantic 모델
- 도구 검증용 API 파라미터 스키마

### 인프라

**PostgreSQL** (Docker 통): LangGraph 체크포인트 저장소
- 연결: `localhost:${POSTGRES_PORT}` (기본값 5432)
- 데이터베이스 이름, 사용자, 비밀번호는 .env에서 로드
- `docker/postgres/init.sql`로 초기화

## 자주 사용하는 명령어

### 초기 설정

**⚠️ 가상환경 필수:** 이 프로젝트는 `chatbot` 콘다 환경에서만 실행됩니다.

```bash
# 가상환경 활성화
conda activate chatbot

# 의존성 설치
poetry install

# .env 파일 생성 및 설정
# (아래 섹션 참고)
```

### PostgreSQL 실행
```bash
# 프로젝트 루트에서 실행
docker compose --env-file .env -f docker/docker-compose.yaml up -d

# 실행 확인
docker ps | grep bookchatbot-postgres
```

### 개발

**Streamlit UI (개발용)**
```bash
cd streamlit
streamlit run app.py
```
- 진입점에서 .env 로드
- 인증 필요 (db.py 설정 없으면 테스트 사용자 기본값)

**LangGraph CLI (대화형 그래프 테스트)**
```bash
# ⚠️ Windows에서 필수: UTF-8 인코딩 설정 (먼저 실행)
chcp 65001

# 가상환경 활성화
conda activate chatbot

# 프로젝트 루트에서 실행 (langgraph.json 위치)
langgraph dev

# http://localhost:2024에서 로컬 스튜디오 열기 (그래프 시각화 및 테스트)
```

**직접 에이전트 테스트**
```bash
# book_memo_agent (agent.py 메인 블록)
python -m book_chatbot.agent

# 에이전트 호출을 통한 개별 에이전트
python -c "from book_chatbot.agent import book_search_agent; ..."
```

### 테스트

**모든 테스트 실행**
```bash
pytest
```

**특정 테스트 실행**
```bash
pytest test/test_book_memo_agent.py::test_book_memo_agent -v
```

**출력 표시하며 실행 (print 문)**
```bash
pytest -s test/test_book_memo_agent.py
```

**테스트 설정 참고**: `test/conftest.py`는 모듈 임포트 **전에** .env를 명시적으로 로드합니다. LLM 클라이언트(ChatOpenAI)가 임포트 시점에 인스턴스화되기 때문입니다.

## 환경 변수 (.env)

필수 변수:
```
OPENAI_API_KEY=<your-key>
ALADIN_API_KEY=<your-aladin-api-key>
NAVER_CLIENT_ID=<naver-book-api-client-id>
NAVER_CLIENT_SECRET=<naver-book-api-secret>

POSTGRES_USER=<db-user>
POSTGRES_PASSWORD=<db-password>
POSTGRES_DB=<db-name>
POSTGRES_PORT=5432  # 선택사항, 기본값 5432
```

**주의사항**: graph.py는 임포트 시점에 이 Postgres 변수에 하드 의존합니다. .env가 없거나 변수가 설정되지 않으면 `langgraph dev` 실행 시 그래프 초기화 중 조용히 실패합니다.

## 주요 설계 패턴

### 다중 의도 라우팅 (graph.py)
1. 사용자 메시지 → `classify_intent`에서 모든 의도 + 하위 쿼리 추출
2. 첫 번째 의도 처리, 나머지는 상태에 큐잉
3. 도구 결과 후 `route_next_intent`에서 다음 의도 디스패치
4. 큐가 빌 때까지 반복 → `draft_response`에서 최종 답변 합성

### 도구 바인딩 및 조건부 엣지 (graph.py)
- LLM은 `.bind_tools([...])`를 통해 도구에 바인딩됨
- `tools_condition` 유틸리티는 응답에 도구 호출이 포함되어 있는지 확인
- 있으면 → ToolNode로 라우팅; 없으면 → 다음 단계로 이동

### 구조화된 출력 (agent.py, book_memo_agent)
- `llm.with_structured_output(BookMemoRecord)`는 응답에 Pydantic 스키마 강제
- 결과는 `result["structured_response"]`로 접근 가능

### 상태 누적 (graph.py)
- `messages: Annotated[list, add_messages]` 리듀서는 도구 결과를 자동으로 추가
- 수동 메시지 중복 제거/병합 불필요

## 알려진 이슈 및 트레이드오프

자세한 내용은 `docs/issues/`를 참고:
- **260813**: langgraph-dev는 상위 디렉토리에서 발견된 .env를 집어올 수 있음 (conftest.py는 테스트에서 완화)
- **260814**: 커스텀 체크포인터 설정은 그래프 빌드 시 PostgreSQL 연결 필요
- **260315**: 다중 의도 라우팅은 순차 처리 필요 (병렬화 미구현)

## 테스트 전략

- `test/` 디렉토리의 pytest를 통한 단위 테스트
- conftest.py는 모듈 임포트 전 .env 로드 보장
- book_memo_agent는 구조화된 출력 검증 (pages_read는 정수로 파싱되어야 함 등)
- 통합 테스트는 실제 알라딘/네이버 API에 의존 (목킹 없음)

## 향후 작업 노트

- graph.py와 agent.py는 두 가지 별도 구현; 가능하면 통합
- Streamlit 인증은 현재 simple db.py 로직 사용; 프로덕션용 OAuth 고려
- API 속도 제한 미구현 (알라딘/네이버)
- LangGraph 지속성은 PostgreSQL이 항상 실행 중이라고 가정; 메모리 내 체크포인터로의 폴백 추가 고려
