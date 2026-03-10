# AI 뉴스 쇼츠 자동 생성기

오늘의 뉴스를 검색하여 유튜브 쇼츠(9:16, 1080×1920, 최대 3분) 영상을 자동 생성하는 파이프라인.

## 요구사항

| 항목 | 버전 | 비고 |
|------|------|------|
| Python | 3.11+ | pyenv 권장 |
| FFmpeg | 6.0+ | libx264, aac, libmp3lame 인코더 필요 |
| Ollama | 0.17+ | 배경 일러스트 생성용 |
| Claude Code | 최신 | 텔레그램 봇 연동 시 필요 |

## 설치

### 1. 저장소 클론

```bash
git clone https://github.com/wowjangpro/ai-news-shorts.git
cd ai-news-shorts
```

### 2. Python 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. FFmpeg 설치

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg
```

### 4. 환경 설정

```bash
cp config/.env.example config/.env
```

`config/.env`를 열어 값을 채워 넣으세요:

```env
# 텔레그램 봇 (선택)
TELEGRAM_BOT_TOKEN=<BotFather에서 발급>
TELEGRAM_CHAT_ID=<본인 채팅 ID>

# TTS
TTS_VOICE=ko-KR-InJoonNeural
TTS_RATE=+15%

# 영상
VIDEO_FPS=24
VIDEO_CRF=20

# Ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_IMAGE_MODEL=x/z-image-turbo
```

### 5. Ollama 설치 및 모델 다운로드

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# 일러스트 생성 모델 다운로드
ollama pull x/z-image-turbo

# ollama 서버 실행 (백그라운드)
ollama serve &
```

### 6. 한글 폰트 설치

`config/settings.py`의 `FONT_PATHS`에서 각 가중치별로 첫 번째 존재하는 폰트를 사용합니다.

**macOS** — Apple SD Gothic Neo가 기본 설치되어 있음. 자막 필기체용 `ChosunSm.TTF`는 별도 설치 필요.

**Linux**:
```bash
# Ubuntu/Debian
sudo apt-get install fonts-noto-cjk

# CentOS/RHEL
sudo yum install google-noto-sans-cjk-fonts
```

> Linux에서는 필기체 폰트(ChosunSm.TTF)가 없으므로 Noto Sans CJK로 fallback됩니다.

### 7. YouTube 업로드 설정 (선택)

