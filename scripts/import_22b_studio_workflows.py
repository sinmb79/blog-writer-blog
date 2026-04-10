"""
22B Studio n8n 워크플로우 3개를 DB에 직접 삽입 (기존 0-node 플레이스홀더 교체)
- 22B Studio - Trend Radar   : f37ce80b-cdb7-449e-8881-bd991ede4ef8
- 22B Studio - Blog Writer   : c3c1414e-fa4d-46bc-b53e-8232009ee9c9
- 22B Studio - Daily Report  : fa5cc724-ffdc-4248-8cda-25e84b43942c

실행 후 docker restart 22b-studio-n8n 필요.
"""
import json
import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path(r"C:\Users\sinmb\workspace\22b-studio\n8n\.n8n\database.sqlite")

# IDs (기존 플레이스홀더와 동일)
TREND_RADAR_ID = "f37ce80b-cdb7-449e-8881-bd991ede4ef8"
BLOG_WRITER_ID = "c3c1414e-fa4d-46bc-b53e-8232009ee9c9"
DAILY_REPORT_ID = "fa5cc724-ffdc-4248-8cda-25e84b43942c"

BLOG_API_BASE = "http://host.docker.internal:8080/api"
TELEGRAM_BOT_TOKEN_EXPR = "{{ $env.TELEGRAM_BOT_TOKEN }}"
TELEGRAM_CHAT_ID = "226731503"

SETTINGS = {"executionOrder": "v1", "timezone": "Asia/Seoul"}
META = {"templateCredsSetupCompleted": True}


# ─── 워크플로우 정의 ────────────────────────────────────────────────────────────

def build_trend_radar() -> dict:
    """
    22B Studio - Trend Radar
    매일 07:00 → collect-topics → 결과 파싱 → Telegram 보고
    """
    nodes = [
        {
            "parameters": {
                "rule": {
                    "interval": [
                        {"field": "cronExpression", "expression": "0 0 7 * * *"}
                    ]
                }
            },
            "id": "trend-schedule",
            "name": "Daily 07:00",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [240, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": f"{BLOG_API_BASE}/automation/collect-topics",
                "options": {"timeout": 300000},
            },
            "id": "call-collect",
            "name": "Collect Topics",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [540, 300],
        },
        {
            "parameters": {
                "jsCode": r"""
const result = $input.first().json?.result || {};
const newTopics = result.new_topics || 0;
const totalTopics = result.total_topics || 0;
const topTopics = result.top_topics || [];

let lines = [];
lines.push(`📡 *트렌드 레이더 — ${new Date().toLocaleDateString('ko-KR')}*`);
lines.push('');
lines.push(`• 신규 글감: *${newTopics}건*`);
lines.push(`• 누적 대기: *${totalTopics}건*`);

if (topTopics.length > 0) {
  lines.push('');
  lines.push('🔥 *오늘의 핫 토픽*');
  topTopics.slice(0, 5).forEach((t, i) => {
    const score = t.quality_score ? ` [${t.quality_score}점]` : '';
    const corner = t.corner ? ` → ${t.corner}` : '';
    lines.push(`${i+1}. ${t.topic}${score}${corner}`);
  });
}

lines.push('');
lines.push('_blog-writer 파이프라인은 09:00에 실행됩니다._');

return [{ json: { text: lines.join('\n') } }];
"""
            },
            "id": "format-report",
            "name": "Format Report",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [840, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": f"https://api.telegram.org/bot{{{{$env.TELEGRAM_BOT_TOKEN}}}}/sendMessage",
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {"name": "chat_id", "value": TELEGRAM_CHAT_ID},
                        {"name": "text", "value": "={{ $json.text }}"},
                        {"name": "parse_mode", "value": "Markdown"},
                    ]
                },
                "options": {},
            },
            "id": "send-telegram",
            "name": "Send Telegram",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [1140, 300],
        },
    ]

    connections = {
        "Daily 07:00": {"main": [[{"node": "Collect Topics", "type": "main", "index": 0}]]},
        "Collect Topics": {"main": [[{"node": "Format Report", "type": "main", "index": 0}]]},
        "Format Report": {"main": [[{"node": "Send Telegram", "type": "main", "index": 0}]]},
    }

    return {"nodes": nodes, "connections": connections}


def build_blog_writer() -> dict:
    """
    22B Studio - Blog Writer
    매일 09:00 → daily-pipeline (collect + write + publish) → Telegram 결과
    """
    nodes = [
        {
            "parameters": {
                "rule": {
                    "interval": [
                        {"field": "cronExpression", "expression": "0 0 9 * * *"}
                    ]
                }
            },
            "id": "blog-schedule",
            "name": "Daily 09:00",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [240, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": f"{BLOG_API_BASE}/automation/daily-pipeline",
                "options": {"timeout": 600000},
            },
            "id": "call-pipeline",
            "name": "Run Daily Pipeline",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [540, 300],
        },
        {
            "parameters": {
                "jsCode": r"""
const success = $input.first().json?.success;
const result = $input.first().json?.result || {};
const status = success ? '✅' : '❌';
const today = new Date().toLocaleDateString('ko-KR');

const lines = [
  `${status} *블로그 파이프라인 — ${today}*`,
  '',
  `상태: ${success ? '성공' : '실패'}`,
];

if (result.published !== undefined) {
  lines.push(`발행: ${result.published}건`);
}
if (result.written !== undefined) {
  lines.push(`작성: ${result.written}건`);
}
if (result.error) {
  lines.push(`오류: ${result.error}`);
}

return [{ json: { text: lines.join('\n') } }];
"""
            },
            "id": "format-result",
            "name": "Format Result",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [840, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "https://api.telegram.org/bot{{$env.TELEGRAM_BOT_TOKEN}}/sendMessage",
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {"name": "chat_id", "value": TELEGRAM_CHAT_ID},
                        {"name": "text", "value": "={{ $json.text }}"},
                        {"name": "parse_mode", "value": "Markdown"},
                    ]
                },
                "options": {},
            },
            "id": "notify-telegram",
            "name": "Notify Telegram",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [1140, 300],
        },
    ]

    connections = {
        "Daily 09:00": {"main": [[{"node": "Run Daily Pipeline", "type": "main", "index": 0}]]},
        "Run Daily Pipeline": {"main": [[{"node": "Format Result", "type": "main", "index": 0}]]},
        "Format Result": {"main": [[{"node": "Notify Telegram", "type": "main", "index": 0}]]},
    }

    return {"nodes": nodes, "connections": connections}


