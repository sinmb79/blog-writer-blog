# 블로그 자동화 앱 초보자 가이드

이 문서는 `blog-writer-blog`를 처음 사용하는 사람도 혼자서 설치하고, 글을 수집하고, 글을 작성하고, 검수하고, Blogger에 게시할 수 있도록 순서대로 설명하는 안내서입니다.

## 1. 이 프로그램으로 할 수 있는 일

이 앱은 아래 흐름만 담당합니다.

1. 글감 수집
2. 블로그 글 초안 생성
3. 검수 대기
4. Blogger 게시
5. 대시보드에서 상태 확인

이 저장소에는 쇼츠, 소설, SNS 배포 같은 기능은 들어 있지 않습니다.

## 2. 준비물

사용 전에 아래 항목이 필요합니다.

- Windows PC
- Python 3.11 이상
- Node.js 18 이상
- Blogger를 운영하는 Google 계정
- GitHub에서 저장소를 내려받을 수 있는 기본 사용법

선택 사항:

- Claude API 키
- Gemini API 키
- OpenClaw CLI
- Telegram 알림용 봇 토큰

## 3. 폴더 구조 이해하기

중요한 폴더는 아래 정도만 알면 충분합니다.

- `blogwriter/`
  CLI 명령 진입점입니다.
- `bots/`
  글감 수집, 글쓰기, 게시 로직이 들어 있습니다.
- `dashboard/`
  웹 대시보드입니다.
- `config/`
  엔진 설정, 품질 규칙, 소스 목록이 들어 있습니다.
- `data/`
  수집 결과와 초안, 검수 대기, 게시 이력이 저장됩니다.
- `logs/`
  실행 로그가 저장됩니다.
- `scripts/get_token.py`
  Blogger 게시용 `token.json` 생성 스크립트입니다.

## 4. 설치 방법

### 4-1. 저장소 내려받기

```powershell
git clone https://github.com/sinmb79/blog-writer-blog.git
cd blog-writer-blog
```

### 4-2. Python 가상환경 만들기

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

설명:

- `venv`는 이 프로젝트 전용 Python 환경입니다.
- `pip install -e .`를 하면 `bw` 명령을 사용할 수 있습니다.

### 4-3. 프런트엔드 설치

```powershell
cd dashboard\frontend
npm install
cd ..\..
```

## 5. 환경설정 파일 만들기

`.env.example`을 참고해서 `.env` 파일을 만듭니다.

```powershell
copy .env.example .env
```

최소로 중요한 값은 아래입니다.

- `BLOG_MAIN_ID`
- `BLOG_SITE_URL`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

글쓰기 엔진을 바꾸고 싶으면 아래도 입력합니다.

- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`

## 6. Blogger 게시 준비하기

이 단계가 가장 중요합니다. 게시 기능은 `token.json`이 있어야 작동합니다.

### 6-1. Google Cloud Console에서 OAuth 앱 만들기

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속합니다.
2. 프로젝트를 하나 만듭니다.
3. `Blogger API`를 활성화합니다.
4. OAuth 동의 화면을 설정합니다.
5. `OAuth client ID`를 만들 때 애플리케이션 유형은 `Desktop app`으로 선택합니다.
6. 다운로드한 JSON 파일 이름을 `credentials.json`으로 바꿉니다.
7. 이 파일을 프로젝트 루트에 넣습니다.

프로젝트 루트 예시:

- `C:\Users\sinmb\workspace\blog-writer-blog\credentials.json`

### 6-2. token.json 만들기

```powershell
venv\Scripts\python scripts\get_token.py
```

실행하면 브라우저가 열리고 Google 로그인 및 권한 허용 과정을 거칩니다. 완료되면 루트 폴더에 `token.json`이 생성됩니다.

주의:

- `credentials.json`
- `token.json`
- `.env`

이 세 파일은 민감정보가 들어 있으므로 GitHub에 올리면 안 됩니다. 이 저장소에는 `.gitignore`가 이미 설정되어 있습니다.

## 7. 실행 방법

### 7-1. CLI 도움말 보기

```powershell
venv\Scripts\bw --help
```

주요 명령:

- `bw collect`
- `bw write`
- `bw publish`
- `bw review list`
- `bw review approve <파일경로>`
- `bw review reject <파일경로>`
- `bw status`
- `bw doctor`

### 7-2. 대시보드 백엔드 실행

```powershell
venv\Scripts\python -m uvicorn dashboard.backend.server:app --port 8080 --reload
```

### 7-3. 대시보드 프런트엔드 실행

새 터미널에서:

```powershell
cd dashboard\frontend
npm run dev
```

브라우저에서 아래 주소로 접속합니다.

- `http://localhost:5173`

