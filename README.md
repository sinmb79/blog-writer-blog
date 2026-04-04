# Blog Writer Blog

**블로그 글감 수집부터 Blogger·WordPress·Naver 자동 게시까지 — 블로그 운영 자동화 도구**

영문으로 보고 싶다면 [English Notes](./docs/README.en.md)를 열어보세요.

RSS 피드·Hacker News·GitHub Trending에서 글감을 자동으로 수집하고, AI로 블로그 초안을 작성한 다음, 내가 검수·승인하면 Blogger·WordPress·Naver에 자동으로 게시해 주는 도구입니다.

---

## 이 도구가 하는 일

한 줄로 설명하면 이렇습니다.

> "매일 글감을 찾고, AI에게 초안을 맡기고, 내가 마지막에 OK 하면 블로그에 올라간다."

구체적인 흐름은 아래와 같습니다.

```
① 글감 수집   RSS·HackerNews·GitHub Trending에서 오늘의 기사 수집
      ↓
② 초안 작성   AI(Claude·Gemini·OpenClaw)가 블로그 글 초안 작성
      ↓
③ 검수 대기   사람이 직접 확인해야 하는 글은 검수 대기 상태로 이동
      ↓
④ 승인/거절   대시보드나 CLI에서 OK 또는 반려
      ↓
⑤ 멀티 플랫폼 게시  승인된 글이 Blogger·WordPress·Naver에 자동 게시
```

---

## 이 저장소에 있는 것 / 없는 것

| 있는 것 | 없는 것 |
|--------|--------|
| 글감 수집 | 쇼츠 영상 제작 |
| AI 블로그 초안 작성 | 소설 작성 |
| 검수 승인·거절 워크플로 | SNS 배포 |
| Blogger·WordPress·Naver 자동 게시 | 어시스트 모드 |
| 웹 대시보드 | |
| CLI 도구 | |

---

## 설치 (3단계면 끝)

### 사전 준비

- [Node.js 20+](https://nodejs.org) 설치
- [Python 3.11+](https://www.python.org/downloads/) 설치
- `blog-writer-blog`용 `.env`, `token.json` 등 런타임 설정 준비
- Naver 무인 발행을 쓰려면 `python -m playwright install chromium` 실행

### 설치 + n8n 실행

```bash
git clone https://github.com/sinmb79/blog-writer-blog.git
cd blog-writer-blog

# Linux / macOS
chmod +x setup.sh
./setup.sh

# Windows (cmd.exe)
setup.bat
```

브라우저에서 [http://localhost:5678](http://localhost:5678) 를 열면 끝입니다.
워크플로우 목록에 아래 5개가 바로 보여야 합니다.

- Blog Daily Pipeline
- Blog Write Queue
- Blog Publish Queue
- Blog Weekly Report
- Blog Monthly Reminder

### 퍼블리싱 플랫폼 설정

기본 발행 대상은 `Blogger`입니다. WordPress와 Naver를 쓰려면 `.env.example`의 아래 항목을 채워 넣으면 됩니다.

The default publishing target is `Blogger`. To use WordPress or Naver, fill in the matching keys from `.env.example`.

```env
WP_URL=https://your-site.com
WP_USERNAME=your_username
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

NAVER_BLOG_ENABLED=false
NAVER_BLOG_URL=https://blog.naver.com/your_blog_id
NAVER_BLOG_NEW_POST_URL=https://blog.naver.com/PostWriteForm.naver
NAVER_CHROME_PROFILE_DIR=C:/Users/your-user/key/naver-blog-chrome-profile
NAVER_PUBLISH_RETRY_COUNT=3

BANANAPRO_API_KEY=
OPENAI_API_KEY=
```

Naver 무인 발행은 전용 계정과 전용 Chrome 프로필을 한 번 로그인해 둔 뒤 재사용하는 방식입니다. 대표 이미지는 `기존 image_path -> BananaPro -> OpenAI` 순서로 준비됩니다.

Naver unattended publishing reuses a dedicated logged-in Chrome profile. The representative image fallback order is `existing image_path -> BananaPro -> OpenAI`.

### 수동 앱 설정이 필요할 때

👉 **[docs/BEGINNER_GUIDE_KO.md](docs/BEGINNER_GUIDE_KO.md)**

Python 환경, Google OAuth, Blogger 게시 설정, 대시보드 수동 실행은 위 가이드를 참고하세요.

### 기존 대시보드 직접 실행 방법

```powershell
# 1. 가상환경 활성화
venv\Scripts\activate

# 2. 백엔드 실행
python -m uvicorn dashboard.backend.server:app --port 8080 --reload

# 3. 새 터미널에서 프런트엔드 실행
cd dashboard\frontend
npm run dev

# 4. 브라우저에서 접속
# http://localhost:5173
```

---

## 주요 CLI 명령어

```powershell
bw collect                                  # 글감 수집
bw write                                    # AI로 초안 작성
bw write "주제 직접 입력"                    # 특정 주제로 바로 작성
bw write --publish-now --platform wordpress # 작성 후 지정 플랫폼에 즉시 게시
bw review list                              # 검수 대기 목록
bw review approve data\pending_review\파일  # 승인 → 원래 요청한 플랫폼으로 게시
bw review reject  data\pending_review\파일  # 반려
bw publish --platform blogger               # Blogger 발행 (기본값)
bw publish --platform wordpress             # WordPress 발행
bw publish --platform both                  # Blogger + WordPress 동시 발행
bw publish --platform naver                 # Naver 무인 발행
bw publish --platform all                   # Blogger + WordPress + Naver 동시 발행
bw status                                   # 현재 상태 한눈에 보기
bw doctor                                   # 설정 이상 여부 진단
```

---

## 접속 주소

| 주소 | 설명 |
|------|------|
| http://localhost:5173 | 웹 대시보드 |
| http://localhost:8080/docs | API 문서 (FastAPI Swagger) |

---

## 라이선스

MIT License
