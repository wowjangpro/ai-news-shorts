#!/bin/bash
# 하루 2회(10시, 15시) 뉴스 최대 10개 자동 생성 + 공개 업로드
# LaunchAgent에서 호출됨

PROJECT_DIR="/Users/jeniel/Works/ai-news-shorts"
CLAUDE_PATH="/Users/jeniel/.local/bin/claude"
LOG_FILE="$PROJECT_DIR/output/daily_news.log"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/Users/jeniel/.local/bin:$PATH"

echo "======================================" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') 데일리 뉴스 시작" >> "$LOG_FILE"
echo "======================================" >> "$LOG_FILE"

# 이전 영상/스크립트 삭제 (오늘 날짜 파일만 보존)
TODAY=$(date '+%Y%m%d')
OUTPUT_DIR="$PROJECT_DIR/output"
deleted=0
for f in "$OUTPUT_DIR"/*.mp4 "$OUTPUT_DIR"/*_script_*.json; do
    [ -f "$f" ] || continue
    if [[ "$(basename "$f")" != *"$TODAY"* ]]; then
        rm "$f"
        deleted=$((deleted + 1))
    fi
done
echo "$(date '+%Y-%m-%d %H:%M:%S') 이전 영상 ${deleted}개 삭제" >> "$LOG_FILE"

# 이전 배치 JSON 삭제 — 이번 실행에서 Claude가 새로 작성한 JSON만 렌더링하도록
# (이전 배치의 stale JSON 재업로드 방지). batch_*.json은 .gitignore 대상.
rm -f "$PROJECT_DIR"/scripts/batch_*.json

# 디스코드 시작 알림
cd "$PROJECT_DIR"
python3 -c "
import urllib.request, json, sys
sys.path.insert(0, '.')
from config.settings import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID
if DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID:
    msg = '📰 뉴스 자동 생성 시작 ($(date '+%H')시 배치)'
    data = json.dumps({'content': msg}).encode()
    req = urllib.request.Request(f'https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages', data=data, headers={'Authorization': f'Bot {DISCORD_BOT_TOKEN}', 'Content-Type': 'application/json', 'User-Agent': 'DiscordBot (ai-news-shorts, 1.0)'})
    urllib.request.urlopen(req, timeout=10)
" >> "$LOG_FILE" 2>&1

CURRENT_HOUR=$(date '+%H')

PROMPT='오늘 주요 뉴스를 선정해서 유튜브 쇼츠 영상 제작용 데이터(batch JSON)를 준비해줘.
영상 렌더링·공개 업로드는 이 작업이 끝난 직후 래퍼 스크립트가 자동으로 이어서 실행한다.

현재 시각: '"$CURRENT_HOUR"'시 배치

규칙:
- 최대 10개까지 생성하되, 추천할 만한 주제가 부족하면 10개를 채우지 않아도 됨
- 하루 2회(10시, 15시) 실행되므로 같은 날 이미 다룬 주제는 절대 중복 금지
- memory/generated_topics.md를 반드시 확인하여 오늘 날짜에 이미 기록된 주제 제외

작업 순서:
1. WebSearch로 오늘 한국 주요 뉴스 검색 (여러 매체가 동시에 보도하는 뉴스 우선)
2. memory/generated_topics.md에서 오늘 이미 다룬 주제 확인 → 중복 제외
3. 선정된 주제 목록을 디스코드로 미리 알림 (번호 + 제목 리스트)
4. 선정된 뉴스 개수만큼 scripts/batch_01.json ~ batch_NN.json 작성 (script-format.md 참조)
5. 각 뉴스별 팩트체크 (최소 3개 언론사 기사 대조)
5-1. 작성된 JSON 파일 한글 깨짐 검증 — 각 batch JSON을 Read로 읽어서 \\ufffd 문자가 있으면 해당 파일을 다시 작성해줘. 깨진 글자가 없어질 때까지 재작성.
6. memory/generated_topics.md에 오늘 선정한 주제 기록 (기존 오늘 날짜 섹션에 추가, 같은 날 2배치 중복 방지용). 업로드 URL은 영상 생성 후 결정되므로 제목·핵심 요약만 기록하면 된다.
7. 준비 완료(선정 N건·JSON 작성·검증 완료)를 디스코드로 알림

⚠️ 매우 중요: scripts/batch_run.py 를 절대 직접 실행하지 마라(백그라운드/포그라운드 모두 금지).
헤드리스(-p) 세션이 끝나면 백그라운드 자식 프로세스가 강제 종료되어 영상이 중간에 죽는다.
JSON 작성·검증·기록까지만 하고 작업을 종료해라. 영상 렌더링과 공개(public) 업로드는
이 세션 종료 직후 래퍼 스크립트(daily_news.sh)가 foreground로 직접 실행한다.

디스코드 전송 코드:
import urllib.request, json
from config.settings import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID
data = json.dumps({"content": "메시지"}).encode()
req = urllib.request.Request(f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages", data=data, headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json", "User-Agent": "DiscordBot (ai-news-shorts, 1.0)"})
urllib.request.urlopen(req, timeout=10)'

cd "$PROJECT_DIR"

# 행(hang) 상태 방지: 2시간 상한 watchdog
TIMEOUT_SECS=7200

"$CLAUDE_PATH" -p "$PROMPT" \
    --dangerously-skip-permissions \
    --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Agent,Skill" \
    >> "$LOG_FILE" 2>&1 &
CLAUDE_PID=$!

(
    sleep "$TIMEOUT_SECS"
    if kill -0 "$CLAUDE_PID" 2>/dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') ⚠️ ${TIMEOUT_SECS}초 초과 — claude(PID $CLAUDE_PID) 강제 종료" >> "$LOG_FILE"
        kill -TERM "$CLAUDE_PID" 2>/dev/null
        sleep 30
        kill -KILL "$CLAUDE_PID" 2>/dev/null
    fi
) &
WATCHDOG_PID=$!

wait "$CLAUDE_PID"
CLAUDE_EXIT=$?
kill "$WATCHDOG_PID" 2>/dev/null
wait "$WATCHDOG_PID" 2>/dev/null

echo "$(date '+%Y-%m-%d %H:%M:%S') 데일리 뉴스 완료 (exit=$CLAUDE_EXIT)" >> "$LOG_FILE"

# ── 영상 생성·공개 업로드 — 래퍼가 직접 foreground 실행 ────────────────────
# Claude(-p)가 batch_run.py를 백그라운드로 띄우면 응답 종료와 함께 자식
# 프로세스가 SIGKILL되어 영상이 일러스트 생성 도중 죽는 문제를 방지.
# Claude는 batch_*.json 작성까지만 하고, 실제 렌더링·업로드는 여기서 수행.
BATCH_LOG="$OUTPUT_DIR/batch_${CURRENT_HOUR}h_${TODAY}.log"

shopt -s nullglob
batch_jsons=("$PROJECT_DIR"/scripts/batch_*.json)
shopt -u nullglob

if [ "${#batch_jsons[@]}" -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') ⚠️ batch_*.json 없음 — 영상 생성 건너뜀 (Claude가 JSON을 작성하지 못함)" >> "$LOG_FILE"
    "$PROJECT_DIR/.venv/bin/python" -c "
import urllib.request, json, sys
sys.path.insert(0, '$PROJECT_DIR')
from config.settings import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID
if DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID:
    data = json.dumps({'content': '⚠️ 배치 JSON이 없어 영상 생성을 건너뜀 ($(date '+%H')시 배치)'}).encode()
    req = urllib.request.Request(f'https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages', data=data, headers={'Authorization': f'Bot {DISCORD_BOT_TOKEN}', 'Content-Type': 'application/json', 'User-Agent': 'DiscordBot (ai-news-shorts, 1.0)'})
    urllib.request.urlopen(req, timeout=10)
" >> "$LOG_FILE" 2>&1
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') 🎬 배치 영상 생성 시작 (${#batch_jsons[@]}개, foreground) → $BATCH_LOG" >> "$LOG_FILE"

    # 배치도 행(hang) 방지: 2시간 상한 watchdog
    "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/scripts/batch_run.py" >> "$BATCH_LOG" 2>&1 &
    BATCH_PID=$!

    (
        sleep "$TIMEOUT_SECS"
        if kill -0 "$BATCH_PID" 2>/dev/null; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') ⚠️ ${TIMEOUT_SECS}초 초과 — batch_run(PID $BATCH_PID) 강제 종료" >> "$LOG_FILE"
            kill -TERM "$BATCH_PID" 2>/dev/null
            sleep 30
            kill -KILL "$BATCH_PID" 2>/dev/null
        fi
    ) &
    BATCH_WATCHDOG_PID=$!

    wait "$BATCH_PID"
    BATCH_EXIT=$?
    kill "$BATCH_WATCHDOG_PID" 2>/dev/null
    wait "$BATCH_WATCHDOG_PID" 2>/dev/null

    echo "$(date '+%Y-%m-%d %H:%M:%S') 🎬 배치 영상 생성 완료 (exit=$BATCH_EXIT)" >> "$LOG_FILE"
fi
