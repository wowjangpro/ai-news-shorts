#!/usr/bin/env python3
"""10개 뉴스 영상 배치 생성 + 공개 업로드"""
import asyncio
import builtins
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# 모든 input() 프롬프트에 자동 "y" 응답
builtins.input = lambda *args: "y"

from config.settings import OUTPUT_DIR, DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID


def send_discord(msg: str):
    """디스코드 메시지 전송"""
    if not DISCORD_BOT_TOKEN or not DISCORD_CHANNEL_ID:
        return
    try:
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
    except Exception as e:
        print(f"  ⚠️ 디스코드 전송 실패: {e}")


async def batch_run():
    json_files = sorted(Path(__file__).parent.glob("batch_*.json"))
    total = len(json_files)
    print(f"\n🚀 배치 실행 시작: {total}개 영상")
    send_discord(f"🚀 배치 생성 시작: {total}개 영상")

    results = []

    for i, jf in enumerate(json_files):
        num = i + 1
        script_data = json.loads(jf.read_text(encoding="utf-8"))
        title = script_data.get("title", "뉴스")

        print(f"\n{'='*55}")
        print(f"📰 [{num}/{total}] {title}")
        print(f"{'='*55}")
        send_discord(f"📰 [{num}/{total}] {title} 생성 시작...")

        # 배경 캐시 삭제 (영상마다 새 일러스트)
        bg_cache = OUTPUT_DIR / "bg_cache.png"
        bg_cache.unlink(missing_ok=True)

        try:
            # 파이프라인 실행 (main 함수 직접 호출)
            from scripts.run_news_shorts import main
            output_path = await main(jf)
            results.append({"num": num, "title": title, "status": "✅", "path": output_path})
        except Exception as e:
            print(f"  ❌ 실패: {e}")
            send_discord(f"❌ [{num}/{total}] {title} 실패: {e}")
            results.append({"num": num, "title": title, "status": "❌", "error": str(e)})

    # 최종 결과 요약
    success = sum(1 for r in results if r["status"] == "✅")
    summary = f"🎬 배치 완료: {success}/{total}개 성공\n\n"
    for r in results:
        summary += f"{r['status']} {r['num']}. {r['title']}\n"

    print(f"\n{summary}")
    send_discord(summary)


if __name__ == "__main__":
    asyncio.run(batch_run())
