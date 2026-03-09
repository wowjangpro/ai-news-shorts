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
    VIDEO_WIDTH, VIDEO_HEIGHT, IMAGE_AREA_TOP, IMAGE_AREA_BOTTOM, OUTPUT_DIR,
    TTS_VOICES, TTS_RATE,
    OLLAMA_URL, OLLAMA_IMAGE_MODEL,
)
from src.graphics.infographic import generate_infographic, get_random_card_style, set_card_style, CARD_STYLE_NAMES
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
    import random

    # 영상마다 랜덤 음성 선택
    voice = random.choice(TTS_VOICES)
    print(f"  🎙️ TTS 음성: {voice}")

    segments = []
    seg_durations = []
    all_word_timings = []  # 씬별 단어 타이밍 [{text, offset, duration}, ...]
    for i, scene in enumerate(scenes):
        seg_path = work_dir / f"tts_{i:02d}.mp3"
        meta_path = work_dir / f"tts_{i:02d}_meta.json"
        comm = edge_tts.Communicate(scene["tts_text"], voice, rate=TTS_RATE)
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

        # 1. 풀스크린 배경 일러스트 생성 (ollama, 1장)
        fullscreen_bg: Image.Image | None = None
        bg_prompt = script.get("bg_prompt")
        bg_cache_path = OUTPUT_DIR / "bg_cache.png"
        if bg_prompt:
            # 캐시된 배경이 있으면 확인 후 재사용
            if bg_cache_path.exists():
                print(f"\n🎨 1단계: 캐시된 배경 일러스트 발견")
                subprocess.run(["open", str(bg_cache_path)])
                try:
                    answer = input("  👀 캐시된 일러스트를 사용할까요? (y=사용 / n=새로 생성): ").strip().lower()
                except EOFError:
                    answer = "y"
                if answer == "y":
                    fullscreen_bg = Image.open(bg_cache_path)
                    print(f"  ✓ 캐시된 일러스트 사용")
                else:
                    bg_cache_path.unlink()
                    print(f"  🔄 새로 생성합니다...")
            if not bg_cache_path.exists():
                while True:
                    print(f"\n🎨 1단계: 배경 일러스트 생성 (ollama {OLLAMA_IMAGE_MODEL})...")
                    bg_path = work_dir / "bg_fullscreen.png"
                    try:
                        import urllib.request, io, base64
                        req_data = json.dumps({
                            "model": OLLAMA_IMAGE_MODEL,
                            "prompt": bg_prompt,
                        }).encode()
                        req = urllib.request.Request(
                            f"{OLLAMA_URL}/api/generate",
                            data=req_data,
                            headers={"Content-Type": "application/json"},
                        )
                        image_data = None
                        with urllib.request.urlopen(req, timeout=300) as resp:
                            for line in resp:
                                line = line.decode().strip()
                                if not line:
                                    continue
                                chunk = json.loads(line)
                                completed = chunk.get("completed", 0)
                                total = chunk.get("total", 0)
                                if completed and total:
                                    print(f"\r  생성 중... {completed}/{total}", end="", flush=True)
                                if chunk.get("done") and "image" in chunk:
                                    image_data = chunk["image"]
                                    print()
                                    break

                        if image_data:
                            # 1024x1024 → 1080x1920 (center crop)
                            raw_img = Image.open(io.BytesIO(base64.b64decode(image_data)))
                            scale = max(VIDEO_WIDTH / raw_img.width, VIDEO_HEIGHT / raw_img.height)
                            new_w = int(raw_img.width * scale)
                            new_h = int(raw_img.height * scale)
                            raw_img = raw_img.resize((new_w, new_h), Image.LANCZOS)
                            left = (new_w - VIDEO_WIDTH) // 2
                            top = (new_h - VIDEO_HEIGHT) // 2
                            resized = raw_img.crop((left, top, left + VIDEO_WIDTH, top + VIDEO_HEIGHT))
                            resized.save(str(bg_path))
                            print(f"  ✓ 일러스트 생성 완료 ({raw_img.width}x{raw_img.height} → {VIDEO_WIDTH}x{VIDEO_HEIGHT})")
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
                            print(f"  ⚠️ 일러스트 실패 (이미지 없음), 검정 배경 사용")
                            break
                    except Exception as e:
                        print(f"  ⚠️ 일러스트 실패 ({e.__class__.__name__}), 검정 배경 사용")
                        break

        # 인포그래픽 배경: 풀스크린에서 해당 영역 크롭
        infographic_bg = None
        if fullscreen_bg:
            infographic_bg = fullscreen_bg.crop((0, IMAGE_AREA_TOP, IMAGE_W, IMAGE_AREA_TOP + IMAGE_H))

        # 2. 인포그래픽 (데이터 오버레이)
        step = "2" if bg_prompt else "1"
        # 카드 스타일 랜덤 선택 (--card-style 인자로 고정 가능)
        card_style_arg = None
        for arg in sys.argv:
            if arg.startswith("--card-style="):
                card_style_arg = int(arg.split("=")[1])
        if card_style_arg is not None:
            set_card_style(card_style_arg)
            cs = card_style_arg
        else:
            cs = get_random_card_style()
        print(f"\n🖼️  {step}단계: 인포그래픽 ({len(scenes)}개 씬) — 카드 스타일: {CARD_STYLE_NAMES[cs]}")
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

        # 6. 미리보기 프레임 추출 + 영상 확인
        preview_path = OUTPUT_DIR / "preview_frame.png"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(output_path),
            "-vf", "select='eq(n,200)'", "-frames:v", "1", str(preview_path),
        ], capture_output=True)
        if preview_path.exists():
            subprocess.run(["open", str(preview_path)])
        subprocess.run(["open", str(output_path)])

        # 7. YouTube 업로드 확인
        try:
            answer = input("\n   👀 영상을 확인하세요. YouTube에 업로드하시겠습니까? (y=업로드 / n=건너뛰기): ").strip().lower()
        except EOFError:
            answer = "n"
        if answer == "y":
            print("   📤 YouTube 업로드 중...")
            from src.youtube_uploader import YouTubeUploader
            video_id = YouTubeUploader().authenticate().upload(output_path, script)
            print(f"  🔗 https://youtu.be/{video_id}")
        else:
            print("   ⏭️  업로드를 건너뜁니다.")

        print(f"\n🎉 완료! 영상: {output_path}")
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