## 8. 실제 사용 순서

초보자는 아래 순서로 쓰면 가장 이해하기 쉽습니다.

### 방법 A. 웹 대시보드 중심으로 사용

1. 백엔드를 실행합니다.
2. 프런트엔드를 실행합니다.
3. `Content` 탭에서 `Run Collect + Write` 버튼을 누릅니다.
4. 생성된 글 초안을 확인합니다.
5. `Review` 컬럼에 검수 대기 글이 있으면 확인합니다.
6. 승인할 글은 `Approve`를 눌러 게시합니다.
7. 게시 결과는 `Published` 컬럼과 `Overview`, `Logs`에서 확인합니다.

### 방법 B. CLI 중심으로 사용

1. 글감 수집

```powershell
bw collect
```

2. 수집된 글감으로 초안 생성

```powershell
bw write
```

3. 상태 확인

```powershell
bw status
```

4. 검수 대기 목록 확인

```powershell
bw review list
```

5. 특정 검수 대기 파일 승인

```powershell
bw review approve data\pending_review\파일이름.json
```

6. 또는 초안을 바로 게시

```powershell
bw publish
```

## 9. 각 폴더에 쌓이는 파일 설명

- `data/topics/`
  수집된 원시 글감 후보
- `data/collected/`
  정리된 수집 결과
- `data/originals/`
  생성된 글 초안
- `data/pending_review/`
  사람이 검토해야 하는 글
- `data/published/`
  게시 완료 기록
- `data/discarded/`
  폐기된 항목

## 10. 글쓰기 엔진 바꾸기

대시보드 `Settings` 탭에서 글쓰기 엔진을 바꿀 수 있습니다.

선택 가능한 기본 엔진:

- `OpenClaw`
- `Claude`
- `Gemini`

추천:

- 초보자: `OpenClaw`
- API를 안정적으로 쓰고 싶은 경우: `Claude` 또는 `Gemini`

## 11. 문제 해결

### `bw` 명령이 안 보일 때

```powershell
venv\Scripts\activate
pip install -e .
```

### `ModuleNotFoundError`가 날 때

필수 패키지가 설치되지 않은 상태입니다.

```powershell
pip install -r requirements.txt
```

### Blogger 게시가 안 될 때

아래를 확인합니다.

1. `.env`에 `BLOG_MAIN_ID`가 있는지
2. 루트에 `credentials.json`이 있는지
3. 루트에 `token.json`이 있는지
4. `scripts/get_token.py`를 다시 실행해도 되는지

### 대시보드가 비어 있을 때

먼저 수집과 글쓰기를 실행해야 합니다.

```powershell
bw collect
bw write
```

또는 대시보드에서 `Run Collect + Write`를 누릅니다.

## 12. 처음 쓰는 사람에게 추천하는 가장 쉬운 루틴

아래 순서만 기억하면 됩니다.

1. 가상환경 활성화
2. 백엔드 실행
3. 프런트엔드 실행
4. 대시보드 접속
5. `Run Collect + Write`
6. `Review` 확인
7. `Approve`로 게시

## 13. 보안 주의사항

절대 GitHub에 올리면 안 되는 파일:

- `.env`
- `token.json`
- `credentials.json`

이 파일은 개인 계정과 연결되는 민감정보를 포함합니다.

## 14. 마지막 팁

처음에는 CLI보다 대시보드로 시작하는 편이 훨씬 쉽습니다. 대시보드에서 흐름을 익힌 뒤, 익숙해지면 `bw collect`, `bw write`, `bw publish` 순서로 CLI를 같이 사용하면 훨씬 빠르게 운영할 수 있습니다.
