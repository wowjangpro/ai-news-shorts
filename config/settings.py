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
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "24"))
VIDEO_CRF = int(os.getenv("VIDEO_CRF", "20"))

# ── 레이아웃 ──
HEADER_HEIGHT = 250        # 상단 제목 영역 (0~250)
IMAGE_AREA_TOP = HEADER_HEIGHT  # 인포그래픽 상단 (250, 요약자막 제거)
IMAGE_AREA_BOTTOM = IMAGE_AREA_TOP + 1060          # 인포그래픽 하단 (1310)
TTS_SUB_TOP = 975          # TTS 실시간 자막 시작 (유튜브 타이틀 회피)
TTS_SUB_HEIGHT = 295       # TTS 자막 높이 (1275~1570)
BOTTOM_BAR_HEIGHT = 55     # 하단 AI 고지 바 (1865~1920)

# ── 색상 ──
ACCENT_RED = (255, 60, 60)
GOLD = (255, 200, 50)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BG = (15, 15, 25)

# ── TTS ──
TTS_VOICES = [
    "ko-KR-InJoonNeural",           # 남성
    "ko-KR-HyunsuMultilingualNeural", # 남성 2
    "ko-KR-SunHiNeural",            # 여성
]
TTS_VOICE = os.getenv("TTS_VOICE", "ko-KR-InJoonNeural")  # fallback
TTS_RATE = os.getenv("TTS_RATE", "+15%")

# ── 일러스트 생성 (ollama) ──
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_IMAGE_MODEL = os.getenv("OLLAMA_IMAGE_MODEL", "x/z-image-turbo")

# ── YouTube ──
YOUTUBE_UPLOAD = os.getenv("YOUTUBE_UPLOAD", "true").lower() == "true"
YOUTUBE_CATEGORY = "25"  # News & Politics
CLIENT_SECRET_PATH = CONFIG_DIR / "client_secret.json"
TOKEN_PATH = CONFIG_DIR / "youtube_token.json"


# ── Discord ──
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")

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
    "Handwriting": [
        os.path.expanduser("~/Library/Fonts/ChosunSm.TTF"),
        "/Library/Fonts/ChosunSm.TTF",
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 0),    # fallback
    ],
}
