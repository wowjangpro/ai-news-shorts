"""배경음악 합성 모듈"""
import math
import struct
import wave
from pathlib import Path


class BGMGenerator:
    """뉴스 스타일 앰비언트 BGM 합성"""

    SAMPLE_RATE = 44100
    NOTES = {
        "C3": 130.81, "E3": 164.81, "F3": 174.61, "G3": 196.00,
        "A3": 220.00, "B3": 246.94,
        "C4": 261.63, "D4": 293.66, "E4": 329.63, "G4": 392.00,
        "A4": 440.00, "C5": 523.25, "D5": 587.33, "E5": 659.25,
    }

    def generate(self, duration: float, output_path: Path, style: str = "news"):
        """BGM 생성 → WAV"""
        sr = self.SAMPLE_RATE
        samples = [0.0] * int(sr * duration)

        if style == "news":
            self._add_news_bgm(samples, duration)
        else:
            self._add_ambient_bgm(samples, duration)

        # 정규화 + 페이드
        mx = max(abs(s) for s in samples) or 1
        fi, fo = int(2 * sr), int(3 * sr)
        for i in range(len(samples)):
            samples[i] = samples[i] / mx * 0.35
            if i < fi:
                samples[i] *= i / fi
            if i > len(samples) - fo:
                samples[i] *= (len(samples) - i) / fo

        with wave.open(str(output_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            for s in samples:
                s = max(-1, min(1, s))
                wf.writeframes(struct.pack("<h", int(s * 32767)))

    def _add_tone(self, samples, freq, start, dur, vol=0.08, attack=0.05):
        sr = self.SAMPLE_RATE
        si = int(start * sr)
        ei = min(si + int(dur * sr), len(samples))
        for i in range(ei - si):
            t = i / sr
            env = min(1, t / attack) * max(0, 1 - t / dur)
            val = (math.sin(2 * math.pi * freq * t) * 0.6
                   + math.sin(2 * math.pi * freq * 2 * t) * 0.2)
            samples[si + i] += val * vol * env

    def _add_news_bgm(self, samples, duration):
        """긴박한 뉴스 스타일"""
        N = self.NOTES
        # 펄스 베이스
        t = 0
        while t < duration:
            self._add_tone(samples, N["C3"], t, 0.3, 0.06)
            self._add_tone(samples, N["E3"], t + 0.5, 0.3, 0.05)
            t += 1.0

        # 상위 멜로디
        melody = ["E4", "G4", "A4", "G4", "E4", "C5", "A4"]
        t, idx = 0.5, 0
        while t < duration - 2:
            self._add_tone(samples, N[melody[idx % len(melody)]], t, 0.8, 0.05)
            t += 1.5
            idx += 1

    def _add_ambient_bgm(self, samples, duration):
        """잔잔한 앰비언트 스타일"""
        N = self.NOTES
        chords = [("A3", "C4", "E4"), ("F3", "A3", "C4"),
                  ("C3", "E4", "G4"), ("G3", "B3", "D4")]
        t = 0
        for chord in chords * int(duration // 20 + 1):
            if t >= duration:
                break
            for n in chord:
                self._add_tone(samples, N[n], t, 4, 0.03)
            t += 5

        melody = ["E5", "C5", "G4", "A4", "E5", "D5"]
        t, idx = 1, 0
        while t < duration - 2:
            self._add_tone(samples, N[melody[idx % len(melody)]], t, 2.5, 0.06)
            t += 2.5
            idx += 1


if __name__ == "__main__":
    gen = BGMGenerator()
    gen.generate(30, Path("test_bgm.wav"), "news")
    print("BGM 생성 완료")
