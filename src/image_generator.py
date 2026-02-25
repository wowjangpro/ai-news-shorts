"""이미지 생성 모듈 - 멀티 소스 지원"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math
import random

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    VIDEO_WIDTH, IMAGE_AREA_TOP, IMAGE_AREA_BOTTOM,
    REPLICATE_API_TOKEN, DARK_BG,
)


IMAGE_W = VIDEO_WIDTH
IMAGE_H = IMAGE_AREA_BOTTOM - IMAGE_AREA_TOP  # 1320px


class ImageGenerator:
    """씬별 배경 이미지 생성"""

    def __init__(self, source: str = "graphic"):
        self.source = source

    async def generate(self, prompt: str, output_path: Path, tag: str = "") -> Path:
        """프롬프트로 이미지 생성"""
        if self.source == "replicate":
            return await self._generate_replicate(prompt, output_path)
        elif self.source == "stock":
            return await self._generate_stock(prompt, output_path)
        elif self.source == "local":
            return await self._generate_local_sd(prompt, output_path)
        else:
            return self._generate_graphic(prompt, output_path, tag)

    # ── Replicate API (FLUX) ──
    async def _generate_replicate(self, prompt: str, output_path: Path) -> Path:
        """Replicate FLUX로 고품질 이미지 생성"""
        try:
            import replicate

            output = replicate.run(
                "black-forest-labs/flux-1.1-pro",
                input={
                    "prompt": prompt,
                    "width": IMAGE_W,
                    "height": IMAGE_H,
                    "num_inference_steps": 25,
                },
            )

            # URL에서 이미지 다운로드
            import requests
            img_url = output[0] if isinstance(output, list) else str(output)
            resp = requests.get(img_url, timeout=30)
            output_path.write_bytes(resp.content)

        except Exception as e:
            print(f"    ⚠️ Replicate 실패 ({e}), 인포그래픽으로 fallback")
            self._generate_graphic(prompt, output_path)

        return output_path

    # ── 무료 스톡 이미지 (Unsplash) ──
    async def _generate_stock(self, prompt: str, output_path: Path) -> Path:
        """Unsplash에서 관련 이미지 검색"""
        import requests

        # 프롬프트에서 영어 키워드 추출
        keywords = prompt.split(",")[0].strip()
        url = f"https://source.unsplash.com/featured/{IMAGE_W}x{IMAGE_H}/?{keywords}"

        try:
            resp = requests.get(url, timeout=15)
            output_path.write_bytes(resp.content)
        except Exception as e:
            print(f"    ⚠️ 스톡 이미지 실패 ({e}), 인포그래픽으로 fallback")
            self._generate_graphic(prompt, output_path)

        return output_path

    # ── 로컬 Stable Diffusion (MLX) ──
    async def _generate_local_sd(self, prompt: str, output_path: Path) -> Path:
        """로컬 Stable Diffusion (Apple MLX 백엔드)"""
        try:
            # mflux 또는 diffusers + MPS 사용
            # pip install mflux
            import subprocess
            result = subprocess.run([
                "mflux-generate",
                "--prompt", prompt,
                "--width", str(IMAGE_W),
                "--height", str(IMAGE_H),
                "--steps", "20",
                "--output", str(output_path),
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise RuntimeError(result.stderr)

        except Exception as e:
            print(f"    ⚠️ 로컬 SD 실패 ({e}), 인포그래픽으로 fallback")
            self._generate_graphic(prompt, output_path)

        return output_path

    # ── 코드 기반 인포그래픽 ──
    def _generate_graphic(self, prompt: str, output_path: Path, tag: str = "") -> Path:
        """Pillow로 인포그래픽 배경 생성"""
        from src.graphics.infographic import generate_infographic
        img = generate_infographic(IMAGE_W, IMAGE_H, prompt, tag)
        img.save(str(output_path))
        return output_path


if __name__ == "__main__":
    import asyncio

    gen = ImageGenerator(source="graphic")
    out = Path("test_image.png")
    asyncio.run(gen.generate("Realistic photo of stock market trading floor", out, "속보"))
    print(f"생성 완료: {out}")
