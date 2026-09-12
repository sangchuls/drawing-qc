# 도면 QC 웹앱

건축 도면 PDF와 법규/QC 체크리스트(PDF·Excel)를 업로드하면, 체크리스트 항목별로 도면에서
근거를 찾아 판정하고(pass/check/error), 마킹된 도면 PDF와 체크리스트 Excel 리포트를 만들어 줍니다.
원래 Claude Code 스킬(`.claude/skills/drawing-review`)로 하던 검토를 팀이 웹에서 쓸 수 있게
만든 버전입니다.

## 구조

```
apps/web/   Next.js — 프런트엔드 (Vercel 배포)
apps/api/   FastAPI — 도면 처리 + Claude API 기반 AI 검토 (Railway/Fly.io 등 상시 서버 배포)
scripts/    원래 세션에서 쓴 로컬 전용 스크립트 (참고용, 웹앱 동작에는 사용 안 함)
```

브라우저는 도면/체크리스트 파일을 **FastAPI 백엔드에 직접** 업로드합니다(Vercel 서버리스
함수의 요청 크기·실행시간 제한을 피하기 위해). Next.js는 로그인 게이트와 업로드 인증 토큰
발급만 담당합니다.

## 로컬 개발

### 1) 백엔드 (apps/api)

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/activate          # Windows(Git Bash: source .venv/Scripts/activate)
pip install -r requirements.txt
cp .env.example .env             # 값 채우기 (아래 "환경변수" 참고)
uvicorn app.main:app --reload --port 8000
```

### 2) 프런트엔드 (apps/web)

```bash
cd apps/web
npm install
cp .env.local.example .env.local # 값 채우기 — UPLOAD_TOKEN_SECRET은 apps/api/.env와 동일해야 함
npm run dev
```

`http://localhost:3000` 접속 → 공유 비밀번호 입력 → 도면 업로드.

## 환경변수

### apps/web (`.env.local`)
| 변수 | 설명 |
|---|---|
| `SHARED_PASSWORD` | 팀 공유 로그인 비밀번호 |
| `SESSION_SECRET` | 세션 쿠키 서명용 임의 문자열 |
| `UPLOAD_TOKEN_SECRET` | 업로드 인증 토큰 서명용 — **apps/api와 동일한 값** |
| `NEXT_PUBLIC_API_BASE_URL` | FastAPI 백엔드 주소 (브라우저가 직접 호출) |

### apps/api (`.env`)
| 변수 | 설명 |
|---|---|
| `UPLOAD_TOKEN_SECRET` | apps/web과 동일한 값 |
| `FRONTEND_ORIGIN` | CORS 허용 origin (Vercel 배포 주소) |
| `DATA_DIR` | 업로드/결과 파일 저장 경로 (Railway/Fly의 영구 볼륨 경로 지정 권장) |
| `MAX_DRAWING_MB` | 업로드 가능한 도면 PDF 최대 용량 (기본 150MB) |
| `ANTHROPIC_MODEL` / `OPENAI_MODEL` / `GOOGLE_MODEL` / `XAI_MODEL` | 제공자별 모델 이름 (선택, 기본값 있음) |

LLM API 키는 서버 환경변수로 두지 않습니다. 각 사용자가 프론트엔드에서 자신의 API 키를
입력하며(아래 참고), 검토 요청 시에만 브라우저 → 백엔드로 전달되어 그 자리에서 쓰이고
디스크에 저장되지 않습니다.

## 배포

1. **GitHub**: 이 리포를 push.
2. **Vercel**: `apps/web`을 프로젝트 루트로 지정해 연결, 위 env var 등록.
3. **Railway / Fly.io 등**: `apps/api`를 Python 앱으로 배포(uvicorn 실행), 위 env var 등록,
   `DATA_DIR`이 가리키는 경로에 영구 볼륨을 붙여야 재배포 후에도 기존 작업 결과가 남습니다.
4. 두 서비스 배포 후 `NEXT_PUBLIC_API_BASE_URL`(web)과 `FRONTEND_ORIGIN`(api)을 서로의
   실제 주소로 맞춰주세요.

## 동작 방식

1. 업로드된 도면 PDF에서 페이지별 텍스트+좌표, 그리고 표제란의 도면번호(A-101 등)를
   자동으로 인식합니다(`apps/api/app/drawing.py`). 도면번호가 세로쓰기 등으로 두 조각
   ("A-" + "001")으로 나뉘어 추출되는 경우도 자동으로 붙여서 인식합니다.
2. 체크리스트 파일을 구조화된 항목 목록으로 변환합니다(`app/checklist.py`). 한국 건축
   인허가 표준 서식(건축법 별표2 체크리스트, □/■ 표기)은 전용 파서로, 그 외 Excel은 행 단위로,
   체크리스트가 없으면 기본 항목으로 처리합니다.
3. 선택한 LLM(Claude/GPT/Gemini/Grok 중 하나)이 각 항목에 대해 도면 텍스트 검색 도구를
   사용해 근거를 찾고 판정합니다 (`app/providers/`) — 원래 세션에서 사람이 손으로 하던
   "키워드 검색 → 근거 페이지 확인 → 판정/코멘트 작성" 과정을 자동화한 것입니다. 제공자와
   API 키는 업로드 화면에서 사용자가 직접 선택/입력하며, 키는 브라우저에만 개별 저장됩니다.
4. 근거가 실제로 있는 항목만 도면에 구름/설명 마킹을 하고(`app/mark.py`), 서로 겹치지
   않도록 자동 배치합니다. 근거를 못 찾은 항목은 도면에 가짜 위치를 표시하지 않고 색인
   페이지/Excel에만 "찾을 수 없음"으로 남깁니다.
5. 마킹된 PDF 맨 앞에 전체 항목 색인 페이지를 삽입하고(`app/report.py`), 같은 내용을
   Excel로도 만듭니다.

## 알려진 한계

- 설계개요표 등이 **이미지로 삽입된 도면**은 텍스트 검색으로 값을 확인할 수 없어
  "찾을 수 없음"으로 표시됩니다(예: 개요표가 스캔/캡처 이미지인 경우의 건폐율·용적률).
  향후 OCR을 추가하면 개선 가능합니다.
- 체크리스트 PDF가 페이지 경계에서 항목이 쪼개져 렌더링되는 극히 일부 케이스는
  "대상법규아님" 판정이 아닌 일반 항목으로 분류될 수 있습니다(빈도 낮음, AI 검토 단계에서
  거를 못 찾으면 어차피 "미확인"으로 표시되어 큰 영향은 없음).
- 인증은 팀 공유 비밀번호 1개뿐이며 개인별 계정/권한 분리는 없습니다.
- LLM API 키는 브라우저 localStorage에 평문으로 저장됩니다 — 공용 PC에서는 사용 후
  브라우저 데이터를 지우는 것을 권장하며, 브라우저를 바꾸거나 데이터를 지우면 다시
  입력해야 합니다.
- Job 상태는 파일 기반(폴더+status.json)으로 저장되며 별도 DB/큐는 없습니다 — 동시 사용자가
  많아지면 Postgres + 작업 큐로 교체를 검토하세요.
