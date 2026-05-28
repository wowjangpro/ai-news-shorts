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

PROMPT='오늘 주요 뉴스를 선정해서 유튜브 쇼츠 영상을 만들고 공개 업로드해줘.

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
6. python scripts/batch_run.py 실행 (자동으로 공개 업로드됨)
7. memory/generated_topics.md에 오늘 다룬 주제 기록 (기존 오늘 날짜 섹션에 추가)
8. 결과를 디스코드로 알려줘

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
