#!/bin/bash
# 매일 아침 뉴스 10개 자동 생성 + 공개 업로드
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

PROMPT='오늘 주요 뉴스 10개를 선정해서 유튜브 쇼츠 영상을 만들고 공개 업로드해줘.

작업 순서:
1. WebSearch로 오늘 한국 주요 뉴스 검색 (여러 매체가 동시에 보도하는 뉴스 우선)
2. memory/generated_topics.md에서 이미 다룬 주제 확인 → 중복 제외
3. 10개 뉴스 각각 scripts/batch_01.json ~ batch_10.json 작성 (script-format.md 참조)
4. 각 뉴스별 팩트체크 (최소 3개 언론사 기사 대조)
5. python scripts/batch_run.py 실행 (자동으로 공개 업로드됨)
6. memory/generated_topics.md에 오늘 다룬 주제 기록
7. 결과를 텔레그램으로 알려줘

텔레그램 전송 코드:
import urllib.request, json
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": "메시지"}).encode()
req = urllib.request.Request(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data=data, headers={"Content-Type": "application/json"})
urllib.request.urlopen(req, timeout=10)'

cd "$PROJECT_DIR"
"$CLAUDE_PATH" -p "$PROMPT" \
    --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Agent,Skill" \
    >> "$LOG_FILE" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') 데일리 뉴스 완료" >> "$LOG_FILE"
