#!/usr/bin/env python3
"""텔레그램 봇 데몬 — 메시지 수신 시 Claude Code 비대화 모드로 영상 생성"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

PROJECT_DIR = Path(__file__).parent.parent
CLAUDE_PATH = "/Users/jeniel/.local/bin/claude"
POLL_INTERVAL = 5  # 초

# 세션 유지: 직전 대화를 이어가기 위한 플래그
_continue_session = False


def send_telegram(text: str):
    """텔레그램 메시지 전송"""
    data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data=data, headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        _flush(f"⚠️ 텔레그램 전송 실패: {e}")


def get_updates(offset: int = 0) -> list:
    """텔레그램 업데이트 가져오기 (long polling)"""
    url = (
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        f"?offset={offset}&timeout=30"
    )
    try:
        resp = urllib.request.urlopen(url, timeout=35)
        result = json.loads(resp.read())
        if result.get("ok"):
            return result.get("result", [])
    except Exception as e:
        _flush(f"⚠️ 폴링 실패: {e}")
    return []


def run_claude(prompt: str, continue_session: bool = False) -> str:
    """Claude Code 비대화 모드 실행

    Args:
        prompt: 실행할 프롬프트
        continue_session: True면 직전 대화 세션을 이어감
    """
    cmd = [
        CLAUDE_PATH, "-p", prompt,
        "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Agent,Skill",
    ]
    if continue_session:
        cmd.append("--continue")

    mode = "이어서" if continue_session else "새 세션"
    _flush(f"🤖 Claude 실행 ({mode}): {prompt[:50]}...")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(PROJECT_DIR), timeout=3600,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            error = result.stderr.strip()
            return f"❌ Claude 실행 실패\n{error[:500]}"
        return output[-1000:] if len(output) > 1000 else output
    except subprocess.TimeoutExpired:
        return "❌ Claude 실행 시간 초과 (60분)"
    except Exception as e:
        return f"❌ Claude 실행 오류: {e}"


def handle_message(text: str, chat_id: str):
    """메시지 처리"""
    global _continue_session

    # 본인 채팅만 허용
    if str(chat_id) != str(TELEGRAM_CHAT_ID):
        _flush(f"⛔ 허용되지 않은 chat_id: {chat_id}")
        return

    text = text.strip()
    if not text:
        return

    # 명령어 처리
    if text == "/status":
        mode = "이어서 대화 중" if _continue_session else "새 세션 대기"
        send_telegram(f"✅ 봇 정상 작동 중\n📌 세션: {mode}")
        return

    if text == "/new":
        _continue_session = False
        send_telegram("🆕 새 세션으로 전환됨\n다음 메시지부터 새 대화가 시작됩니다.")
        return

    if text == "/help":
        send_telegram(
            "📋 사용법\n"
            "• 메시지 입력 → Claude가 요청 수행\n"
            "• 이어서 대화하면 이전 맥락 유지\n"
            "• /new — 새 세션 시작\n"
            "• /status — 봇 상태 확인\n"
            "• /help — 도움말"
        )
        return

    # 사용자 요청 전달
    send_telegram(f"🤖 요청 접수\n{text}")

    prompt = (
        f"사용자 요청: {text}\n\n"
        "위 요청을 정확히 수행해줘. 요청 내용에 따라 판단해.\n"
        "- 검색만 요청하면 검색 결과만 텔레그램으로 알려줘\n"
        "- 영상 생성을 요청하면 생성해줘\n"
        "- 업로드를 요청하면 업로드해줘 (공개/비공개 지정 없으면 기본 비공개)\n"
        "- 결과는 텔레그램으로 알려줘\n\n"
        "텔레그램 전송 코드:\n"
        "import urllib.request, json\n"
        "from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID\n"
        "data = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': '메시지'}).encode()\n"
        "req = urllib.request.Request(f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage', "
        "data=data, headers={'Content-Type': 'application/json'})\n"
        "urllib.request.urlopen(req, timeout=10)"
    )

    result = run_claude(prompt, continue_session=_continue_session)

    # 첫 실행 이후부터는 세션 이어가기
    _continue_session = True

    # Claude 실행 결과도 텔레그램으로 전송
    if result.startswith("❌"):
        send_telegram(result)
    else:
        send_telegram(f"✅ 작업 완료\n{result[-500:]}")


def _flush(*args, **kwargs):
    """즉시 출력 (버퍼링 방지)"""
    print(*args, **kwargs, flush=True)


def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        _flush("❌ TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID를 config/.env에 설정하세요")
        sys.exit(1)

    _flush("=" * 50)
    _flush("🤖 텔레그램 봇 데몬 시작")
    _flush(f"   Chat ID: {TELEGRAM_CHAT_ID}")
    _flush(f"   프로젝트: {PROJECT_DIR}")
    _flush("=" * 50)

    send_telegram("🤖 뉴스 쇼츠 봇 시작됨\n/new로 새 세션, /help로 도움말")

    offset = 0
    # 기존 미처리 메시지 건너뛰기
    updates = get_updates(offset)
    if updates:
        offset = updates[-1]["update_id"] + 1
        _flush(f"📨 기존 메시지 {len(updates)}건 건너뜀")

    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id", "")
                if text:
                    _flush(f"📨 수신: {text}")
                    handle_message(text, chat_id)
        except KeyboardInterrupt:
            _flush("\n👋 봇 종료")
            send_telegram("🛑 뉴스 쇼츠 봇 종료됨")
            break
        except Exception as e:
            _flush(f"⚠️ 오류: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
