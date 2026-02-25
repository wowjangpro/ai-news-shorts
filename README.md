# 🎬 AI 뉴스 쇼츠 자동 생성기

오늘의 뉴스를 자동으로 유튜브 쇼츠 영상으로 만들어주는 파이프라인입니다.

## 기능

1. **뉴스 크롤링** — 오늘의 주요 뉴스 기사 수집
2. **기사 요약** — AI로 쇼츠에 맞게 단락별 요약
3. **이미지 생성** — 단락별 실사 이미지 생성 (Replicate API 또는 로컬 SD)
4. **TTS 나레이션** — 한국어 음성 생성 (edge-tts)
5. **BGM 합성** — 뉴스 스타일 배경음악 자동 생성
6. **영상 합성** — 9:16 세로 쇼츠 영상 (1080x1920)
7. **YouTube 업로드** — YouTube Data API v3 자동 업로드

## 환경

- **OS**: macOS (M1 Pro Max 최적화)
- **Python**: 3.11+
- **FFmpeg**: 필수

## 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt
brew install ffmpeg  # 없으면

# 2. 환경변수 설정
cp config/.env.example config/.env
# config/.env 파일을 열어 API 키 입력

# 3. 실행
python src/main.py

# 특정 뉴스 URL로 실행
python src/main.py --url "https://news.example.com/article/123"

# 이미지 생성 방식 선택
python src/main.py --image-source replicate  # Replicate API (추천)
python src/main.py --image-source local      # 로컬 Stable Diffusion
python src/main.py --image-source stock      # 무료 스톡 이미지
python src/main.py --image-source graphic    # 코드 생성 인포그래픽

# YouTube 업로드 포함
python src/main.py --upload
```

## 프로젝트 구조

```
ai-news-shorts/
├── README.md
├── requirements.txt
├── CLAUDE.md                  # Claude Code 프로젝트 컨텍스트
├── config/
│   ├── .env.example           # 환경변수 템플릿
│   └── settings.py            # 전역 설정
├── src/
│   ├── main.py                # 메인 파이프라인
│   ├── news_fetcher.py        # 뉴스 크롤링 & 요약
│   ├── image_generator.py     # 이미지 생성 (멀티 소스)
│   ├── tts_generator.py       # TTS 음성 생성
│   ├── bgm_generator.py       # 배경음악 합성
│   ├── video_renderer.py      # 영상 프레임 렌더링
│   ├── video_composer.py      # FFmpeg 영상 합성
│   ├── youtube_uploader.py    # YouTube 업로드
│   └── graphics/
│       └── infographic.py     # 코드 기반 인포그래픽 배경
├── templates/
│   └── news_prompt.txt        # 기사 요약 프롬프트 템플릿
├── assets/                    # 생성된 에셋 (gitignore)
└── output/                    # 최종 영상 (gitignore)
```

## 이미지 생성 옵션

| 방식 | 품질 | 비용 | 속도 | 설정 난이도 |
|------|------|------|------|------------|
| Replicate (FLUX) | ⭐⭐⭐⭐⭐ | ~$0.01/장 | 10초 | 쉬움 |
| 로컬 SD (MLX) | ⭐⭐⭐⭐ | 무료 | 1~3분 | 보통 |
| 스톡 이미지 | ⭐⭐⭐ | 무료 | 즉시 | 쉬움 |
| 코드 인포그래픽 | ⭐⭐⭐ | 무료 | 즉시 | 없음 |

## YouTube 업로드 설정

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. YouTube Data API v3 활성화
3. OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱)
4. `client_secret.json`을 `config/` 디렉토리에 저장
5. `config/.env`에서 `YOUTUBE_UPLOAD=true` 설정

## 자동화 (cron)

```bash
# 매일 오전 9시에 자동 실행
0 9 * * * cd /path/to/ai-news-shorts && python src/main.py --upload >> output/cron.log 2>&1
```