def build_daily_report() -> dict:
    """
    22B Studio - Daily Report
    매일 21:00 → 통계 수집 → Telegram 일일 리포트
    """
    nodes = [
        {
            "parameters": {
                "rule": {
                    "interval": [
                        {"field": "cronExpression", "expression": "0 0 21 * * *"}
                    ]
                }
            },
            "id": "report-schedule",
            "name": "Daily 21:00",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [240, 300],
        },
        {
            "parameters": {
                "url": f"{BLOG_API_BASE}/overview",
                "options": {"timeout": 30000},
            },
            "id": "get-overview",
            "name": "Get Overview",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [540, 300],
        },
        {
            "parameters": {
                "jsCode": r"""
const data = $input.first().json || {};
const today = new Date().toLocaleDateString('ko-KR');

const stats = data.stats || data || {};
const topics = stats.topics_pending ?? stats.topics ?? '-';
const originals = stats.originals_pending ?? stats.originals ?? '-';
const published_today = stats.published_today ?? stats.published ?? '-';
const errors = stats.errors_today ?? stats.errors ?? 0;

const lines = [
  `📊 *일일 리포트 — ${today}*`,
  '',
  `• 글감 대기: *${topics}건*`,
  `• 원고 대기: *${originals}건*`,
  `• 오늘 발행: *${published_today}건*`,
  `• 오류: ${errors > 0 ? '⚠️ ' + errors + '건' : '없음'}`,
  '',
  '_The 4th Path 블로그 자동화 시스템_',
];

return [{ json: { text: lines.join('\n') } }];
"""
            },
            "id": "format-daily",
            "name": "Format Daily Report",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [840, 300],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "https://api.telegram.org/bot{{$env.TELEGRAM_BOT_TOKEN}}/sendMessage",
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {"name": "chat_id", "value": TELEGRAM_CHAT_ID},
                        {"name": "text", "value": "={{ $json.text }}"},
                        {"name": "parse_mode", "value": "Markdown"},
                    ]
                },
                "options": {},
            },
            "id": "send-report",
            "name": "Send Daily Report",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [1140, 300],
        },
    ]

    connections = {
        "Daily 21:00": {"main": [[{"node": "Get Overview", "type": "main", "index": 0}]]},
        "Get Overview": {"main": [[{"node": "Format Daily Report", "type": "main", "index": 0}]]},
        "Format Daily Report": {"main": [[{"node": "Send Daily Report", "type": "main", "index": 0}]]},
    }

    return {"nodes": nodes, "connections": connections}


# ─── DB 업데이트 ────────────────────────────────────────────────────────────────

WORKFLOWS = [
    (TREND_RADAR_ID, "22B Studio - Trend Radar", build_trend_radar),
    (BLOG_WRITER_ID, "22B Studio - Blog Writer", build_blog_writer),
    (DAILY_REPORT_ID, "22B Studio - Daily Report", build_daily_report),
]


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"n8n DB not found: {DB_PATH}")

    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()

    for wf_id, name, builder in WORKFLOWS:
        wf = builder()
        nodes = wf["nodes"]
        connections = wf["connections"]
        ver_id = str(uuid.uuid4())

        cur.execute(
            """UPDATE workflow_entity
               SET nodes = ?, connections = ?, settings = ?, meta = ?,
                   active = 1, versionId = ?, triggerCount = 1,
                   versionCounter = versionCounter + 1,
                   updatedAt = datetime('now')
               WHERE id = ?""",
            (
                json.dumps(nodes),
                json.dumps(connections),
                json.dumps(SETTINGS),
                json.dumps(META),
                ver_id,
                wf_id,
            ),
        )
        rows_updated = cur.rowcount
        if rows_updated == 0:
            print(f"[WARN] {name}: 레코드 없음 — INSERT 시도")
            cur.execute(
                """INSERT INTO workflow_entity
                   (id, name, active, nodes, connections, settings, pinData,
                    versionId, triggerCount, meta, isArchived, versionCounter)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    wf_id, name, 1,
                    json.dumps(nodes), json.dumps(connections),
                    json.dumps(SETTINGS), "{}",
                    ver_id, 1, json.dumps(META), 0, 1,
                ),
            )
        print(f"[OK] {name}: {len(nodes)} 노드 업데이트")

    con.commit()
    try:
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        print("WAL checkpoint OK")
    except Exception as e:
        print(f"WAL checkpoint skipped (Docker 컨테이너 활성 중): {e}")
    con.close()
    print("\n완료. 이제 `docker restart 22b-studio-n8n` 실행 필요.")


if __name__ == "__main__":
    main()
