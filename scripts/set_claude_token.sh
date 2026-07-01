#!/bin/bash
# claude setup-token 으로 발급받은 장수명(약 1년) 토큰을 config/.env 에 안전하게 저장/검증한다.
#
# 저장 사용법:
#   1) 별도 터미널에서:  claude setup-token
#      → 브라우저 인증 후 sk-ant-oat01-... 토큰이 출력됨
#   2) 이 스크립트 실행:  bash scripts/set_claude_token.sh
#      → 토큰을 붙여넣으라는 프롬프트가 뜸(입력은 화면에 표시되지 않음)
#
# 검증 사용법:
#   bash scripts/set_claude_token.sh --verify
#      → 저장된 토큰으로 비대화 인증이 되는지 확인(토큰 값은 출력하지 않음)
#
# 참고: money-shorts 와 같은 구독이면 동일 토큰을 재사용해도 된다(새 발급 불필요).
# 토큰을 명령 인자로 넘기지 말 것(쉘 히스토리·ps 에 노출됨). stdin 으로만 받는다.

set -euo pipefail

PROJECT_DIR="/Users/jeniel/Works/ai-news-shorts"
ENV_FILE="$PROJECT_DIR/config/.env"
CLAUDE_PATH="/Users/jeniel/.local/bin/claude"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/Users/jeniel/.local/bin:$PATH"

# ── 검증 모드 ──
if [ "${1:-}" = "--verify" ]; then
    if [ ! -f "$ENV_FILE" ] || ! grep -q '^CLAUDE_CODE_OAUTH_TOKEN=' "$ENV_FILE"; then
        echo "❌ config/.env 에 CLAUDE_CODE_OAUTH_TOKEN 이 없습니다. 먼저 토큰을 저장하세요." >&2
        exit 1
    fi
    echo "🔍 저장된 토큰으로 비대화 인증 테스트 중..."
    RESULT=$(
        set -a
        # shellcheck disable=SC1090
        source "$ENV_FILE"
        set +a
        "$CLAUDE_PATH" -p "reply with exactly: AUTH_OK" --allowedTools "" 2>&1 | head -5
    )
    if echo "$RESULT" | grep -q "AUTH_OK"; then
        echo "✅ 인증 성공 — 크론 작업이 정상 동작합니다."
        exit 0
    else
        echo "❌ 인증 실패:" >&2
        echo "$RESULT" >&2
        exit 1
    fi
fi

# ── 저장 모드 ──
if [ -t 0 ]; then
    read -rsp "claude setup-token 으로 받은 토큰을 붙여넣고 Enter: " TOKEN
    echo
else
    read -r TOKEN
fi

TOKEN="${TOKEN// /}"  # 혹시 모를 공백 제거

if [ -z "$TOKEN" ]; then
    echo "❌ 토큰이 비어 있습니다. 취소." >&2
    exit 1
fi
if [[ "$TOKEN" != sk-ant-oat* ]]; then
    echo "⚠️  토큰이 'sk-ant-oat...' 형식이 아닙니다. 올바른 setup-token 토큰인지 확인하세요." >&2
    exit 1
fi

TODAY=$(date '+%Y-%m-%d')
touch "$ENV_FILE"

TMP="$(mktemp)"
grep -vE '^CLAUDE_CODE_OAUTH_TOKEN=|^CLAUDE_CODE_OAUTH_TOKEN_SET_AT=' "$ENV_FILE" > "$TMP" || true
mv "$TMP" "$ENV_FILE"
printf 'CLAUDE_CODE_OAUTH_TOKEN=%s\n' "$TOKEN" >> "$ENV_FILE"
printf 'CLAUDE_CODE_OAUTH_TOKEN_SET_AT=%s\n' "$TODAY" >> "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo "✅ config/.env 저장 완료 (발급일: $TODAY, 약 1년 유효)."
echo "   이제 검증하세요:  bash scripts/set_claude_token.sh --verify"
