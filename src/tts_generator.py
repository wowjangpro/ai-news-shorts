"""TTS 음성 생성 모듈 (edge-tts)"""
import asyncio
import subprocess
from pathlib import Path

import edge_tts

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import TTS_VOICE, TTS_RATE


class TTSGenerator:
    """한국어 TTS 음성 생성"""

    def __init__(self, voice: str = TTS_VOICE, rate: str = TTS_RATE):
        self.voice = voice
        self.rate = rate

    async def generate(self, text: str, output_path: Path) -> float:
        """텍스트 → MP3 음성 파일, 길이(초) 반환"""
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        await communicate.save(str(output_path))
        return self._get_duration(output_path)

    async def concat_with_gaps(
        self, segments: list[Path], output_path: Path, gap_sec: float = 1.0
    ) -> float:
        """여러 TTS 세그먼트를 간격 포함하여 하나로 합치기"""
        # 무음 파일 생성
        silence_path = output_path.parent / "silence.mp3"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono",
            "-t", str(gap_sec), "-q:a", "9", str(silence_path),
        ], capture_output=True)

        # concat 리스트
        concat_file = output_path.parent / "concat_tts.txt"
        with open(concat_file, "w") as f:
            for i, seg in enumerate(segments):
                f.write(f"file '{seg}'\n")
                if i < len(segments) - 1:
                    f.write(f"file '{silence_path}'\n")
            # 마지막에 여유 무음
            f.write(f"file '{silence_path}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c:a", "libmp3lame", "-q:a", "2",
            str(output_path),
        ], capture_output=True)

        return self._get_duration(output_path)

    @staticmethod
    def _get_duration(path: Path) -> float:
        """오디오 파일 길이(초) 조회"""
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ], capture_output=True, text=True)
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 30.0  # fallback


if __name__ == "__main__":
    async def test():
        tts = TTSGenerator()
        out = Path("test_tts.mp3")
        dur = await tts.generate("코스피가 오늘 사상 처음으로 6000선을 돌파했습니다.", out)
        print(f"길이: {dur:.1f}초, 파일: {out}")

    asyncio.run(test())
