# 🎬 AI 뉴스 쇼츠 자동 생성기

오늘의 뉴스를 JSON 데이터로 작성하면 유튜브 쇼츠 영상을 자동 생성하고 업로드하는 파이프라인입니다.

## 파이프라인

```
news_data.json → 인포그래픽 → TTS → BGM → 프레임 렌더링 → FFmpeg 합성 → YouTube 업로드
```

1. **인포그래픽 생성** — 씬별 데이터 기반 시각화 (5개 타입: headline, numbers, list, quote, comparison)
2. **TTS 나레이션** — edge-tts 한국어 남성 음성 (`ko-KR-InJoonNeural`, +15% 속도)
3. **BGM 합성** — 뉴스 스타일 배경음악 자동 생성
4. **프레임 렌더링** — TTS 길이 기반 씬 동기화, 자막 애니메이션
5. **영상 합성** — FFmpeg로 프레임 + 오디오 합성 (1080×1920, 9:16)
6. **YouTube 업로드** — YouTube Data API v3 자동 공개 업로드 (#Shorts 자동 태그)

## 영상 레이아웃 (1080×1920)

| 영역 | 위치 | 내용 |
|------|------|------|
| 헤더 | 0~250px | 빨간 태그 + 메인 제목 + 날짜 |
| 이미지 | 250~1570px | 인포그래픽 (1080×1320) |
| 자막 | 1570~1865px | 외곽선 자막 (WHITE/GOLD 혼합) |
| 하단바 | 1865~1920px | 해시태그 |

## 환경

- **OS**: macOS (M1 Pro Max)
- **Python**: 3.11+
- **FFmpeg**: 필수

## 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt
brew install ffmpeg  # 없으면

# 2. 뉴스 데이터 작성
# scripts/news_data.json 편집 (형식은 아래 참조)

# 3. 영상 생성 + YouTube 업로드
python scripts/run_news_shorts.py

# 다른 JSON 파일로 생성
python scripts/run_news_shorts.py path/to/data.json

# YouTube 업로드 없이 생성만
YOUTUBE_UPLOAD=false python scripts/run_news_shorts.py
```

## 뉴스 데이터 JSON 형식

```json
{
    "title": "15자 이내 제목",
    "youtube_title": "50자 이내 YouTube 제목",
    "youtube_description": "영상 설명",
    "youtube_tags": ["태그1", "태그2"],
    "scenes": [
        {
            "tag": "속보",
            "subtitle": "첫째 줄\n둘째 줄\n셋째 줄",
            "highlight_lines": [0],
            "tts_text": "TTS로 읽을 자연스러운 한국어 문장",
            "image_prompt": "headline",
            "duration": 6,
            "infographic_data": {
                "type": "headline",
                "text": "메인 텍스트",
                "sub_text": "보조 설명",
                "style": "breaking"
            }
        }
    ]
}
```

- **씬 개수**: 3~10개 (뉴스 분량에 따라 유동적, TTS 합계 3분 이내)
- **자막**: 15자 이내 × 최대 3줄, `\n`으로 줄바꿈
- **highlight_lines**: GOLD 색상으로 강조할 줄 인덱스 (나머지 WHITE)
- **인포그래픽 타입**: `headline` | `numbers` | `list` | `quote` | `comparison`

## 프로젝트 구조

```
ai-news-shorts/
├── scripts/
│   ├── run_news_shorts.py        # 범용 영상 생성 파이프라인
│   ├── news_data.json            # 뉴스 데이터 (매번 새로 작성)
│   └── generate_kospi_shorts.py  # 코스피 6000 뉴스 (참고용)
├── src/
│   ├── video_renderer.py         # 프레임별 렌더링 (TTS 기반 씬 동기화)
│   ├── video_composer.py         # FFmpeg 합성 (나레이션 3배 볼륨)
│   ├── bgm_generator.py          # 뉴스 BGM 합성
│   ├── youtube_uploader.py       # YouTube 쇼츠 자동 업로드
│   └── graphics/
│       └── infographic.py        # 인포그래픽 생성 (5개 범용 타입)
├── config/
│   ├── settings.py               # 전역 설정
│   ├── client_secret.json        # Google OAuth 2.0 (gitignore)
│   └── youtube_token.json        # YouTube 인증 토큰 (gitignore)
├── output/                       # 생성된 영상 (gitignore)
├── news-shorts/                  # Claude Code 스킬
│   └── SKILL.md
└── CLAUDE.md                     # Claude Code 프로젝트 컨텍스트
```

## YouTube 업로드 설정

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. YouTube Data API v3 활성화
3. OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱)
4. `client_secret.json`을 `config/` 디렉토리에 저장
5. 첫 실행 시 브라우저에서 Google 계정 인증 (이후 토큰 자동 갱신)

기본 설정: 자동 공개 업로드, #Shorts 자동 태그, 카테고리 News & Politics
