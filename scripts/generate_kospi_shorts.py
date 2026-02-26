#!/usr/bin/env python3
"""코스피 6000 돌파 뉴스 쇼츠 완전 영상 생성
인포그래픽 + TTS 나레이션 + BGM → 최종 MP4"""
import asyncio
import json
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS, VIDEO_CRF,
    IMAGE_AREA_TOP, IMAGE_AREA_BOTTOM, OUTPUT_DIR,
    TTS_VOICE, TTS_RATE,
)
from src.graphics.infographic import generate_infographic
from src.bgm_generator import BGMGenerator
from src.video_renderer import VideoRenderer
from src.video_composer import VideoComposer

# ── 이미지 크기 ──
IMAGE_W = VIDEO_WIDTH
IMAGE_H = IMAGE_AREA_BOTTOM - IMAGE_AREA_TOP  # 1320px


# ── 스크립트 데이터 ──

SCRIPT = {
    "title": "코스피 6000 돌파",
    "source": "한국거래소",
    "youtube_title": "[속보] 코스피 사상 첫 6000 돌파! 삼성전자 20만원·SK하이닉스 100만원 | 2026.02.25",
    "youtube_description": (
        "코스피가 2026년 2월 25일, 사상 처음으로 6000선을 돌파했습니다.\n"
        "삼성전자 20만원, SK하이닉스 100만원 시대가 열렸습니다.\n\n"
        "#코스피 #주식 #삼성전자 #SK하이닉스 #투자 #속보"
    ),
    "youtube_tags": ["코스피", "6000", "주식", "삼성전자", "SK하이닉스", "투자", "속보"],
    "scenes": [
        {
            "tag": "속보",
            "subtitle": "코스피 사상 첫\n6000선 돌파",
            "highlight_lines": [1],
            "tts_text": "코스피가 사상 처음으로 6000선을 돌파했습니다.",
            "image_prompt": "stock chart surge trading",
            "duration": 6,
        },
        {
            "tag": "역사적 순간",
            "subtitle": "개장과 동시에 6022.70으로 출발\n5000 돌파 후 단 한 달 만에\n1000포인트 추가 상승",
            "highlight_lines": [],
            "tts_text": "개장과 동시에 6022.70으로 출발하며, 5000 돌파 후 단 한 달 만에 1000포인트가 추가 상승했습니다.",
            "image_prompt": "stock ticker price table",
            "duration": 7,
        },
        {
            "tag": "반도체 랠리",
            "subtitle": "삼성전자 20만원 돌파\nSK하이닉스 100만원 돌파\nAI 반도체 수요 폭증이 원인",
            "highlight_lines": [0, 1],
            "tts_text": "삼성전자가 20만원을, SK하이닉스가 100만원을 돌파했습니다. AI 반도체 수요 폭증이 원인입니다.",
            "image_prompt": "semiconductor chip HBM DRAM",
            "duration": 7,
        },
        {
            "tag": "개미의 힘",
            "subtitle": "개인투자자 8291억원 순매수로\n상승을 견인",
            "highlight_lines": [],
            "tts_text": "개인투자자들이 8291억원을 순매수하며 상승을 견인했습니다.",
            "image_prompt": "investor crowd people",
            "duration": 6,
        },
        {
            "tag": "전문가 전망",
            "subtitle": "증권사들 목표치 대폭 상향\n하나증권 7870 KB증권 7500\n노무라 상반기 8000 전망",
            "highlight_lines": [1, 2],
            "tts_text": "증권사들도 목표치를 대폭 상향했습니다. 하나증권 7870, KB증권 7500, 노무라는 상반기 8000을 전망합니다.",
            "image_prompt": "forecast target prediction",
            "duration": 7,
        },
        {
            "tag": "주의사항",
            "subtitle": "시장 과열 신호도 감지\n사이드카 연이어 발동\n투자에 유의하시기 바랍니다",
            "highlight_lines": [0, 1],
            "tts_text": "다만 시장 과열 신호도 감지되고 있습니다. 사이드카가 연이어 발동되었으니, 투자에 유의하시기 바랍니다.",
            "image_prompt": "warning caution risk",
            "duration": 7,
        },
    ],
}


