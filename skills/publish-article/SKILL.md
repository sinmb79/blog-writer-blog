---
name: publish-article
description: 작성된 원고를 안전장치 검사 후 Google Blogger에 발행한다. "발행", "publish", "게시", "올려줘" 키워드 시 활성화.
---

# Publish Article

## 실행
```bash
cd C:\Users\sinmb\workspace\blog-writer-blog
python bots/publisher_bot.py
```

## 안전장치 (config/safety_keywords.json)
자동 발행 차단 → 수동 검토 대기 조건:
- 팩트체크 코너 (항상)
- 위험 키워드 (암호화폐/투자/법률/비판)
- 출처 2개 미만
- 품질 점수 75점 미만

## 발행 시 생성되는 HTML 구조
```
JSON-LD (SEO) → 3줄 요약 → 접이식 목차 → 본문(+AdSense) → 출처 → 면책문구
```

## 라벨 전략
- 1순위: 코너 (쉬운세상, 숨은보물 등)
- 2순위: 태그
- 최대 10개

## 수동 검토 대기 글 처리
```bash
# 대기 목록 확인
python -c "from bots.publisher_bot import get_pending_list; [print(f'{p[\"title\"]} - {p[\"pending_reason\"]}') for p in get_pending_list()]"

# 승인
python -c "from bots.publisher_bot import approve_pending; approve_pending('data/pending_review/파일.json')"
```

## 출력
- 성공: `data/published/YYYYMMDD_*_{post_id}.json` + Blogger URL
- 대기: `data/pending_review/YYYYMMDD_*_pending.json`
- Telegram 알림 자동 발송

## 보고
```
✅ 발행 완료: {title} → {blogger_url}
또는
⚠️ 수동 검토 대기: {title} — 사유: {reason}
```
