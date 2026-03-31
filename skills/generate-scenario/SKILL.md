---
name: generate-scenario
description: 아이디어 또는 블로그 원고에서 숏폼/롱폼/웹툰 시나리오를 생성한다. "시나리오", "숏폼", "롱폼", "웹툰", "대본" 키워드 시 활성화.
---

# Generate Scenario

## 아이디어에서 생성
```bash
cd C:\Users\sinmb\workspace\blog-writer-blog
python bots/scenario_bot.py --idea "아이디어 텍스트" --format short_script
```

## 블로그 원고에서 파생
```bash
python bots/scenario_bot.py --from-article data/originals/파일.json --format webtoon_scenario
```

## 포맷 옵션
| 포맷 | 설명 | mediaforge 연동 |
|------|------|------------------|
| `short_script` | 30-60초 숏폼 대본 | 9:16, wan22 |
| `long_script` | 3-10분 롱폼 대본 | 16:9, wan22 |
| `webtoon_scenario` | 4-8컷 웹툰 | 3:4, sdxl |

## 출력 (media-forge handoff JSON)
- 경로: `data/scenarios/YYYYMMDD_{format}_{id}.json`
- 핵심 필드:
  - `scenes[].visual_note` — 영어 이미지/영상 프롬프트
  - `scenes[].narration` — 한국어 나레이션
  - `scenes[].duration_sec` — 장면 길이
  - `media_forge_options` — 기본 생성 옵션

## mediaforge 전달
생성된 시나리오를 mediaforge에게 넘기려면:
```bash
openclaw agent --agent mediaforge --message "engine scenario ingest data/scenarios/파일.json --json"
```

## 보고
```
✅ 시나리오 생성 완료
- 제목: {title_ko}
- 포맷: {format}
- 장면: {scene_count}개
- 파일: {path}
```
