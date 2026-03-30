# 처음 쓰는 사람을 위한 블로그 자동화 완전 가이드

이 문서는 `blog-writer-blog`를 처음 접하는 분을 위해 썼습니다.
"설치부터 Blogger 게시까지" 전 과정을 선배가 옆에서 알려주듯 하나씩 짚어드릴게요.
명령어만 던져놓지 않고, **왜 이 명령을 실행하는지**도 같이 설명합니다.

---

## 이 가이드를 읽기 전에

이 도구가 하는 일을 딱 한 문장으로 정리하면 이렇습니다.

> "매일 글감을 찾고, AI에게 초안을 맡기고, 내가 마지막에 OK 하면 블로그에 올라간다."

흐름은 이렇습니다.

```
① 글감 수집   RSS·HackerNews·GitHub Trending에서 오늘의 기사 자동 수집
      ↓
② 초안 작성   AI(OpenClaw·Claude·Gemini)가 블로그 글 초안 작성
      ↓
③ 검수 대기   사람이 직접 확인해야 하는 글은 검수 대기 상태로 이동
      ↓
④ 승인/거절   대시보드나 CLI에서 OK 또는 반려
      ↓
⑤ Blogger 게시  승인된 글이 내 Blogger 블로그에 자동 게시
```

중간에 사람이 한 번 확인하는 단계가 있어서, AI가 이상한 글을 써도 직접 거를 수 있습니다. 완전 자동이 아니라 "반자동"이라고 생각하면 됩니다.

---

## 1단계 — 준비물 확인

설치 전에 PC에 아래 것들이 있는지 확인합니다.

**반드시 있어야 하는 것**

