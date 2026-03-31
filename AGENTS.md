# The 4th Path — 에이전트 운영 가이드

> 이 문서는 OpenClaw 에이전트(`main`)가 blog-writer-blog 시스템을 운영할 때 참조하는 설명서다.

## 시스템 개요

**The 4th Path**는 AI 기반 블로그 자동 운영 + 멀티포맷 콘텐츠 생성 시스템이다.

- **블로그**: https://www.the4thpath.com (Google Blogger)
- **운영사**: 22B Labs
- **태그라인**: AI 시대의 독립 미디어. 기술을 쉽게 설명하고, 숨은 도구를 발굴하고, 팩트를 검증합니다.

## 연결된 에이전트

| 에이전트 | 역할 | 프로젝트 |
|----------|------|----------|
| `main` | 글 수집, 작성, 발행, 시나리오 생성 | blog-writer-blog |
| `mediaforge` | 이미지/영상/오디오 생성 | mediaforge |

---

## 파이프라인 전체 흐름

```
[수집] collector_bot → data/topics/
         ↓
[작성] writer_bot → data/originals/
         ↓
[검수] 안전장치 → data/pending_review/ (위험 시)
         ↓
[발행] publisher_bot → Blogger API → data/published/
         ↓ (선택)
[시나리오] scenario_bot → data/scenarios/ → mediaforge 에이전트
```

---

## 봇별 사용법

### 1. collector_bot — 글감 수집

```bash
python bots/collector_bot.py
```

- RSS(GeekNews, ZDNet, Yonhap, Bloter), GitHub Trending, Product Hunt, Hacker News에서 글감 수집
- 품질 점수 60점 이상만 통과 (한국 관련성, 신선도, 검색 수요, 출처 신뢰도, 수익성)
- 코너 자동 분류: 쉬운세상, 숨은보물, 바이브리포트, 팩트체크, 한컷
- 출력: `data/topics/YYYYMMDD_*.json`

### 2. writer_bot — 글 작성

```bash
# 오늘 날짜 미처리 글감 처리 (최대 3개)
python bots/writer_bot.py

# 직접 글감 지정
python bots/writer_bot.py --topic "Claude Code 사용법" --corner 쉬운세상

# 글감 JSON 파일 지정
python bots/writer_bot.py --file data/topics/20260331_example.json
```

- OpenClaw(ChatGPT) 엔진으로 Blogger-ready HTML 원고 생성
- 코너별 톤/구조/품질 기준이 `config/persona.json`에 정의됨
- 품질 guardrail: 제목 길이, 본문 길이, h2 태그, 금지 표현 자동 검증
- 출력: `data/originals/YYYYMMDD_*.json`

### 3. publisher_bot — Blogger 발행

```bash
python bots/publisher_bot.py
```

- 안전장치: 팩트체크 코너/위험 키워드/출처 부족/품질 점수 미달 → 수동 검토
- HTML 조합: JSON-LD(SEO) + 3줄 요약 + 목차 + 본문(AdSense 슬롯) + 출처 + 면책문구
- Blogger API v3로 발행 + Telegram 알림
- 출력: `data/published/YYYYMMDD_*.json`

### 4. scenario_bot — 시나리오 생성

```bash
# 아이디어에서 숏폼 대본
python bots/scenario_bot.py --idea "Claude Code 30초 소개" --format short_script

# 블로그 원고에서 롱폼 대본
python bots/scenario_bot.py --from-article data/originals/20260331_example.json --format long_script

# 웹툰 시나리오
python bots/scenario_bot.py --idea "AI가 그림 그리는 원리" --format webtoon_scenario
```

**포맷 옵션:**
| 포맷 | 설명 | media-forge 연동 |
|------|------|------------------|
| `short_script` | 30-60초 숏폼 (릴스/숏츠) | `video.from-text` 9:16 |
| `long_script` | 3-10분 롱폼 (유튜브) | `video.from-text` 16:9 |
| `webtoon_scenario` | 4-8컷 정보 웹툰 | `image.generate` 3:4 |

- 출력: `data/scenarios/YYYYMMDD_*_{format}_{id}.json`
- visual_note는 영어로 작성됨 (media-forge 프롬프트로 직접 사용)

---

