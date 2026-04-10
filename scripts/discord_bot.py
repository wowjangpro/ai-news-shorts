#!/usr/bin/env python3
"""디스코드 봇 데몬 — 메시지 수신 시 Claude Code 비대화 모드로 영상 생성"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import discord
from config.settings import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID

PROJECT_DIR = Path(__file__).parent.parent
CLAUDE_PATH = "/Users/jeniel/.local/bin/claude"

# 세션 유지: 직전 대화를 이어가기 위한 플래그
_continue_session = False

# 디스코드 봇 설정
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def send_discord(text: str, channel=None):
    """디스코드 메시지 전송 (2000자 제한 분할)"""
    if channel is None:
        try:
            channel = await client.fetch_channel(int(DISCORD_CHANNEL_ID))
        except Exception:
            pass
    if not channel:
        _flush("⚠️ 디스코드 채널을 찾을 수 없음")
        return
    # 디스코드 메시지 2000자 제한
    while text:
        chunk, text = text[:2000], text[2000:]
        await channel.send(chunk)


def run_claude(prompt: str, continue_session: bool = False) -> str:
    """Claude Code 비대화 모드 실행"""
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
        return output[-1500:] if len(output) > 1500 else output
    except subprocess.TimeoutExpired:
        return "❌ Claude 실행 시간 초과 (60분)"
    except Exception as e:
        return f"❌ Claude 실행 오류: {e}"


@client.event
async def on_ready():
    _flush("=" * 50)
    _flush(f"🤖 디스코드 봇 시작: {client.user}")
    _flush(f"   채널 ID: {DISCORD_CHANNEL_ID}")
    _flush(f"   프로젝트: {PROJECT_DIR}")
    _flush("=" * 50)

    try:
        channel = await client.fetch_channel(int(DISCORD_CHANNEL_ID))
        await channel.send("🤖 뉴스 쇼츠 봇 시작됨\n`/new`로 새 세션, `/help`로 도움말")
    except Exception as e:
        _flush(f"⚠️ 시작 메시지 전송 실패: {e}")


@client.event
async def on_message(message: discord.Message):
    global _continue_session

    # 봇 자신의 메시지 무시
    if message.author == client.user:
        return

    # 지정된 채널에서만 반응
    if str(message.channel.id) != str(DISCORD_CHANNEL_ID):
        return

    text = message.content.strip()
    if not text:
        return

    _flush(f"📨 수신: {text}")
    channel = message.channel

    # 명령어 처리
    if text == "/status":
        mode = "이어서 대화 중" if _continue_session else "새 세션 대기"
        await channel.send(f"✅ 봇 정상 작동 중\n📌 세션: {mode}")
        return

    if text == "/new":
        _continue_session = False
        await channel.send("🆕 새 세션으로 전환됨\n다음 메시지부터 새 대화가 시작됩니다.")
        return

    if text == "/help":
        await channel.send(
            "📋 **사용법**\n"
            "• 메시지 입력 → Claude가 요청 수행\n"
            "• 이어서 대화하면 이전 맥락 유지\n"
            "• `/new` — 새 세션 시작\n"
            "• `/status` — 봇 상태 확인\n"
            "• `/help` — 도움말"
        )
        return

    # 사용자 요청 전달
    await channel.send(f"🤖 요청 접수\n{text}")

    prompt = (
        f"사용자 요청: {text}\n\n"
        "위 요청을 정확히 수행해줘. 요청 내용에 따라 판단해.\n"
        "- 검색만 요청하면 검색 결과만 디스코드로 알려줘\n"
        "- 영상 생성을 요청하면 생성해줘\n"
        "- 업로드를 요청하면 업로드해줘 (공개/비공개 지정 없으면 기본 비공개)\n"
        "- 결과는 디스코드로 알려줘\n\n"
        "디스코드 전송 코드:\n"
        "import urllib.request, json\n"
        "from config.settings import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID\n"
        "data = json.dumps({'content': '메시지'}).encode()\n"
        "req = urllib.request.Request(\n"
        "    f'https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages',\n"
        "    data=data,\n"
        "    headers={'Authorization': f'Bot {DISCORD_BOT_TOKEN}', 'Content-Type': 'application/json',\n"
        "             'User-Agent': 'DiscordBot (ai-news-shorts, 1.0)'},\n"
        ")\n"
        "urllib.request.urlopen(req, timeout=10)"
    )

    result = run_claude(prompt, continue_session=_continue_session)

    # 첫 실행 이후부터는 세션 이어가기
    _continue_session = True

    # Claude 실행 결과도 디스코드로 전송
    if result.startswith("❌"):
        await send_discord(result, channel)
    else:
        await send_discord(f"✅ 작업 완료\n{result[-1500:]}", channel)


def _flush(*args, **kwargs):
    """즉시 출력 (버퍼링 방지)"""
    print(*args, **kwargs, flush=True)


def _check_duplicate():
    """이미 실행 중인 디스코드 봇이 있으면 종료"""
    import os
    my_pid = os.getpid()
    try:
        result = subprocess.run(
            ["pgrep", "-f", "discord_bot.py"],
            capture_output=True, text=True,
        )
        pids = [int(p) for p in result.stdout.strip().split("\n") if p.strip()]
        other_pids = [p for p in pids if p != my_pid]
        if other_pids:
            _flush(f"⚠️ 디스코드 봇이 이미 실행 중 (PID: {other_pids}). 종료합니다.")
            sys.exit(0)
    except Exception:
        pass


def main():
    _check_duplicate()

    if not DISCORD_BOT_TOKEN or not DISCORD_CHANNEL_ID:
        _flush("❌ DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID를 config/.env에 설정하세요")
        sys.exit(1)

    client.run(DISCORD_BOT_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
