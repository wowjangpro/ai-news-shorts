"""영상 프레임 렌더러 - 헤더 + 이미지 + 씬자막 + TTS자막"""
import os
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import *


class VideoRenderer:
    """유튜브 쇼츠 스타일 프레임 렌더링"""

    def __init__(self):
        self.fonts = {}

    def get_font(self, size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont:
        key = (size, weight)
        if key not in self.fonts:
            for entry in FONT_PATHS.get(weight, FONT_PATHS["Bold"]):
                if isinstance(entry, tuple):
                    path, index = entry
                else:
                    path, index = entry, 0
                if os.path.exists(path):
                    try:
                        self.fonts[key] = ImageFont.truetype(path, size, index=index)
                        break
                    except Exception:
                        continue
            if key not in self.fonts:
                self.fonts[key] = ImageFont.load_default()
        return self.fonts[key]

    def render_all_frames(
        self,
        script: dict,
        images: list[Path],
        total_duration: float,
        frames_dir: Path,
        seg_durations: list[float] | None = None,
        all_word_timings: list[list[dict]] | None = None,
        bg_img: Image.Image | None = None,
    ):
        """전체 프레임 렌더링 — FFmpeg 파이프 + 멀티프로세싱"""
        import subprocess
        from concurrent.futures import ProcessPoolExecutor, as_completed

        total_frames = int(total_duration * VIDEO_FPS)
        scenes = script["scenes"]

        # 씬별 타이밍 계산
        scene_timings = self._calc_timings(scenes, total_duration, seg_durations)

        # TTS 문장 타이밍 전처리 (씬별 단어 → 문장 그룹)
        sentence_timings = self._build_sentence_timings(scenes, scene_timings, all_word_timings)

        # 풀스크린 배경 이미지 준비
        if bg_img is not None:
            self._bg_img = bg_img.convert("RGB").resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
        else:
            self._bg_img = None

        # 이미지 프리로드 (RGBA 투명 인포그래픽 지원)
        loaded_images = []
        for img_path in images:
            img = Image.open(str(img_path))
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            img = img.resize((VIDEO_WIDTH, IMAGE_AREA_BOTTOM - IMAGE_AREA_TOP), Image.LANCZOS)
            loaded_images.append(img)

        # FFmpeg 파이프로 raw 프레임 직접 전송
        raw_frames_path = frames_dir / "raw_frames.rgb"
        ffmpeg_proc = subprocess.Popen([
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-pixel_format", "rgb24",
            "-video_size", f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}",
            "-framerate", str(VIDEO_FPS),
            "-i", "pipe:0",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "fast",
            str(frames_dir / "video_only.mp4"),
        ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 멀티프로세싱: 배치 단위 병렬 렌더 → 순서대로 FFmpeg 파이프 전송
        batch_size = os.cpu_count() or 4
        for batch_start in range(0, total_frames, batch_size):
            batch_end = min(batch_start + batch_size, total_frames)
            frames = {}
            for i in range(batch_start, batch_end):
                frame = self._render_frame(
                    i, total_frames, script, scenes, scene_timings,
                    loaded_images, total_duration, sentence_timings,
                )
                frames[i] = frame

            # 순서대로 FFmpeg에 전송
            for i in range(batch_start, batch_end):
                ffmpeg_proc.stdin.write(frames[i].tobytes())

            if batch_start % (batch_size * 10) == 0:
                pct = batch_start * 100 // total_frames
                print(f"  {pct}% ({batch_start}/{total_frames})")

        ffmpeg_proc.stdin.close()
        ffmpeg_proc.wait()
        print(f"  ✓ {total_frames}프레임 완료")

    def _calc_timings(self, scenes, total_duration, seg_durations=None) -> list[tuple]:
        """씬별 (시작초, 끝초) 계산 — TTS 실제 길이 기반 동기화"""
        SILENCE_GAP = 0.3
        timings = []
        t = 0.0
        for i, s in enumerate(scenes):
            if seg_durations and i < len(seg_durations):
                dur = seg_durations[i] + SILENCE_GAP
            else:
                total_dur = sum(sc.get("duration", 6) for sc in scenes)
                dur = s.get("duration", 6) / total_dur * total_duration
            timings.append((t, t + dur))
            t += dur
        return timings

    def _build_sentence_timings(self, scenes, scene_timings, all_word_timings) -> list[list[dict]]:
        """TTS 단어 타이밍을 문장 단위로 그룹핑, 절대 시간 기준"""
        result = []
        for si, scene in enumerate(scenes):
            scene_start = scene_timings[si][0]
            tts_text = scene["tts_text"]
            sentences = self._split_into_sentences(tts_text)

            # 단어 타이밍으로 씬 내 음성 시작/끝 시간 추출 → 문장별 비례 분배
            if all_word_timings and si < len(all_word_timings) and all_word_timings[si]:
                words = all_word_timings[si]
                speech_start = words[0]["offset"]
                speech_end = words[-1]["offset"] + words[-1]["duration"]
                speech_dur = speech_end - speech_start
                total_len = sum(len(s) for s in sentences) or 1
                t = speech_start
                sent_timings = []
                for sent in sentences:
                    dur = speech_dur * len(sent) / total_len
                    sent_timings.append({
                        "text": sent,
                        "start": scene_start + t,
                        "end": scene_start + t + dur,
                    })
                    t += dur
                result.append(sent_timings)
            else:
                # 타이밍 없으면 씬 시간 기준 균등 분배
                scene_start, scene_end = scene_timings[si]
                scene_dur = scene_end - scene_start
                total_len = sum(len(s) for s in sentences) or 1
                t = scene_start
                sent_timings = []
                for sent in sentences:
                    dur = scene_dur * len(sent) / total_len
                    sent_timings.append({"text": sent, "start": t, "end": t + dur})
                    t += dur
                result.append(sent_timings)
        return result

    @staticmethod
    def _split_into_sentences(text: str) -> list[str]:
        """TTS 텍스트를 문장 단위로 분리"""
        # 마침표, 물음표, 느낌표 기준 분리
        parts = re.split(r'(?<=[.?!])\s+', text.strip())
        # 너무 긴 문장은 쉼표로 추가 분리
        result = []
        for p in parts:
            if len(p) > 40:
                sub = re.split(r'(?<=,)\s+', p)
                result.extend(sub)
            else:
                result.append(p)
        return [s.strip() for s in result if s.strip()]

    def _render_frame(
        self, frame_num, total_frames, script, scenes,
        scene_timings, loaded_images, total_duration, sentence_timings,
    ) -> Image.Image:
        sec = frame_num / VIDEO_FPS

        # 풀스크린 배경: 일러스트 또는 검정
        if self._bg_img is not None:
            img = self._bg_img.copy()
        else:
            img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BLACK)
        draw = ImageDraw.Draw(img)

        # 현재 씬
        scene_idx = -1
        local_t = 0
        for i, (start, end) in enumerate(scene_timings):
            if start <= sec < end:
                scene_idx = i
                local_t = (sec - start) / (end - start)
                break

        # 전체 페이드
        fade = 1.0
        if sec < 0.2:
            fade = sec / 0.2
        elif sec > total_duration - 0.2:
            fade = max(0, (total_duration - sec) / 0.2)

        # ── 배경 위 얇은 오버레이 (가독성 보조) ──
        if self._bg_img is not None:
            overlay = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 140))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

        # ── 1. 인포그래픽 이미지 ──
        if 0 <= scene_idx < len(loaded_images):
            scene_img = loaded_images[scene_idx].copy()
            if scene_img.mode == "RGBA":
                # 투명 인포그래픽: 배경 위에 알파 합성
                region = img.crop((0, IMAGE_AREA_TOP, VIDEO_WIDTH, IMAGE_AREA_BOTTOM)).convert("RGBA")
                composited = Image.alpha_composite(region, scene_img)
                img.paste(composited.convert("RGB"), (0, IMAGE_AREA_TOP))
            else:
                # 기존 불투명 인포그래픽: 페이드 + 붙이기
                sf = 1.0
                start, end = scene_timings[scene_idx]
                if sec - start < 0.12:
                    sf = (sec - start) / 0.12
                elif end - sec < 0.08:
                    sf = (end - sec) / 0.08
                if sf < 1 or fade < 1:
                    from PIL import ImageEnhance
                    enhancer = ImageEnhance.Brightness(scene_img)
                    scene_img = enhancer.enhance(sf * fade)
                img.paste(scene_img, (0, IMAGE_AREA_TOP))

        # ── 2. 상단 헤더 ──
        self._draw_header(draw, script, scenes, scene_idx, fade)

        # ── 3. 하단 통합 배경 ──
        self._draw_lower_bg(draw)

        # ── 5. TTS 실시간 자막 (하단) ──
        if 0 <= scene_idx < len(sentence_timings):
            self._draw_tts_subtitle(draw, sentence_timings[scene_idx], sec, fade)

        # ── 6. 하단 바 ──
        if self._bg_img is None:
            draw.rectangle([0, VIDEO_HEIGHT - BOTTOM_BAR_HEIGHT, VIDEO_WIDTH, VIDEO_HEIGHT], fill=BLACK)
        f = self.get_font(22, "Regular")
        draw.text((30, VIDEO_HEIGHT - 42), "AI로 생성되어 사실과 다를 수 있습니다.", font=f, fill=(120, 120, 130))
        # 출처 표기 (우측)
        source_text = "공개된 언론 보도를 참고하여 재구성되었습니다."
        bbox = f.getbbox(source_text)
        sw = bbox[2] - bbox[0]
        draw.text((VIDEO_WIDTH - sw - 30, VIDEO_HEIGHT - 42), source_text, font=f, fill=(120, 120, 130))

        return img

    def _draw_header(self, draw, script, scenes, scene_idx, fade):
        """상단 헤더 영역"""
        # 헤더 반투명 검정 배경
        header_overlay = Image.new("RGBA", (VIDEO_WIDTH, HEADER_HEIGHT), (0, 0, 0, 128))
        base_img = draw._image
        base_region = base_img.crop((0, 0, VIDEO_WIDTH, HEADER_HEIGHT)).convert("RGBA")
        base_img.paste(Image.alpha_composite(base_region, header_overlay).convert("RGB"), (0, 0))
        draw.rectangle([0, 0, VIDEO_WIDTH, 5], fill=ACCENT_RED)

        if 0 <= scene_idx < len(scenes):
            tag = scenes[scene_idx].get("tag", "뉴스")
        else:
            tag = "뉴스"

        f_tag = self.get_font(30, "Black")
        bbox = draw.textbbox((0, 0), tag, font=f_tag)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = 10
        draw.rectangle([35, 20, 35 + tw + pad * 2, 20 + th + pad * 2], fill=ACCENT_RED)
        draw.text((35 + pad, 20 + pad - 2), tag, font=f_tag, fill=WHITE)

        title = script.get("title", "오늘의 뉴스")
        max_w = VIDEO_WIDTH - 70  # 좌우 여백 35px씩
        title_size = 96
        f_title = self.get_font(title_size, "Black")
        bbox = draw.textbbox((0, 0), title, font=f_title)
        tw = bbox[2] - bbox[0]
        # 제목이 화면을 넘으면 폰트 자동 축소
        while tw > max_w and title_size > 40:
            title_size -= 4
            f_title = self.get_font(title_size, "Black")
            bbox = draw.textbbox((0, 0), title, font=f_title)
            tw = bbox[2] - bbox[0]
        x = (VIDEO_WIDTH - tw) // 2
        self._text_outline(draw, title, x, 100, f_title, GOLD, BLACK, 4)

        f_date = self.get_font(24, "Regular")
        from datetime import datetime
        date_str = datetime.now().strftime("%Y.%m.%d")
        draw.text((35, HEADER_HEIGHT - 38), date_str, font=f_date, fill=(150, 150, 160))

    def _draw_lower_bg(self, draw):
        """인포그래픽 아래 ~ 하단까지 자연스러운 배경"""
        pass

    def _draw_subtitle(self, draw, scene, local_t, fade):
        """씬 요약 자막 — 헤더 바로 아래"""

        # 자막 텍스트
        lines = scene["subtitle"].split("\n")
        highlight_lines = set(scene.get("highlight_lines", []))
        f_sub = self.get_font(46, "Black")

        total_h = len(lines) * 65
        start_y = SCENE_SUB_TOP + (SCENE_SUB_HEIGHT - total_h) // 2

        for i, line in enumerate(lines):
            line_progress = min(1, max(0, (local_t - i * 0.1) * 5))
            if line_progress <= 0:
                continue

            y = start_y + i * 65
            offset_x = int(25 * (1 - self._ease_out(line_progress)))
            alpha = line_progress * fade

            bbox = draw.textbbox((0, 0), line, font=f_sub)
            tw = bbox[2] - bbox[0]
            x = (VIDEO_WIDTH - tw) // 2 + offset_x

            color = GOLD if i in highlight_lines else WHITE
            fill = tuple(int(v * alpha) for v in color)
            outline = tuple(int(v * alpha) for v in BLACK)
            self._text_outline(draw, line, x, y, f_sub, fill, outline, 4)

    def _wrap_text(self, text: str, font, max_width: int) -> list[str]:
        """텍스트를 max_width에 맞게 줄바꿈"""
        dummy = Image.new("RGB", (1, 1))
        d = ImageDraw.Draw(dummy)
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            bbox = d.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        return lines if lines else [text]

    def _draw_tts_subtitle(self, draw, sent_timings: list[dict], sec: float, fade: float):
        """TTS 실시간 자막 — 텔레프롬프터 스크롤 방식"""
        if not sent_timings:
            return

        f_tts = self.get_font(48, "Handwriting")
        f_active = self.get_font(54, "Handwriting")
        line_height = 68
        max_w = VIDEO_WIDTH - 80

        # 표시 영역
        area_top = TTS_SUB_TOP + 10
        area_bottom = VIDEO_HEIGHT - BOTTOM_BAR_HEIGHT - 10
        center_y = area_top + (area_bottom - area_top) // 2

        # 현재 활성 문장 인덱스
        active_idx = 0
        for i, st in enumerate(sent_timings):
            if st["start"] <= sec:
                active_idx = i

        # 각 문장을 줄바꿈 처리하여 렌더 블록 생성
        blocks = []  # [(sent_idx, wrapped_lines)]
        for i, st in enumerate(sent_timings):
            font = f_active if i == active_idx else f_tts
            wrapped = self._wrap_text(st["text"], font, max_w)
            blocks.append((i, wrapped))

        # 활성 문장까지의 총 줄 수로 스크롤 오프셋 계산
        active_line_offset = 0
        for i, (si, lines) in enumerate(blocks):
            if si < active_idx:
                active_line_offset += len(lines)
        target_y = center_y - active_line_offset * line_height

        # 렌더링
        y = target_y
        for si, wrapped in blocks:
            is_active = (si == active_idx)

            if not is_active:
                y += len(wrapped) * line_height
                continue

            for line_text in wrapped:
                bbox = draw.textbbox((0, 0), line_text, font=f_active)
                tw = bbox[2] - bbox[0]
                x = (VIDEO_WIDTH - tw) // 2
                self._text_outline(draw, line_text, x, int(y), f_active, (255, 255, 255), (0, 0, 0), 3)
                y += line_height

    @staticmethod
    def _text_outline(draw, text, x, y, f, fill, outline, w):
        draw.text((x, y), text, font=f, fill=fill, stroke_width=w, stroke_fill=outline)

    @staticmethod
    def _ease_out(t):
        return 1 - (1 - t) ** 3
