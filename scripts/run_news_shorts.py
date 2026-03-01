#!/usr/bin/env python3
"""뉴스 쇼츠 영상 생성 파이프라인 (범용)
사용법: python scripts/run_news_shorts.py [JSON 파일 경로]
기본값: scripts/news_data.json
"""
import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

from config.settings import (
    VIDEO_WIDTH, IMAGE_AREA_TOP, IMAGE_AREA_BOTTOM, OUTPUT_DIR,
    TTS_VOICE, TTS_RATE,
    MFLUX_MODEL, MFLUX_QUANTIZE, MFLUX_STEPS,
)
from src.graphics.infographic import generate_infographic
from src.bgm_generator import BGMGenerator
from src.video_renderer import VideoRenderer
from src.video_composer import VideoComposer

IMAGE_W = VIDEO_WIDTH
IMAGE_H = IMAGE_AREA_BOTTOM - IMAGE_AREA_TOP


def load_script(json_path: Path) -> dict:
    """JSON 파일에서 SCRIPT 데이터 로드"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


SILENCE_GAP = 0.3  # 씬 사이 무음 (초)

async def generate_tts(scenes: list[dict], work_dir: Path) -> tuple[Path, float, list[float], list[list[dict]]]:
    """edge-tts로 씬별 나레이션 생성 후 합치기. 씬별 TTS 길이 + 단어 타이밍 반환."""
    import edge_tts

    segments = []
    seg_durations = []
    all_word_timings = []  # 씬별 단어 타이밍 [{text, offset, duration}, ...]
    for i, scene in enumerate(scenes):
        seg_path = work_dir / f"tts_{i:02d}.mp3"
        meta_path = work_dir / f"tts_{i:02d}_meta.json"
        comm = edge_tts.Communicate(scene["tts_text"], TTS_VOICE, rate=TTS_RATE)
        await comm.save(str(seg_path), metadata_fname=str(meta_path))
        segments.append(seg_path)
        dur = _get_audio_duration(seg_path)
        seg_durations.append(dur)

        # 메타데이터에서 단어 타이밍 추출
        word_timings = []
        if meta_path.exists():
            for line in meta_path.read_text().strip().split("\n"):
                if not line:
                    continue
                m = json.loads(line)
                if m.get("type") in ("WordBoundary", "SentenceBoundary"):
                    word_timings.append({
                        "text": m["text"],
                        "offset": m["offset"] / 1e7,   # 100ns → 초
                        "duration": m["duration"] / 1e7,
                    })
        all_word_timings.append(word_timings)
        print(f"  ✓ 씬 {i+1}: {scene['tts_text'][:30]}... ({dur:.1f}초)")

    silence_path = work_dir / "silence.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-t", str(SILENCE_GAP), "-q:a", "9", str(silence_path),
    ], capture_output=True)

    concat_file = work_dir / "concat_tts.txt"
    with open(concat_file, "w") as f:
        for i, seg in enumerate(segments):
            f.write(f"file '{seg}'\n")
            if i < len(segments) - 1:
                f.write(f"file '{silence_path}'\n")
        f.write(f"file '{silence_path}'\n")

    narration_path = work_dir / "narration.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:a", "libmp3lame", "-q:a", "2", str(narration_path),
    ], capture_output=True)

    return narration_path, _get_audio_duration(narration_path), seg_durations, all_word_timings


def _get_audio_duration(path: Path) -> float:
    r = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 30.0


async def main(json_path: Path):
    script = load_script(json_path)
    scenes = script["scenes"]
    title = script.get("title", "뉴스")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = Path(tempfile.mkdtemp(prefix="news_shorts_"))

    print("=" * 55)
    print(f"🎬 뉴스 쇼츠 생성: {title}")
    print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    try:
        # 톤 설정: 최상위 tone을 각 씬의 infographic_data에 전파
        tone = script.get("tone", "society")
        for sc in scenes:
            info_data = sc.get("infographic_data")
            if info_data and "tone" not in info_data:
                info_data["tone"] = tone

        # 1. 풀스크린 배경 일러스트 생성 (mflux, 1장)
        fullscreen_bg: Image.Image | None = None
        bg_prompt = script.get("bg_prompt")
        bg_cache_path = OUTPUT_DIR / "bg_cache.png"
        if bg_prompt:
            from config.settings import VIDEO_HEIGHT
            # 캐시된 배경이 있으면 재사용
            if bg_cache_path.exists():
                fullscreen_bg = Image.open(bg_cache_path)
                print(f"\n🎨 1단계: 캐시된 배경 일러스트 사용")
            else:
                while True:
                    print(f"\n🎨 1단계: 배경 일러스트 생성 (mflux, 1080x1920)...")
                    bg_path = work_dir / "bg_fullscreen.png"
                    try:
                        result = subprocess.run([
                            "mflux-generate",
                            "--model", MFLUX_MODEL,
                            "--quantize", str(MFLUX_QUANTIZE),
                            "--steps", str(MFLUX_STEPS),
                            "--width", str(IMAGE_W),
                            "--height", str(VIDEO_HEIGHT),
                            "--prompt", bg_prompt,
                            "--output", str(bg_path),
                        ], capture_output=True, text=True, timeout=600)
                        if result.returncode == 0 and bg_path.exists():
                            print(f"  ✓ 일러스트 생성 완료 — 미리보기...")
                            subprocess.run(["open", str(bg_path)])
                            try:
                                answer = input("  👀 일러스트가 괜찮습니까? (y=사용 / n=재생성): ").strip().lower()
                            except EOFError:
                                answer = "y"
                            if answer == "y":
                                fullscreen_bg = Image.open(bg_path)
                                fullscreen_bg.save(str(bg_cache_path))
                                print(f"  ✓ 캐시 저장 완료")
                                break
                            else:
                                print(f"  🔄 재생성합니다...")
                                bg_path.unlink(missing_ok=True)
                                continue
                        else:
                            print(f"  ⚠️ 일러스트 실패, 검정 배경 사용")
                            break
                    except (subprocess.TimeoutExpired, Exception) as e:
                        print(f"  ⚠️ 일러스트 실패 ({e.__class__.__name__}), 검정 배경 사용")
                        break

        # 인포그래픽 배경: 풀스크린에서 해당 영역 크롭
        infographic_bg = None
        if fullscreen_bg:
            infographic_bg = fullscreen_bg.crop((0, IMAGE_AREA_TOP, IMAGE_W, IMAGE_AREA_TOP + IMAGE_H))

        # 2. 인포그래픽 (데이터 오버레이)
        step = "2" if bg_prompt else "1"
        print(f"\n🖼️  {step}단계: 인포그래픽 ({len(scenes)}개 씬)...")
        images = []
        for i, sc in enumerate(scenes):
            p = work_dir / f"scene_{i:02d}.png"
            generate_infographic(
                IMAGE_W, IMAGE_H,
                sc.get("image_prompt", ""),
                sc.get("tag", ""),
                data=sc.get("infographic_data"),
                bg_img=infographic_bg,
            ).save(str(p))
            images.append(p)
            print(f"  ✓ 씬 {i+1}: [{sc.get('tag','')}]")

        # 2. TTS
        print("\n🎙️  2단계: TTS 나레이션...")
        narration_path, total_duration, seg_durations, all_word_timings = await generate_tts(scenes, work_dir)
        print(f"  📏 총 길이: {total_duration:.1f}초")

        # 3. BGM
        print("\n🎵 3단계: BGM...")
        bgm_path = work_dir / "bgm.wav"
        BGMGenerator().generate(total_duration + 3, bgm_path, "news")

        # 4. 프레임 렌더링
        print("\n🎬 4단계: 프레임 렌더링...")
        frames_dir = work_dir / "frames"
        frames_dir.mkdir()
        VideoRenderer().render_all_frames(script, images, total_duration, frames_dir, seg_durations, all_word_timings, bg_img=fullscreen_bg)

        # 5. 합성
        print("\n🔧 5단계: 최종 합성...")
        # 파일명: 제목에서 안전한 문자만 추출
        safe_title = "".join(c for c in title if c.isalnum() or c in "_ ")[:20].strip().replace(" ", "_")
        output_path = OUTPUT_DIR / f"{safe_title}_{timestamp}.mp4"
        VideoComposer().compose(frames_dir, narration_path, bgm_path, output_path)
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  ✅ 완성: {output_path} ({size_mb:.1f}MB)")

        # 사용된 스크립트 저장
        script_out = OUTPUT_DIR / f"{safe_title}_script_{timestamp}.json"
        script_out.write_text(json.dumps(script, ensure_ascii=False, indent=2))

        # 6. 미리보기
        subprocess.run(["open", str(output_path)])
        print(f"\n🎉 완료! 영상: {output_path}")
        print(f"   업로드: python scripts/upload.py {output_path}")
        return str(output_path)

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    data_path = Path(args[0]) if args else Path(__file__).parent / "news_data.json"
    if not data_path.exists():
        print(f"❌ JSON 파일을 찾을 수 없습니다: {data_path}")
        sys.exit(1)
    asyncio.run(main(data_path))
