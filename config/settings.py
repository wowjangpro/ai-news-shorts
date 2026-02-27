"""전역 설정"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 로드
load_dotenv(Path(__file__).parent / ".env")

# ── 경로 ──
PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "output"
CONFIG_DIR = PROJECT_ROOT / "config"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

ASSETS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 영상 설정 ──
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))
VIDEO_CRF = int(os.getenv("VIDEO_CRF", "20"))

# ── 레이아웃 ──
HEADER_HEIGHT = 250        # 상단 제목 영역
SUBTITLE_HEIGHT = 350      # 하단 자막 영역
IMAGE_AREA_TOP = HEADER_HEIGHT
IMAGE_AREA_BOTTOM = VIDEO_HEIGHT - SUBTITLE_HEIGHT

# ── 색상 ──
ACCENT_RED = (255, 60, 60)
GOLD = (255, 200, 50)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BG = (15, 15, 25)

# ── TTS ──
TTS_VOICE = os.getenv("TTS_VOICE", "ko-KR-InJoonNeural")
TTS_RATE = os.getenv("TTS_RATE", "+15%")

# ── 이미지 생성 ──
IMAGE_SOURCE = os.getenv("IMAGE_SOURCE", "graphic")  # graphic | local | replicate | stock
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")

# ── mflux (로컬 FLUX) ──
MFLUX_MODEL = os.getenv("MFLUX_MODEL", "schnell")  # schnell(빠름) | dev(고품질)
MFLUX_QUANTIZE = int(os.getenv("MFLUX_QUANTIZE", "4"))  # 3|4|5|6|8 비트 양자화
MFLUX_STEPS = int(os.getenv("MFLUX_STEPS", "4"))  # schnell: 4, dev: 20

# ── YouTube ──
YOUTUBE_UPLOAD = os.getenv("YOUTUBE_UPLOAD", "true").lower() == "true"
YOUTUBE_CATEGORY = "25"  # News & Politics
CLIENT_SECRET_PATH = CONFIG_DIR / "client_secret.json"
TOKEN_PATH = CONFIG_DIR / "youtube_token.json"

# ── Claude API (기사 요약) ──
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── 폰트 (Mac / Linux) ──
# .ttc 파일은 (경로, 인덱스) 튜플로 지정
FONT_PATHS = {
    "Black": [
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 16),   # Heavy
        "/Library/Fonts/NanumSquareRoundEB.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
    ],
    "Bold": [
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 6),    # Bold
        "/Library/Fonts/NanumSquareRoundB.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ],
    "Medium": [
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 4),    # SemiBold
        "/Library/Fonts/NanumSquareRound.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
    ],
    "Regular": [
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 0),    # Regular
        "/Library/Fonts/NanumSquareRoundR.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ],
}
