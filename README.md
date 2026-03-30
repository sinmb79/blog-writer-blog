# Blog Writer Blog

**블로그 글감 수집부터 Blogger 자동 게시까지 — 블로그 운영 자동화 도구**

RSS 피드·Hacker News·GitHub Trending에서 글감을 자동으로 수집하고, AI로 블로그 초안을 작성한 다음, 내가 검수·승인하면 Blogger에 자동으로 게시해 주는 도구입니다.

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
⑤ Blogger 게시  승인된 글이 내 Blogger 블로그에 자동 게시
```

---

## 이 저장소에 있는 것 / 없는 것

| 있는 것 | 없는 것 |
|--------|--------|
| 글감 수집 | 쇼츠 영상 제작 |
| AI 블로그 초안 작성 | 소설 작성 |
| 검수 승인·거절 워크플로 | SNS 배포 |
| Blogger 자동 게시 | 어시스트 모드 |
| 웹 대시보드 | |
| CLI 도구 | |

---

## 빠른 시작 (이미 설정이 완료된 경우)

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

처음 설치하는 분은 아래 상세 가이드를 참고하세요.

---

## 상세 설치 가이드

👉 **[docs/BEGINNER_GUIDE_KO.md](docs/BEGINNER_GUIDE_KO.md)**

Google OAuth 설정·설치·실행·트러블슈팅을 단계별로 자세하게 설명한 가이드입니다.
처음 사용하는 분은 이 문서를 먼저 읽어보세요.

---

## 주요 CLI 명령어

```powershell
bw collect                                  # 글감 수집
bw write                                    # AI로 초안 작성
bw write "주제 직접 입력"                    # 특정 주제로 바로 작성
bw write --publish-now                      # 작성 후 즉시 게시
bw review list                              # 검수 대기 목록
bw review approve data\pending_review\파일  # 승인 → Blogger 게시
bw review reject  data\pending_review\파일  # 반려
bw publish                                  # 초안 전체 게시
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