async def generate_tts(scenes: list[dict], work_dir: Path) -> tuple[Path, float]:
    """edge-tts로 씬별 나레이션 생성 후 합치기"""
    import edge_tts

    segments = []
    for i, scene in enumerate(scenes):
        seg_path = work_dir / f"tts_{i:02d}.mp3"
        communicate = edge_tts.Communicate(
            scene["tts_text"], TTS_VOICE, rate=TTS_RATE
        )
        await communicate.save(str(seg_path))
        segments.append(seg_path)
        dur = _get_audio_duration(seg_path)
        print(f"  ✓ 씬 {i+1}: {scene['tts_text'][:30]}... ({dur:.1f}초)")

    # 무음 생성 (씬 간 간격)
    silence_path = work_dir / "silence.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=mono",
        "-t", "1.0", "-q:a", "9", str(silence_path),
    ], capture_output=True)

    # concat 리스트
    concat_file = work_dir / "concat_tts.txt"
    with open(concat_file, "w") as f:
        for i, seg in enumerate(segments):
            f.write(f"file '{seg}'\n")
            if i < len(segments) - 1:
                f.write(f"file '{silence_path}'\n")
        f.write(f"file '{silence_path}'\n")

    narration_path = work_dir / "narration.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:a", "libmp3lame", "-q:a", "2",
        str(narration_path),
    ], capture_output=True)

    total_duration = _get_audio_duration(narration_path)
    return narration_path, total_duration


def _get_audio_duration(path: Path) -> float:
    """오디오 파일 길이(초)"""
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ], capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 30.0


async def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = Path(tempfile.mkdtemp(prefix="kospi_shorts_"))

    print("=" * 55)
    print("🎬 코스피 6000 돌파 뉴스 쇼츠 생성")
    print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    try:
        script = SCRIPT
        scenes = script["scenes"]

        # ── 1. 인포그래픽 이미지 생성 ──
        print(f"\n🖼️  1단계: 인포그래픽 이미지 생성 ({len(scenes)}개 씬)...")
        images = []
        for i, scene in enumerate(scenes):
            img_path = work_dir / f"scene_{i:02d}.png"
            img = generate_infographic(
                IMAGE_W, IMAGE_H,
                scene["image_prompt"],
                scene.get("tag", "")
            )
            img.save(str(img_path))
            images.append(img_path)
            print(f"  ✓ 씬 {i+1}: [{scene['tag']}] {img_path.name}")

        # ── 2. TTS 나레이션 생성 ──
        print("\n🎙️  2단계: TTS 나레이션 생성 (edge-tts)...")
        narration_path, total_duration = await generate_tts(scenes, work_dir)
        print(f"  📏 나레이션 총 길이: {total_duration:.1f}초")

        # ── 3. BGM 생성 ──
        print("\n🎵 3단계: BGM 생성...")
        bgm_gen = BGMGenerator()
        bgm_path = work_dir / "bgm.wav"
        bgm_gen.generate(total_duration + 3, bgm_path, "news")
        print(f"  ✓ BGM 생성 완료 ({total_duration + 3:.1f}초)")

        # ── 4. 영상 프레임 렌더링 ──
        print("\n🎬 4단계: 영상 프레임 렌더링...")
        frames_dir = work_dir / "frames"
        frames_dir.mkdir()
        renderer = VideoRenderer()
        renderer.render_all_frames(script, images, total_duration, frames_dir)

        # ── 5. 최종 합성 ──
        print("\n🔧 5단계: 최종 영상 합성...")
        composer = VideoComposer()
        output_filename = f"kospi_6000_complete_{timestamp}.mp4"
        output_path = OUTPUT_DIR / output_filename
        composer.compose(frames_dir, narration_path, bgm_path, output_path)
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  ✅ 완성: {output_path} ({size_mb:.1f}MB)")

        # 스크립트 데이터 저장
        script_path = OUTPUT_DIR / f"kospi_6000_script_{timestamp}.json"
        script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2))

        print(f"\n🎉 완료! 영상: {output_path}")
        return str(output_path)

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