## 코너 (카테고리) 가이드

| 코너 | 톤 | 용도 |
|------|-----|------|
| **쉬운세상** | 친절한 선생님 | 복잡한 기술을 쉽게 설명하는 가이드 |
| **숨은보물** | 절제된 추천 | 잘 안 알려진 유용한 도구/서비스 발굴 |
| **바이브리포트** | 냉정한 분석가 | 기술 트렌드 분석 리포트 |
| **팩트체크** | 중립적 수사관 | 떠도는 정보의 사실 검증 (항상 수동 검토) |
| **한컷** | 임팩트 한마디 | 짧은 텍스트로 핵심 전달 |

---

## 설정 파일 맵

| 파일 | 역할 | 수정 빈도 |
|------|------|-----------|
| `config/persona.json` | 브랜드 보이스, 코너별 가이드, 글쓰기 규칙, Blogger 설정, 시나리오 가이드 | 자주 |
| `config/engine.json` | 글쓰기 엔진 선택 (openclaw/claude/gemini) | 드물게 |
| `config/content_types.json` | 포맷별 제약조건, media-forge 연동 스키마 | 드물게 |
| `config/sources.json` | 수집 소스 (RSS, GitHub, Product Hunt 등) | 가끔 |
| `config/quality_rules.json` | 품질 점수 기준, 폐기 규칙 | 드물게 |
| `config/safety_keywords.json` | 위험 키워드, 수동 검토 트리거 | 드물게 |

---

## 데이터 디렉토리

```
data/
├── topics/          ← collector 수집 글감
├── collected/       ← (예비)
├── originals/       ← writer 생성 원고
├── pending_review/  ← 수동 검토 대기
├── published/       ← 발행 완료 이력
├── discarded/       ← 폐기된 글감
└── scenarios/       ← scenario_bot 생성 시나리오 (→ mediaforge)
```

---

## media-forge 연동

scenario_bot이 생성하는 JSON은 media-forge가 바로 소비할 수 있는 형식이다.

**handoff 예시:**
```json
{
  "request_id": "uuid",
  "format": "short_script",
  "title_ko": "제목",
  "scenes": [
    {
      "seq": 1,
      "desc_ko": "장면 설명",
      "narration": "나레이션 (한국어)",
      "visual_note": "English visual description for image/video prompt",
      "duration_sec": 5
    }
  ],
  "media_forge_options": {
    "aspect_ratio": "9:16",
    "quality": "draft"
  }
}
```

**mediaforge 에이전트 명령 예시:**
```bash
# 이미지 생성 (웹툰 컷)
openclaw agent --agent mediaforge --message "forge image generate --prompt '{visual_note}' --aspect-ratio 3:4 --json"

# 영상 생성 (숏폼 장면)
openclaw agent --agent mediaforge --message "forge video from-text --desc '{desc_ko}' --aspect-ratio 9:16 --json"
```

---

## 글쓰기 품질 규칙 (요약)

- **제목**: 40자 이내, 클릭베이트 금지
- **본문**: 코너별 최소 길이 (쉬운세상/바이브리포트 800자, 숨은보물/팩트체크 600자, 한컷 150자)
- **구조**: `<h2>` 필수 (한컷 제외), 문단당 4문장 이내
- **금지 표현**: "혁명적인", "충격적인", "완벽한 가이드", "오늘은 ~에 대해 알아보겠습니다" 등
- **원칙**: 전문용어에 설명 필수, 과장 금지, 출처 있는 주장만, 짧은 문장

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 글쓰기 엔진 응답 비어 있음 | OpenClaw timeout 또는 에이전트 미응답 | `config/engine.json`에서 timeout 확인, OpenClaw 상태 확인 |
| 파싱 실패 | 엔진이 섹션 헤더 형식 미준수 | `logs/writer.log`에서 raw output 확인, 프롬프트 조정 |
| Blogger 발행 실패 | token.json 만료 | `python scripts/get_token.py` 재실행 |
| 수동 검토 대기 | 안전장치 작동 | 대시보드에서 승인/거부, 또는 `safety_keywords.json` 조정 |
| 인코딩 깨짐 | Windows cp949 | engine_loader에 `encoding="utf-8"` 이미 적용됨 |
