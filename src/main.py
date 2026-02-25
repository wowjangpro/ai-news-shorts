#!/usr/bin/env python3
"""
🎬 AI 뉴스 쇼츠 자동 생성 파이프라인
메인 오케스트레이터 - 전체 워크플로우를 순차 실행
"""
import argparse
import asyncio
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import *
from src.news_fetcher import NewsFetcher
from src.image_generator import ImageGenerator
from src.tts_generator import TTSGenerator
from src.bgm_generator import BGMGenerator
from src.video_renderer import VideoRenderer
from src.video_composer import VideoComposer
from src.youtube_uploader import YouTubeUploader


async def run_pipeline(
    url: str | None = None,
    image_source: str = IMAGE_SOURCE,
    upload: bool = YOUTUBE_UPLOAD,
):
    """전체 파이프라인 실행"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = Path(tempfile.mkdtemp(prefix="news_shorts_"))

    print("=" * 55)
    print("🎬 AI 뉴스 쇼츠 자동 생성기")
    print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   이미지: {image_source} | 업로드: {'✅' if upload else '❌'}")
    print("=" * 55)

    try:
        # ── 1단계: 뉴스 수집 & 요약 ──
        print("\n📰 1단계: 뉴스 수집 및 요약...")
        fetcher = NewsFetcher()
        if url:
            article = fetcher.fetch_from_url(url)
        else:
            article = fetcher.fetch_top_news()

        script = fetcher.summarize_to_script(article)
        script_path = work_dir / "script.json"
        script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2))
        print(f"  ✓ 제목: {script['title']}")
        print(f"  ✓ {len(script['scenes'])}개 씬 생성")

        # ── 2단계: 이미지 생성 ──
        print(f"\n🖼️  2단계: 이미지 생성 ({image_source})...")
        img_gen = ImageGenerator(source=image_source)
        images = []
        for i, scene in enumerate(script["scenes"]):
            img_path = work_dir / f"scene_{i:02d}.png"
            await img_gen.generate(scene["image_prompt"], img_path, scene.get("tag", ""))
            images.append(img_path)
            print(f"  ✓ 씬 {i+1}/{len(script['scenes'])}: {img_path.name}")

        # ── 3단계: TTS 생성 ──
        print("\n🎙️  3단계: TTS 음성 생성...")
        tts_gen = TTSGenerator()
        tts_segments = []
        for i, scene in enumerate(script["scenes"]):
            seg_path = work_dir / f"tts_{i:02d}.mp3"
            await tts_gen.generate(scene["tts_text"], seg_path)
            tts_segments.append(seg_path)
            print(f"  ✓ 씬 {i+1}: {scene['tts_text'][:30]}...")

        narration_path = work_dir / "narration.mp3"
        total_duration = await tts_gen.concat_with_gaps(tts_segments, narration_path)
        print(f"  📏 나레이션: {total_duration:.1f}초")

        # ── 4단계: BGM 생성 ──
        print("\n🎵 4단계: BGM 생성...")
        bgm_gen = BGMGenerator()
        bgm_path = work_dir / "bgm.wav"
        bgm_gen.generate(total_duration + 3, bgm_path)
        print(f"  ✓ BGM 생성 완료")

        # ── 5단계: 영상 프레임 렌더링 ──
        print("\n🎬 5단계: 영상 프레임 렌더링...")
        frames_dir = work_dir / "frames"
        frames_dir.mkdir()
        renderer = VideoRenderer()
        renderer.render_all_frames(script, images, total_duration, frames_dir)

        # ── 6단계: 최종 합성 ──
        print("\n🔧 6단계: 최종 영상 합성...")
        composer = VideoComposer()
        output_filename = f"news_{timestamp}.mp4"
        output_path = OUTPUT_DIR / output_filename
        composer.compose(frames_dir, narration_path, bgm_path, output_path)
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  ✅ 완성: {output_path} ({size_mb:.1f}MB)")

        # ── 7단계: YouTube 업로드 ──
        if upload:
            print("\n📤 7단계: YouTube 업로드...")
            uploader = YouTubeUploader()
            video_id = uploader.upload(
                video_path=str(output_path),
                title=script["youtube_title"],
                description=script["youtube_description"],
                tags=script["youtube_tags"],
            )
            if video_id:
                print(f"  ✅ https://youtube.com/watch?v={video_id}")
        
        print(f"\n🎉 완료! 영상: {output_path}")
        return str(output_path)

    finally:
        # 임시 파일 정리
        shutil.rmtree(work_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="AI 뉴스 쇼츠 자동 생성기")
    parser.add_argument("--url", type=str, help="뉴스 기사 URL")
    parser.add_argument(
        "--image-source",
        choices=["replicate", "local", "stock", "graphic"],
        default=IMAGE_SOURCE,
        help="이미지 생성 방식",
    )
    parser.add_argument("--upload", action="store_true", help="YouTube 업로드")
    args = parser.parse_args()

    asyncio.run(run_pipeline(
        url=args.url,
        image_source=args.image_source,
        upload=args.upload,
    ))


if __name__ == "__main__":
    main()