1. [Google Cloud Console](https://console.cloud.google.com)에서 프로젝트 생성
2. **YouTube Data API v3** 활성화
3. **OAuth 2.0 클라이언트 ID** 생성 (유형: 데스크톱 앱)
4. JSON 파일을 `config/client_secret.json`으로 저장
5. 첫 실행 시 브라우저에서 Google 계정 인증 → `config/youtube_token.json` 자동 생성

### 8. 디렉토리 생성

```bash
mkdir -p output assets
```

## 사용법

### 영상 생성 (CLI)

```bash
# scripts/news_data.json에 뉴스 데이터 작성 후 실행
rm -f output/bg_cache.png && yes | python scripts/run_news_shorts.py

# 다른 JSON 파일 지정
rm -f output/bg_cache.png && yes | python scripts/run_news_shorts.py path/to/data.json
```

### Claude Code로 자동 생성

```bash
claude
# 프롬프트: "오늘 주요 뉴스 검색해서 영상 올려줘"
```

### 텔레그램 봇

텔레그램에서 봇에게 메시지를 보내면 Claude Code가 자동으로 작업을 수행합니다.
이어서 대화하면 이전 맥락이 유지됩니다.

```
뉴스 검색해줘          → 검색 결과만 전송
영상 만들어줘          → 영상 생성 + 업로드
/new                  → 새 세션 시작 (대화 초기화)
/status               → 봇 상태 확인
/help                 → 도움말
```

**수동 실행:**
```bash
python scripts/telegram_bot.py
```

**macOS 자동 시작 (LaunchAgent):**

`~/Library/LaunchAgents/com.ainews.telegram-bot.plist` 파일을 생성합니다.
아래에서 `/path/to/` 부분을 실제 경로로 수정하세요.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ainews.telegram-bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/python3</string>
        <string>/path/to/ai-news-shorts/scripts/telegram_bot.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/ai-news-shorts</string>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/path/to/ai-news-shorts/output/bot.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/ai-news-shorts/output/bot_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.ainews.telegram-bot.plist
```

**Linux 자동 시작 (systemd):**

`/etc/systemd/system/ainews-telegram-bot.service` 파일을 생성합니다:

```ini
[Unit]
Description=AI News Shorts Telegram Bot
After=network.target

[Service]
Type=simple
User=<username>
WorkingDirectory=/path/to/ai-news-shorts
ExecStart=/path/to/python3 scripts/telegram_bot.py
Restart=always
StandardOutput=append:/path/to/ai-news-shorts/output/bot.log
StandardError=append:/path/to/ai-news-shorts/output/bot_error.log

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ainews-telegram-bot
sudo systemctl start ainews-telegram-bot
```

## 파이프라인 흐름

```
뉴스 검색 → news_data.json 작성 → 팩트체크
    ↓
배경 일러스트 생성 (ollama) → 인포그래픽 렌더링 (Pillow)
    ↓
TTS 나레이션 (edge-tts) → BGM 합성
    ↓
프레임 렌더링 (FFmpeg 파이프) → 최종 합성
    ↓
YouTube 비공개 업로드 → 텔레그램 알림
```

## 영상 레이아웃 (1080×1920)

| 영역 | 위치 | 내용 |
|------|------|------|
| 헤더 | 0~250px | 반투명 검정 + 빨간 태그 + GOLD 제목 + 날짜 |
| 인포그래픽 | 250~1310px | 투명 RGBA 오버레이 (5종 카드 스타일 랜덤) |
| TTS 자막 | 1275~1570px | 필기체, 현재 문장만 표시 |
| 하단 바 | 1865~1920px | AI 생성 고지 |

## 뉴스 데이터 JSON 형식

JSON 구조와 인포그래픽 타입별 데이터는 아래 참조:
- [script-format.md](.claude/skills/news-shorts/references/script-format.md)
- [infographic-types.md](.claude/skills/news-shorts/references/infographic-types.md)

## 프로젝트 구조

```
ai-news-shorts/
├── config/
│   ├── settings.py          # 전역 설정 (레이아웃, 색상, 폰트, API)
│   ├── .env                 # 환경변수 (git 제외)
│   ├── .env.example         # 환경변수 템플릿
│   ├── client_secret.json   # Google OAuth 클라이언트 (git 제외)
│   └── youtube_token.json   # YouTube 토큰 (자동 생성, git 제외)
├── scripts/
│   ├── run_news_shorts.py   # 메인 파이프라인
│   ├── news_data.json       # 뉴스 데이터 (매번 덮어쓰기, git 제외)
│   └── telegram_bot.py      # 텔레그램 봇 데몬
├── src/
│   ├── graphics/
│   │   └── infographic.py   # 인포그래픽 렌더링 (5개 타입 × 5종 카드 스타일)
│   ├── bgm_generator.py     # BGM 합성
│   ├── video_renderer.py    # 프레임 렌더링 (FFmpeg 파이프)
│   ├── video_composer.py    # 영상 합성 (비디오 + 오디오)
│   └── youtube_uploader.py  # YouTube 업로드
├── output/                  # 생성된 영상·로그 (git 제외)
├── assets/                  # 동적 에셋 (git 제외)
├── memory/
│   └── generated_topics.md  # 생성된 주제 기록 (중복 방지)
├── .claude/
│   └── skills/news-shorts/  # Claude Code 스킬
├── CLAUDE.md                # Claude Code 프로젝트 컨텍스트
├── requirements.txt
└── README.md
```

## 포팅 체크리스트

- [ ] Python 3.11+ 설치
- [ ] `pip install -r requirements.txt`
- [ ] FFmpeg 설치
- [ ] Ollama 설치 + `ollama pull x/z-image-turbo`
- [ ] 한글 폰트 설치 (Linux: `fonts-noto-cjk`)
- [ ] `cp config/.env.example config/.env` → 값 채우기
- [ ] `mkdir -p output assets`
- [ ] (선택) YouTube: `config/client_secret.json` 설정
- [ ] (선택) 텔레그램 봇: LaunchAgent 또는 systemd 설정
- [ ] (선택) Claude Code 설치 (텔레그램 봇 연동 시)
- [ ] 테스트: `rm -f output/bg_cache.png && yes | python scripts/run_news_shorts.py`
