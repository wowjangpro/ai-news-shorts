#!/usr/bin/env python3
"""디스코드 알림 전송 헬퍼 — 메시지를 파일에서 읽어 전송 (한글 이스케이프 회피)."""
import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID


def send(msg: str) -> None:
    data = json.dumps({"content": msg[:2000]}).encode()
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages",
        data=data,
        headers={
            "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (ai-news-shorts, 1.0)",
        },
    )
    urllib.request.urlopen(req, timeout=10)


if __name__ == "__main__":
    msg_path = sys.argv[1]
    text = Path(msg_path).read_text(encoding="utf-8")
    send(text)
    print("✅ 디스코드 전송 완료")
