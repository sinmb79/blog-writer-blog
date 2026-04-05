# The 4th Path — Agent Instructions

> "AI 시대의 독립 미디어. 기술을 쉽게 설명하고, 숨은 도구를 발굴하고, 팩트를 검증합니다."

_Global instructions (`~/.codex/AGENTS.md`) apply here. This file adds project-specific context only._

---

## Every Session

1. Read `SOUL.md` — your identity and boundaries
2. Read `USER.md` — 보스's preferences
3. Read `TOOLS.md` — service URLs and paths
4. Check engine status if writing: `config/engine.json`

---

## What This Project Is

The 4th Path is the **voice** of 22B Labs. Where mediaforge makes visuals and 22b-studio orchestrates pipelines, you **write, curate, and publish**.

- **Blog**: https://www.the4thpath.com (Google Blogger)
- **Operator**: 22B Labs
- **Mission**: Make tech accessible. Find hidden gems. Verify facts.

```
[수집] collector → data/topics/
    ↓
[작성] writer → data/originals/
    ↓
[검수] safety check → data/pending_review/ (if flagged)
    ↓
[발행] publisher → Blogger API → data/published/
    ↓ (optional)
[시나리오] scenario_bot → data/scenarios/ → mediaforge
```

---

## Connected Systems

| System | Role | How |
|--------|------|-----|
| **OpenClaw/ChatGPT** | Writing engine | API via `config/engine.json` |
| **Blogger API v3** | Publishing | OAuth token (local only) |
| **Telegram** (chat_id: 226731503) | Publish alerts | Bot API |
| **mediaforge** | Visual content from scenarios | File handoff: `data/scenarios/` |
| **n8n** (`localhost:5678`) | Workflow automation | HTTP API |

---

## The Four Bots

### 1. collector_bot — Find Stories

```bash
python bots/collector_bot.py
```

- Sources: RSS (GeekNews, ZDNet, Yonhap, Bloter), GitHub Trending, Product Hunt, Hacker News
- Quality score ≥ 60 to pass (Korea relevance, freshness, search demand, source trust, revenue potential)
- Auto-classified into corners
- Output: `data/topics/YYYYMMDD_*.json`

### 2. writer_bot — Write Articles

```bash
# Process today's unwritten topics (max 3)
python bots/writer_bot.py

# Specify topic directly
python bots/writer_bot.py --topic "Claude Code 사용법" --corner 쉬운세상

# From topic JSON file
python bots/writer_bot.py --file data/topics/20260331_example.json
```

- Generates Blogger-ready HTML via OpenClaw engine
- Corner-specific tone/structure defined in `config/persona.json`
- Quality guardrails: title length, body length, h2 tags, banned phrases
- Output: `data/originals/YYYYMMDD_*.json`

### 3. publisher_bot — Publish to Blog

```bash
python bots/publisher_bot.py
```

- Safety gates: fact-check corner / risky keywords / missing sources / low quality → manual review
- HTML assembly: JSON-LD (SEO) + 3-line summary + TOC + body (AdSense slots) + sources + disclaimer
- Publishes via Blogger API v3 + Telegram notification
- Output: `data/published/YYYYMMDD_*.json`

### 4. scenario_bot — Generate Visual Scenarios

```bash
# From idea → short-form script
python bots/scenario_bot.py --idea "Claude Code 30초 소개" --format short_script

# From article → long-form script
python bots/scenario_bot.py --from-article data/originals/20260331_example.json --format long_script

# Webtoon scenario
python bots/scenario_bot.py --idea "AI가 그림 그리는 원리" --format webtoon_scenario
```

| Format | Description | MediaForge Integration |
|--------|-------------|----------------------|
| `short_script` | 30-60s short (Reels/Shorts) | `video.from-text` 9:16 |
| `long_script` | 3-10min long (YouTube) | `video.from-text` 16:9 |
| `webtoon_scenario` | 4-8 panel info webtoon | `image.generate` 3:4 |

Output: `data/scenarios/YYYYMMDD_*_{format}_{id}.json`
`visual_note` is always in English (directly usable as mediaforge prompt).

---

## Corners (Categories)

Each corner has a distinct voice. Respect it.

| Corner | Tone | Purpose |
|--------|------|---------|
| **쉬운세상** | 친절한 선생님 / Kind teacher | Complex tech explained simply |
| **숨은보물** | 절제된 추천 / Restrained curator | Hidden useful tools and services |
| **바이브리포트** | 냉정한 분석가 / Cool analyst | Tech trend analysis reports |
| **팩트체크** | 중립적 수사관 / Neutral investigator | Fact verification (always manual review) |
| **한컷** | 임팩트 한마디 / One-shot impact | Core message in minimal text |

---

## Writing Quality Rules

| Rule | Standard |
|------|----------|
| **Title** | ≤ 40 chars. No clickbait |
| **Body length** | 쉬운세상/바이브리포트 ≥ 800자, 숨은보물/팩트체크 ≥ 600자, 한컷 ≥ 150자 |
| **Structure** | `<h2>` required (except 한컷). ≤ 4 sentences per paragraph |
| **Banned phrases** | "혁명적인", "충격적인", "완벽한 가이드", "오늘은 ~에 대해 알아보겠습니다" |
| **Principles** | Jargon must be explained. No exaggeration. Claims need sources. Short sentences |

---

## Config Files

| File | Purpose | Edit Frequency |
|------|---------|---------------|
| `config/persona.json` | Brand voice, corner guides, writing rules, Blogger settings | Often |
| `config/engine.json` | Writing engine selection (openclaw/claude/gemini) | Rarely |
| `config/content_types.json` | Format constraints, mediaforge integration schema | Rarely |
| `config/sources.json` | Collection sources (RSS, GitHub, Product Hunt, etc.) | Sometimes |
| `config/quality_rules.json` | Quality scoring criteria, discard rules | Rarely |
| `config/safety_keywords.json` | Risky keywords, manual review triggers | Rarely |

---

## Data Directory

```
data/
├── topics/          ← Collected story seeds
├── originals/       ← Written articles
├── pending_review/  ← Awaiting manual review
├── published/       ← Published history
├── discarded/       ← Discarded items
└── scenarios/       ← Visual scenarios → mediaforge
```

---

## MediaForge Handoff

scenario_bot output is directly consumable by mediaforge.

<details>
<summary>📦 Handoff JSON structure</summary>

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

</details>

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Empty engine response | OpenClaw timeout / agent unresponsive | Check timeout in `config/engine.json`, verify OpenClaw status |
| Parse failure | Engine didn't follow section header format | Check raw output in `logs/writer.log`, adjust prompt |
| Blogger publish failed | token.json expired | Re-run `python scripts/get_token.py` |
| Stuck in pending_review | Safety gate triggered | Approve/reject in dashboard, or adjust `safety_keywords.json` |
| Encoding broken | Windows cp949 | Already handled: `encoding="utf-8"` in engine_loader |

---

## Remember

Words are not content. Words are **trust**.
Every article published under The 4th Path either earns a reader's trust or burns it.
There is no middle ground.

Write like the reader's time matters. Because it does.
