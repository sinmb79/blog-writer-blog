---
name: collect-topics
description: RSS/GitHub/ProductHunt/HackerNews에서 글감을 수집하고 품질 점수로 필터링한다. "수집", "collect", "글감", "토픽" 키워드 시 활성화.
---

# Collect Topics

## 실행
```bash
cd C:\Users\sinmb\workspace\blog-writer-blog
python bots/collector_bot.py
```

## 소스 (config/sources.json)
- RSS: GeekNews, ZDNet Korea, Yonhap IT, Bloter
- GitHub Trending (Python, JavaScript)
- Product Hunt (일일)
- Hacker News (Top 30)

## 품질 기준 (config/quality_rules.json)
- 60점 이상만 통과 (한국 관련성 30 + 신선도 20 + 검색 수요 20 + 출처 신뢰 15 + 수익성 15)
- 폐기: 한국 무관, 출처 불명, 중복 80%+, 7일+ 지남, 광고성, 클릭베이트

## 코너 자동 분류
- 에버그린(가이드/튜토리얼) → 쉬운세상 또는 숨은보물
- 트렌딩(GitHub/ProductHunt) → 숨은보물
- 그 외 → 쉬운세상

## 출력
- `data/topics/YYYYMMDD_*.json`
- 폐기: `data/discarded/YYYYMMDD_discarded.jsonl`

## 보고
```
✅ 수집 완료: {통과}건 / 폐기 {폐기}건
```