- **Python 3.11 이상**
  `python --version`을 터미널에 입력했을 때 `Python 3.11.x` 이상이 나와야 합니다.
  없으면 [python.org](https://www.python.org/downloads/)에서 받습니다. 설치할 때 "Add Python to PATH" 체크박스를 꼭 체크하세요.

- **Node.js 18 이상**
  웹 대시보드(프런트엔드)를 실행할 때 필요합니다.
  `node --version`으로 확인합니다. 없으면 [nodejs.org](https://nodejs.org/)에서 LTS 버전을 받습니다.

- **Blogger를 운영하는 Google 계정**
  블로그 게시 기능을 쓰려면 Blogger 블로그가 하나 있어야 합니다.
  [blogger.com](https://www.blogger.com/)에서 먼저 블로그를 만들어두세요.

**선택 사항 (있으면 더 좋은 것)**

- Claude API 키 → 앤트로픽 AI로 글을 쓸 때
- Gemini API 키 → Google AI로 글을 쓸 때
- 기본 엔진인 OpenClaw는 별도 API 키가 없어도 무료로 동작합니다.

---

## 2단계 — 저장소 내려받기

터미널(PowerShell)을 열고 아래 명령을 입력합니다.

```powershell
git clone https://github.com/sinmb79/blog-writer-blog.git
cd blog-writer-blog
```

이 명령은 GitHub에서 코드를 내 PC로 복사해오는 것입니다. `blog-writer-blog` 폴더가 생기면 성공입니다.

---

## 3단계 — Python 가상환경 만들기

가상환경이 뭔지 모르더라도 괜찮습니다. 간단히 설명하면, 이 프로젝트 전용 Python 환경을 따로 만드는 겁니다. 다른 프로젝트와 충돌하지 않도록 격리하는 좋은 습관입니다.

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

각 명령이 하는 일:

- `python -m venv venv` — `venv`라는 이름의 가상환경 폴더를 만듭니다.
- `venv\Scripts\activate` — 가상환경을 켭니다. 이 명령 다음부터는 이 프로젝트 전용 Python이 사용됩니다. 터미널 앞에 `(venv)`가 붙으면 정상입니다.
- `pip install --upgrade pip` — pip를 최신 버전으로 올립니다.
- `pip install -r requirements.txt` — 이 프로젝트에 필요한 Python 패키지를 전부 설치합니다.
- `pip install -e .` — `bw` 명령어를 터미널에서 바로 쓸 수 있게 등록합니다.

> 나중에 새 터미널을 열 때마다 `venv\Scripts\activate`를 먼저 실행해야 합니다.
> 이 명령을 빠뜨리면 `bw` 명령을 못 찾는다는 오류가 납니다.

---

## 4단계 — 프런트엔드(웹 대시보드) 설치

```powershell
cd dashboard\frontend
npm install
cd ..\..
```

`npm install`은 대시보드 화면에 필요한 JavaScript 패키지를 설치하는 명령입니다. `node_modules` 폴더가 생기면 성공입니다. 시간이 좀 걸릴 수 있습니다. 기다리면 됩니다.

---

## 5단계 — 환경설정 파일 만들기

프로젝트 루트에 `.env`라는 파일을 만들어야 합니다. API 키나 블로그 ID 같은 민감한 정보는 코드에 직접 넣지 않고 이 파일에 따로 보관합니다.

먼저 예시 파일을 복사합니다.

```powershell
copy .env.example .env
```

그 다음 메모장이나 VS Code로 `.env` 파일을 열고, 아래 값들을 채웁니다.

```
BLOG_MAIN_ID=         ← Blogger 블로그 ID (아래에서 찾는 방법 설명)
BLOG_SITE_URL=        ← 블로그 주소 (예: https://myblog.blogspot.com)
GOOGLE_CLIENT_ID=     ← Google OAuth 클라이언트 ID
GOOGLE_CLIENT_SECRET= ← Google OAuth 클라이언트 시크릿
GOOGLE_REFRESH_TOKEN= ← 나중에 token.json에서 확인 가능
ANTHROPIC_API_KEY=    ← Claude 사용 시 (선택)
GEMINI_API_KEY=       ← Gemini 사용 시 (선택)
TELEGRAM_BOT_TOKEN=   ← Telegram 알림 시 (선택)
TELEGRAM_CHAT_ID=     ← Telegram 알림 시 (선택)
```

**Blogger 블로그 ID 찾는 방법**

[blogger.com](https://www.blogger.com/) → 내 블로그 대시보드 → 주소창을 보면 이런 형태입니다.

```
https://www.blogger.com/blog/posts/1234567890123456789
```

저 긴 숫자가 `BLOG_MAIN_ID`입니다.

---

## 6단계 — Google OAuth 설정 (가장 중요한 단계)

이 단계가 처음 설정하는 분들이 가장 헷갈리는 부분입니다. 차근차근 따라오세요.
Blogger에 글을 자동으로 게시하려면 Google의 허락이 필요합니다. 그 허락 과정이 OAuth입니다.

### 6-1. Google Cloud Console에서 프로젝트 만들기

1. [console.cloud.google.com](https://console.cloud.google.com/)에 접속합니다.
2. 상단의 프로젝트 드롭다운 → **새 프로젝트**를 클릭합니다.
3. 이름은 아무거나 짓습니다. 예: `blog-writer`

### 6-2. Blogger API 활성화하기

1. 왼쪽 메뉴 → **API 및 서비스** → **라이브러리**
2. 검색창에 `Blogger` 입력
3. **Blogger API v3** 클릭 → **사용** 버튼 클릭

### 6-3. OAuth 동의 화면 설정

1. 왼쪽 메뉴 → **API 및 서비스** → **OAuth 동의 화면**
2. **외부** 선택 → **만들기**
3. 앱 이름 입력 (아무거나), 이메일 주소 입력
4. 저장하고 계속 → 나머지는 기본값으로 넘깁니다.
5. **테스트 사용자** 항목에 본인 Google 이메일을 추가합니다. 이 단계를 빠뜨리면 나중에 "이 앱이 검증되지 않았습니다" 오류가 납니다.

### 6-4. OAuth 클라이언트 ID 만들기

1. 왼쪽 메뉴 → **API 및 서비스** → **사용자 인증 정보**
2. 상단 **+ 사용자 인증 정보 만들기** → **OAuth 클라이언트 ID**
3. 애플리케이션 유형: **데스크톱 앱** 선택
4. 이름은 아무거나 → **만들기**
5. 팝업에서 **JSON 다운로드** 클릭
6. 다운로드된 파일 이름을 `credentials.json`으로 바꿉니다.
7. 이 파일을 프로젝트 루트 폴더에 넣습니다.

```
blog-writer-blog/
├── credentials.json   ← 여기에 넣기
├── .env
├── requirements.txt
└── ...
```

### 6-5. token.json 만들기

```powershell
venv\Scripts\python scripts\get_token.py
```

실행하면 브라우저가 자동으로 열립니다. Google 계정으로 로그인하고 권한을 허용하면 됩니다.
완료되면 프로젝트 루트에 `token.json`이 생깁니다.

이 파일이 있어야 Blogger에 글을 자동으로 게시할 수 있습니다.

> **주의**: `credentials.json`, `token.json`, `.env` 이 세 파일은 절대 GitHub에 올리면 안 됩니다.
> 이 파일에는 내 Google 계정 접근 권한이 담겨 있습니다. `.gitignore`가 이미 설정되어 있으니 걱정하지 않아도 되지만, 혹시라도 직접 `git add credentials.json` 같은 명령을 치지 않도록 주의하세요.

---

## 7단계 — 설정이 맞는지 진단하기

여기까지 왔으면 한 번 점검해봅니다.

```powershell
bw doctor
```

이 명령은 설정 파일, API 키, 토큰 파일을 전부 훑어보고 문제가 있는 항목을 짚어줍니다.
이상 없다는 메시지가 나오면 본격적으로 시작할 준비가 된 겁니다.

---

## 8단계 — 처음 실행해보기 (추천 루틴)

처음에는 CLI보다 웹 대시보드로 시작하는 편이 훨씬 쉽습니다. 눈으로 흐름을 볼 수 있거든요.

### 8-1. 백엔드 실행

터미널 하나를 열고:

```powershell
venv\Scripts\activate
python -m uvicorn dashboard.backend.server:app --port 8080 --reload
```

`Application startup complete.` 메시지가 나오면 정상입니다.

### 8-2. 프런트엔드 실행

**새 터미널**을 하나 더 열고:

```powershell
cd dashboard\frontend
npm run dev
```

`Local: http://localhost:5173` 메시지가 나오면 준비된 겁니다.

### 8-3. 브라우저로 접속

[http://localhost:5173](http://localhost:5173) 에 접속합니다.

대시보드 화면이 보이면 성공입니다.

### 8-4. 글감 수집 → 초안 작성

대시보드의 **Content** 탭에서 **Run Collect + Write** 버튼을 클릭합니다.

이 버튼 하나로 아래 두 작업이 순서대로 실행됩니다.

1. GeekNews, ZDNet Korea, Yonhap IT, Bloter RSS + Hacker News + GitHub Trending + Product Hunt 에서 오늘의 기사 수집
2. AI가 수집된 내용을 바탕으로 블로그 초안 작성

완료되면 **Review** 탭에 검수 대기 중인 글 목록이 나타납니다.

### 8-5. 검수하고 게시

1. **Review** 탭에서 초안을 클릭해서 내용을 확인합니다.
2. 괜찮으면 **Approve** 클릭 → Blogger에 즉시 게시됩니다.
3. 이상하다 싶으면 **Reject** 클릭 → 폐기 처리됩니다.

**Published** 탭에서 게시된 글 목록과 링크를 확인할 수 있습니다.

---

## CLI로도 같은 작업 하기

대시보드가 열려 있지 않을 때는 CLI 명령 몇 가지로 같은 작업을 할 수 있습니다.

```powershell
# 글감 수집
bw collect

# AI로 초안 작성
bw write

# 특정 주제로 바로 작성
bw write "파이썬 3.13 새 기능 정리"

# 작성 후 즉시 게시 (검수 건너뛰기)
bw write --publish-now

# 현재 상태 한눈에 보기
bw status

# 검수 대기 목록 확인
bw review list

# 특정 글 승인 → Blogger 게시
bw review approve data\pending_review\파일이름.json

# 특정 글 반려
bw review reject data\pending_review\파일이름.json

# 초안 전체 게시
bw publish
```

---

## 글쓰기 엔진 바꾸기

기본 엔진은 OpenClaw입니다. 별도 API 키 없이 무료로 동작합니다.

Claude나 Gemini로 바꾸고 싶으면 대시보드 **Settings** 탭에서 변경하거나, `config/engine.json`을 직접 편집합니다.

```json
{
  "writing": {
    "provider": "claude"
  }
}
```

각 엔진을 사용할 때:

- `openclaw` — `.env`에 별도 키 불필요. 기본값.
- `claude` — `.env`에 `ANTHROPIC_API_KEY` 필요.
- `gemini` — `.env`에 `GEMINI_API_KEY` 필요.

---

## 파일이 어디에 저장되는지

한 번 수집하고 작성해보면 `data/` 폴더 안에 파일이 쌓이기 시작합니다.

```
data/
├── topics/          ← 수집된 원시 글감 후보
├── collected/       ← 정리된 수집 결과
├── originals/       ← AI가 작성한 초안
├── pending_review/  ← 사람이 검토해야 하는 글 (여기서 approve/reject)
├── published/       ← 게시 완료 기록
└── discarded/       ← 반려된 항목
```

파일 흐름은 이렇습니다.

```
topics → collected → originals → pending_review → published
                                               ↘ discarded
```

---

## 자주 만나는 문제와 해결법

### `bw: command not found` 또는 `bw` 명령을 못 찾을 때

가상환경이 꺼진 상태입니다. 아래를 먼저 실행하세요.

```powershell
venv\Scripts\activate
pip install -e .
```

### `ModuleNotFoundError` 오류가 날 때

필수 패키지가 설치되지 않았습니다.

```powershell
venv\Scripts\activate
pip install -r requirements.txt
```

### Blogger 게시가 안 될 때

아래를 차례로 확인합니다.

1. `.env`에 `BLOG_MAIN_ID`가 채워져 있는가?
2. 프로젝트 루트에 `credentials.json`이 있는가?
3. 프로젝트 루트에 `token.json`이 있는가?
4. 없으면 `venv\Scripts\python scripts\get_token.py` 재실행

### "이 앱이 Google에서 확인하지 않은 앱입니다" 경고가 뜰 때

Google Cloud Console → OAuth 동의 화면 → **테스트 사용자** 목록에 본인 이메일이 있는지 확인하세요. 없으면 추가합니다.

### 대시보드에 글이 하나도 안 보일 때

아직 수집과 작성을 한 번도 안 한 상태입니다.

```powershell
bw collect
bw write
```

를 먼저 실행하거나, 대시보드에서 **Run Collect + Write**를 클릭합니다.

### 포트 충돌 오류가 날 때

8080이나 5173 포트를 다른 프로그램이 쓰고 있는 경우입니다.

```powershell
# 포트를 쓰고 있는 프로세스 확인
netstat -ano | findstr :8080
netstat -ano | findstr :5173

# PID 확인 후 종료
taskkill /PID <PID번호> /F
```

---

## 보안 주의사항

아래 파일은 절대 GitHub에 올리지 마세요.

| 파일 | 이유 |
|------|------|
| `.env` | API 키, 블로그 ID 등 개인 정보 |
| `credentials.json` | Google OAuth 클라이언트 시크릿 |
| `token.json` | Google 계정 접근 토큰 |

이 저장소의 `.gitignore`에 이미 포함되어 있지만, `git add -f` 나 `git add credentials.json` 같은 강제 추가 명령은 하지 마세요.

---

## 마지막으로

처음 설정이 조금 복잡해 보여도, 한 번 설정해두면 이후부터는 이 세 명령만 기억하면 됩니다.

```powershell
bw collect    # 글감 수집
bw write      # 초안 작성
bw publish    # 게시
```

또는 대시보드를 열고 버튼 하나 누르면 끝입니다.

처음에 Google OAuth 설정이 가장 까다롭습니다. 오류가 생기면 당황하지 말고 이 문서의 6단계로 돌아와서 순서를 하나씩 다시 확인해보세요. 대부분의 문제는 `credentials.json` 위치가 틀렸거나, `token.json`이 없거나, 테스트 사용자 등록을 빠뜨린 경우입니다.
