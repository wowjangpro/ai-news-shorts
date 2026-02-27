"""FFmpeg 영상 합성 모듈"""
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import VIDEO_FPS, VIDEO_CRF


class VideoComposer:
    """프레임 + 오디오 → 최종 MP4"""

    def compose(
        self,
        frames_dir: Path,
        narration_path: Path,
        bgm_path: Path,
        output_path: Path,
        narration_vol: float = 3.0,
        bgm_vol: float = 0.2,
    ):
        """최종 영상 합성"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mixed_audio = frames_dir.parent / "mixed_audio.wav"

        # 1. 오디오 믹싱 (나레이션 + BGM)
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(narration_path),
            "-i", str(bgm_path),
            "-filter_complex",
            f"[0:a]volume={narration_vol}[voice];"
            f"[1:a]volume={bgm_vol}[bgm];"
            "[voice][bgm]amix=inputs=2:duration=longest[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            str(mixed_audio),
        ], capture_output=True)

        # 2. 영상 + 오디오 합성
        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(VIDEO_FPS),
            "-i", str(frames_dir / "frame_%05d.png"),
            "-i", str(mixed_audio),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", str(VIDEO_CRF),
            "-preset", "medium",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path),
        ], capture_output=True)

    def compose_simple(self, frames_dir: Path, bgm_path: Path, output_path: Path):
        """TTS 없이 BGM만으로 합성"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(VIDEO_FPS),
            "-i", str(frames_dir / "frame_%05d.png"),
            "-i", str(bgm_path),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", str(VIDEO_CRF),
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            str(output_path),
        ], capture_output=True)
