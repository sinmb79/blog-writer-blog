---
name: write-article
description: 글감(topic)을 받아 코너별 톤/구조에 맞는 Blogger HTML 원고를 생성한다. "글 써줘", "작성", "write", "원고" 키워드 시 활성화.
---

# Write Article

## 실행 방법 3가지

### 미처리 글감 일괄 (기본)
```bash
cd C:\Users\sinmb\workspace\blog-writer-blog
python bots/writer_bot.py --limit 3
```

### 직접 주제 지정
```bash
python bots/writer_bot.py --topic "주제" --corner 숨은보물
```

### topic JSON 파일 지정
```bash
python bots/writer_bot.py --file data/topics/파일명.json
```

## topic JSON 직접 생성 시 템플릿
```json
{
  "topic": "주제 제목",
  "corner": "숨은보물",
  "description": "핵심 포인트와 배경. 구체적일수록 글 품질이 올라간다.",
  "source": "https://출처URL",
  "source_url": "https://출처URL",
  "published_at": "2026-03-31",
  "quality_score": 85
}
```
파일명: `data/topics/YYYYMMDD_슬러그.json`

## 코너별 톤 (config/persona.json)
| 코너 | 톤 | 최소 길이 |
|------|-----|----------|
| 쉬운세상 | 친절한 선생님. 비유 필수. | 800자 |
| 숨은보물 | 절제된 추천. 기능+가격+대안. | 600자 |
| 바이브리포트 | 냉정한 분석가. 데이터+전망. | 800자 |
| 팩트체크 | 중립 수사관. 교차검증+판정. | 600자 |
| 한컷 | 임팩트 한마디. | 150자 |

## 품질 guardrail (자동)
- 제목 40자 이내
- 금지 표현 감지 ("혁명적", "충격적" 등)
- h2 태그 존재 확인
- 코너별 최소 길이

## 출력
- `data/originals/YYYYMMDD_*.json`
- 품질 경고: `article.quality_issues` 배열로 기록됨

## 보고
```
✅ 글 작성 완료
- 제목: {title}
- 코너: {corner}
- 파일: {path}
- 경고: {quality_issues 또는 없음}
```
