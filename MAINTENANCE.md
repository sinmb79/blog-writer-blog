# The 4th Path — 유지관리 가이드

> 시스템을 안정적으로 운영하기 위해 주기적으로 확인할 항목들.

---

## 일간 (매일 1회)

### 블로그 파이프라인 확인
```bash
cd C:\Users\sinmb\workspace\blog-writer-blog

# 1. 수집 실행
python bots/collector_bot.py

# 2. 미처리 글감 확인
ls data/topics/$(date +%Y%m%d)_*.json 2>/dev/null | wc -l

# 3. 수동 검토 대기 글 확인
ls data/pending_review/*_pending.json 2>/dev/null | wc -l
```

### 로그 이상 확인
```bash
# 에러만 필터
grep -i "error\|fail\|exception" logs/writer.log | tail -5
grep -i "error\|fail\|exception" logs/publisher.log | tail -5
```

---

## 주간 (매주 월요일)

### 1. 발행 현황 집계
```bash
cd C:\Users\sinmb\workspace\blog-writer-blog

# 이번 주 발행 건수
ls data/published/ | wc -l

# 코너별 분포
python -c "
import json, glob
corners = {}
for f in glob.glob('data/published/*.json'):
    d = json.loads(open(f, encoding='utf-8').read())
    c = d.get('corner', '미분류')
    corners[c] = corners.get(c, 0) + 1
for k, v in sorted(corners.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v}건')
"
```

### 2. 품질 경고 리뷰
```bash
# 품질 이슈가 있었던 원고 확인
python -c "
import json, glob
for f in sorted(glob.glob('data/originals/*.json'))[-10:]:
    d = json.loads(open(f, encoding='utf-8').read())
    issues = d.get('quality_issues', [])
    if issues:
        print(f'{d.get(\"title\", \"?\")[:30]}')
        for i in issues: print(f'  ⚠️ {i}')
"
```

### 3. OpenClaw 에이전트 상태
```bash
# 등록된 에이전트 확인
openclaw agents list

# blog-writer 세션 정리 (오래된 세션 삭제)
ls -lt C:\Users\sinmb\.openclaw\agents\blog-writer\sessions\ | head -5
```

### 4. Google 토큰 만료 확인
```bash
python -c "
import json
from datetime import datetime
token = json.loads(open('token.json').read())
expiry = token.get('expiry', 'unknown')
print(f'토큰 만료: {expiry}')
"
```
만료 임박 시: `python scripts/get_token.py`

### 5. 디스크 정리
```bash
# 로그 크기 확인
du -sh logs/

# 30일 이상 된 로그 삭제
find logs/ -name "*.log" -mtime +30 -delete 2>/dev/null

# 폐기 글감 크기
du -sh data/discarded/
```

---

## 월간 (매월 1일)

### 1. persona.json 리뷰

`config/persona.json`을 열고 확인:
- [ ] 코너별 톤 가이드가 실제 발행 글과 맞는지
- [ ] 금지 표현 목록에 추가할 게 있는지
- [ ] 제목 좋은/나쁜 예시를 업데이트할 필요 있는지
- [ ] 새로운 코너를 추가할 필요 있는지

### 2. 수집 소스 점검

`config/sources.json` 확인:
- [ ] RSS 피드가 아직 유효한지 (URL 접속 확인)
- [ ] X 키워드를 시대에 맞게 업데이트할 필요 있는지
- [ ] 새로운 소스를 추가할 것이 있는지

### 3. 품질 규칙 점검

`config/quality_rules.json` 확인:
- [ ] min_score(60점)가 적절한지 (너무 낮으면 저품질 유입, 높으면 수집 부족)
- [ ] 한국 관련성 키워드 업데이트
- [ ] 에버그린 키워드 추가할 것이 있는지

### 4. 안전 키워드 점검

`config/safety_keywords.json` 확인:
- [ ] 위험 키워드 목록에 추가할 것이 있는지
- [ ] min_quality_score_for_auto(75점) 조정 필요한지

### 5. 에이전트 instructions 리뷰

각 에이전트의 instructions.md가 실제 운영과 맞는지:
- `~/.openclaw/agents/blog-writer/agent/instructions.md`
- `~/.openclaw/agents/mediaforge/agent/instructions.md`

### 6. MEMORY.md 정리

