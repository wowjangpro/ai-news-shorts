"""이미지 생성 모듈 - 멀티 소스 지원"""
import subprocess
from pathlib import Path
from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    VIDEO_WIDTH, IMAGE_AREA_TOP, IMAGE_AREA_BOTTOM,
    REPLICATE_API_TOKEN,
    MFLUX_MODEL, MFLUX_QUANTIZE, MFLUX_STEPS,
)


IMAGE_W = VIDEO_WIDTH
IMAGE_H = IMAGE_AREA_BOTTOM - IMAGE_AREA_TOP  # 1320px


class ImageGenerator:
    """씬별 배경 이미지 생성"""

    def __init__(self, source: str = "local"):
        self.source = source

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        tag: str = "",
        data: dict | None = None,
        image_url: str | None = None,
    ) -> Path:
        """이미지 생성. image_url → mflux → 인포그래픽 순으로 시도."""
        # URL이 있으면 직접 다운로드 우선
        if image_url:
            result = await self._download_image(image_url, output_path)
            if result:
                return result

        if self.source == "local":
            return await self._generate_mflux(prompt, output_path, tag, data)
        elif self.source == "replicate":
            return await self._generate_replicate(prompt, output_path, tag, data)
        elif self.source == "stock":
            return await self._generate_stock(prompt, output_path, tag, data)
        else:
            return self._generate_graphic(prompt, output_path, tag, data)

    # ── URL에서 이미지 다운로드 ──
    async def _download_image(self, url: str, output_path: Path) -> Path | None:
        """URL에서 이미지 다운로드 후 1080×1320 리사이즈"""
        import requests
        try:
            resp = requests.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
            })
            resp.raise_for_status()
            output_path.write_bytes(resp.content)

            img = Image.open(output_path).convert("RGB")
            # 비율 유지하며 크롭+리사이즈
            src_ratio = img.width / img.height
            dst_ratio = IMAGE_W / IMAGE_H
            if src_ratio > dst_ratio:
                # 원본이 더 넓음 → 좌우 크롭
                new_w = int(img.height * dst_ratio)
                left = (img.width - new_w) // 2
                img = img.crop((left, 0, left + new_w, img.height))
            else:
                # 원본이 더 높음 → 상하 크롭
                new_h = int(img.width / dst_ratio)
                top = (img.height - new_h) // 2
                img = img.crop((0, top, img.width, top + new_h))
            img = img.resize((IMAGE_W, IMAGE_H), Image.LANCZOS)
            img.save(str(output_path))
            return output_path
        except Exception as e:
            print(f"    ⚠️ 이미지 다운로드 실패 ({e}), AI 생성으로 전환")
            return None

    # ── 로컬 FLUX (mflux) ──
    async def _generate_mflux(
        self, prompt: str, output_path: Path, tag: str = "", data: dict | None = None,
    ) -> Path:
        """mflux로 로컬 이미지 생성 (Apple Silicon MLX)"""
        try:
            result = subprocess.run([
                "mflux-generate",
                "--model", MFLUX_MODEL,
                "--quantize", str(MFLUX_QUANTIZE),
                "--steps", str(MFLUX_STEPS),
                "--width", str(IMAGE_W),
                "--height", str(IMAGE_H),
                "--prompt", prompt,
                "--output", str(output_path),
            ], capture_output=True, text=True, timeout=600)

            if result.returncode != 0 or not output_path.exists():
                raise RuntimeError(result.stderr[:300] if result.stderr else "이미지 파일 미생성")

            # 크기 보정 (mflux가 다른 크기로 생성할 경우)
            img = Image.open(output_path)
            if img.size != (IMAGE_W, IMAGE_H):
                img = img.resize((IMAGE_W, IMAGE_H), Image.LANCZOS)
                img.save(str(output_path))

        except Exception as e:
            print(f"    ⚠️ mflux 실패 ({e}), 인포그래픽으로 fallback")
            return self._generate_graphic(prompt, output_path, tag, data)

        return output_path

    # ── Replicate API (FLUX) ──
    async def _generate_replicate(
        self, prompt: str, output_path: Path, tag: str = "", data: dict | None = None,
    ) -> Path:
        """Replicate FLUX로 고품질 이미지 생성"""
        try:
            import replicate
            import requests

            output = replicate.run(
                "black-forest-labs/flux-1.1-pro",
                input={
                    "prompt": prompt,
                    "width": IMAGE_W,
                    "height": IMAGE_H,
                    "num_inference_steps": 25,
                },
            )
            img_url = output[0] if isinstance(output, list) else str(output)
            resp = requests.get(img_url, timeout=30)
            output_path.write_bytes(resp.content)

        except Exception as e:
            print(f"    ⚠️ Replicate 실패 ({e}), 인포그래픽으로 fallback")
            return self._generate_graphic(prompt, output_path, tag, data)

        return output_path

    # ── 무료 스톡 이미지 (Unsplash) ──
    async def _generate_stock(
        self, prompt: str, output_path: Path, tag: str = "", data: dict | None = None,
    ) -> Path:
        """Unsplash에서 관련 이미지 검색"""
        import requests

        keywords = prompt.split(",")[0].strip()
        url = f"https://source.unsplash.com/featured/{IMAGE_W}x{IMAGE_H}/?{keywords}"
        try:
            resp = requests.get(url, timeout=15)
            output_path.write_bytes(resp.content)
        except Exception as e:
            print(f"    ⚠️ 스톡 이미지 실패 ({e}), 인포그래픽으로 fallback")
            return self._generate_graphic(prompt, output_path, tag, data)

        return output_path

    # ── 코드 기반 인포그래픽 ──
    def _generate_graphic(
        self, prompt: str, output_path: Path, tag: str = "", data: dict | None = None,
    ) -> Path:
        """Pillow로 인포그래픽 배경 생성"""
        from src.graphics.infographic import generate_infographic
        img = generate_infographic(IMAGE_W, IMAGE_H, prompt, tag, data=data)
        img.save(str(output_path))
        return output_path


if __name__ == "__main__":
    import asyncio

    gen = ImageGenerator(source="local")
    out = Path("test_image.png")
    asyncio.run(gen.generate(
        "Cinematic photo of a modern smartphone on a dark reflective surface, dramatic lighting",
        out, "테스트"
    ))
    print(f"생성 완료: {out}")
