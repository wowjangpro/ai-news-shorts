"""영상 프레임 렌더러 - 헤더 + 이미지 + 자막"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

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
                # .ttc 파일은 (경로, 인덱스) 튜플
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
    ):
        """전체 프레임 렌더링"""
        total_frames = int(total_duration * VIDEO_FPS)
        scenes = script["scenes"]

        # 씬별 타이밍 계산
        scene_timings = self._calc_timings(scenes, total_duration)

        # 이미지 프리로드
        loaded_images = []
        for img_path in images:
            img = Image.open(str(img_path)).convert("RGB")
            img = img.resize((VIDEO_WIDTH, IMAGE_AREA_BOTTOM - IMAGE_AREA_TOP), Image.LANCZOS)
            loaded_images.append(img)

        for i in range(total_frames):
            if i % 150 == 0:
                pct = i * 100 // total_frames
                print(f"  {pct}% ({i}/{total_frames})")

            frame = self._render_frame(
                i, total_frames, script, scenes, scene_timings,
                loaded_images, total_duration,
            )
            frame.save(str(frames_dir / f"frame_{i:05d}.png"))

        print(f"  ✓ {total_frames}프레임 완료")

    def _calc_timings(self, scenes: list[dict], total_duration: float) -> list[tuple]:
        """씬별 (시작초, 끝초) 계산"""
        # 각 씬 duration 비율로 분배
        total_dur = sum(s.get("duration", 6) for s in scenes)
        timings = []
        t = 0.5  # 시작 여유
        for s in scenes:
            dur = s.get("duration", 6) / total_dur * (total_duration - 2)
            timings.append((t, t + dur))
            t += dur
        return timings

    def _render_frame(
        self, frame_num, total_frames, script, scenes,
        scene_timings, loaded_images, total_duration,
    ) -> Image.Image:
        sec = frame_num / VIDEO_FPS
        img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), DARK_BG)
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
        if sec < 1:
            fade = sec
        elif sec > total_duration - 1.5:
            fade = max(0, (total_duration - sec) / 1.5)

        # ── 1. 중앙 이미지 ──
        if 0 <= scene_idx < len(loaded_images):
            bg_img = loaded_images[scene_idx].copy()

            # 씬 전환 페이드
            sf = 1.0
            start, end = scene_timings[scene_idx]
            if sec - start < 0.4:
                sf = (sec - start) / 0.4
            elif end - sec < 0.3:
                sf = (end - sec) / 0.3

            # 밝기 조절
            if sf < 1 or fade < 1:
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Brightness(bg_img)
                bg_img = enhancer.enhance(sf * fade)

            img.paste(bg_img, (0, IMAGE_AREA_TOP))

        # ── 2. 상단 헤더 ──
        self._draw_header(draw, script, scenes, scene_idx, fade)

        # ── 3. 하단 자막 ──
        if 0 <= scene_idx < len(scenes):
            self._draw_subtitle(draw, scenes[scene_idx], local_t, fade)

        # ── 4. 하단 바 ──
        draw.rectangle([0, VIDEO_HEIGHT - 55, VIDEO_WIDTH, VIDEO_HEIGHT], fill=BLACK)
        f = self.get_font(22, "Regular")
        tags = script.get("youtube_tags", ["뉴스", "속보"])
        tag_str = " ".join(f"#{t}" for t in tags[:4])
        draw.text((30, VIDEO_HEIGHT - 42), f"📰 AI 뉴스 브리핑 | {tag_str}", font=f, fill=(120, 120, 130))

        return img

    def _draw_header(self, draw, script, scenes, scene_idx, fade):
        """상단 헤더 영역"""
        draw.rectangle([0, 0, VIDEO_WIDTH, HEADER_HEIGHT], fill=BLACK)

        # 빨간 악센트 바
        draw.rectangle([0, 0, VIDEO_WIDTH, 5], fill=ACCENT_RED)

        # 태그
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

        # 메인 제목
        f_title = self.get_font(64, "Black")
        title = script.get("title", "오늘의 뉴스")
        bbox = draw.textbbox((0, 0), title, font=f_title)
        tw = bbox[2] - bbox[0]
        x = (VIDEO_WIDTH - tw) // 2
        self._text_outline(draw, title, x, 100, f_title, WHITE, BLACK, 4)

        # 날짜
        f_date = self.get_font(24, "Regular")
        from datetime import datetime
        date_str = datetime.now().strftime("%Y.%m.%d")
        draw.text((35, HEADER_HEIGHT - 38), date_str, font=f_date, fill=(150, 150, 160))

    def _draw_subtitle(self, draw, scene, local_t, fade):
        """하단 자막 영역 — 기본 WHITE, highlight_lines만 GOLD"""
        # 반투명 배경
        sub_top = VIDEO_HEIGHT - SUBTITLE_HEIGHT
        for y in range(sub_top, sub_top + 80):
            alpha = (y - sub_top) / 80
            c = int(12 * alpha)
            draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(c, c, c))
        draw.rectangle([0, sub_top + 80, VIDEO_WIDTH, VIDEO_HEIGHT - 55], fill=(10, 10, 15))

        # 자막 텍스트
        lines = scene["subtitle"].split("\n")
        highlight_lines = set(scene.get("highlight_lines", []))
        f_sub = self.get_font(46, "Black")

        total_h = len(lines) * 65
        start_y = sub_top + 90 + (200 - total_h) // 2

        for i, line in enumerate(lines):
            # 줄별 등장 애니메이션
            line_progress = min(1, max(0, (local_t - i * 0.1) * 5))
            if line_progress <= 0:
                continue

            y = start_y + i * 65
            offset_x = int(25 * (1 - self._ease_out(line_progress)))
            alpha = line_progress * fade

            bbox = draw.textbbox((0, 0), line, font=f_sub)
            tw = bbox[2] - bbox[0]
            x = (VIDEO_WIDTH - tw) // 2 + offset_x

            # 하이라이트 줄은 GOLD, 나머지는 WHITE
            color = GOLD if i in highlight_lines else WHITE
            fill = tuple(int(v * alpha) for v in color)
            outline = tuple(int(v * alpha) for v in BLACK)
            self._text_outline(draw, line, x, y, f_sub, fill, outline, 4)

    @staticmethod
    def _text_outline(draw, text, x, y, f, fill, outline, w):
        for dx in range(-w, w + 1):
            for dy in range(-w, w + 1):
                if dx * dx + dy * dy <= w * w:
                    draw.text((x + dx, y + dy), text, font=f, fill=outline)
        draw.text((x, y), text, font=f, fill=fill)

    @staticmethod
    def _ease_out(t):
        return 1 - (1 - t) ** 3