각 workspace의 MEMORY.md에서:
- [ ] 더 이상 유효하지 않은 정보 삭제
- [ ] 새로 배운 교훈 추가
- 대상: `~/.openclaw/workspace/MEMORY.md`, `mediaforge/MEMORY.md`

### 7. 의존성 업데이트
```bash
cd C:\Users\sinmb\workspace\blog-writer-blog
pip list --outdated | head -10

cd C:\Users\sinmb\workspace\mediaforge
npm outdated | head -10
```

---

## 분기별 (3개월마다)

### 1. 콘텐츠 전략 리뷰

- [ ] 코너별 발행 비율이 목표와 맞는지 (에버그린 50%, 트렌딩 30%, 개성 20%)
- [ ] 블로그 트래픽/유입 키워드 분석 (Google Analytics / Search Console)
- [ ] 시나리오→미디어 파이프라인 사용 현황
- [ ] 새로운 포맷(팟캐스트, 뉴스레터 등) 추가 필요성 검토

### 2. 에이전트 아키텍처 리뷰

- [ ] 보조 에이전트(blog-writer, mediaforge, novel-studio) 역할 분담이 적절한지
- [ ] 스킬이 실제로 사용되는지. 안 쓰는 스킬은 아카이브.
- [ ] OpenClaw 버전 업데이트 확인

### 3. 아카이브 정리
```bash
du -sh ~/.openclaw/workspace/90_archive/
```
6개월 이상 된 아카이브는 외부 백업 후 삭제 고려.

---

## 긴급 대응

### 발행 실패 시
```bash
# 1. 로그 확인
tail -20 logs/publisher.log

# 2. 토큰 확인
python scripts/get_token.py

# 3. safety_keywords.json 존재 확인
ls config/safety_keywords.json
```

### ChatGPT 형식 미준수 시
```bash
# 최근 raw output 확인
tail -50 logs/writer.log | grep "파싱 실패"

# 프롬프트 확인
python -c "from bots.writer_bot import _build_prompt; s,p = _build_prompt({'topic':'test','corner':'쉬운세상'}); print(p[-200:])"
```

원인: ChatGPT가 인사말로 응답 → `article_parser`가 자동 제거하지만, 본문 자체가 없으면 실패.
대응: `instructions.md`의 few-shot 예시를 최근 성공 원고로 업데이트.

### OpenClaw 에이전트 미응답 시
```bash
# 게이트웨이 상태
openclaw status

# 에이전트 목록
openclaw agents list

# 직접 테스트
openclaw agent --agent blog-writer --message "test" --json
```

### mediaforge 백엔드 다운 시
```bash
cd C:\Users\sinmb\workspace\mediaforge
engine doctor --json
```
ComfyUI가 꺼져 있으면 수동 시작 필요.

---

## 설정 파일 위치 한눈에 보기

| 파일 | 위치 | 용도 | 수정 빈도 |
|------|------|------|-----------|
| persona.json | blog-writer-blog/config/ | 브랜드 보이스, 코너 규칙 | 월 1회 |
| engine.json | blog-writer-blog/config/ | 글쓰기 엔진 선택 | 거의 없음 |
| quality_rules.json | blog-writer-blog/config/ | 수집 품질 기준 | 분기 1회 |
| safety_keywords.json | blog-writer-blog/config/ | 발행 안전장치 | 월 1회 |
| sources.json | blog-writer-blog/config/ | 수집 소스 | 월 1회 |
| content_types.json | blog-writer-blog/config/ | 시나리오 포맷 | 거의 없음 |
| instructions.md | ~/.openclaw/agents/*/agent/ | 에이전트 지시문 | 월 1회 |
| SOUL.md | 각 workspace/ | 에이전트 페르소나 | 분기 1회 |
| MEMORY.md | 각 workspace/ | 학습 기록 | 주 1회 |
| defaults.yaml | mediaforge/config/ | 미디어 생성 기본값 | 거의 없음 |
| hardware-profile.yaml | mediaforge/config/ | GPU/VRAM 설정 | HW 변경 시 |

---

## 자동화 후보 (향후)

현재 수동인 작업 중 자동화 가능한 것:
- [ ] 일간 수집→작성 파이프라인 → cron 또는 OpenClaw heartbeat
- [ ] 주간 발행 현황 리포트 → Telegram 자동 전송
- [ ] 토큰 만료 사전 알림 → 7일 전 Telegram 경고
- [ ] 로그 자동 정리 → 30일 초과 로그 자동 삭제 cron
