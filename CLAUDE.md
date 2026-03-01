# AI 뉴스 쇼츠 자동 생성기 - Claude Code 프로젝트 컨텍스트

## 프로젝트 개요
오늘의 뉴스를 검색하여 유튜브 쇼츠(9:16, 1080x1920, 최대 3분) 영상을 자동 생성하는 파이프라인.
Mac M1 Pro Max 환경에서 로컬 실행.

## 기술 스택
- Python 3.11+, Pillow, edge-tts, FFmpeg
- 배경 일러스트: mflux (FLUX dev 모델, 로컬 생성)
- 인포그래픽: Pillow RGBA 투명 오버레이
- TTS: edge-tts (ko-KR-InJoonNeural 남성, 속도 +15%)
- 업로드: YouTube Data API v3

## 핵심 파이프라인
`scripts/run_news_shorts.py` — 범용 파이프라인 (JSON 데이터 입력 → 영상 출력)

1. 뉴스 검색 → `scripts/news_data.json` 작성 (매번 새로 작성)
2. **팩트체크** — 원본 기사와 JSON 데이터 대조 (숫자, 고유명사, 인용문, 맥락)
3. **배경 일러스트 생성** — mflux dev 모델로 풀스크린 일러스트 (1080x1920)
4. `src/graphics/infographic.py` — 투명 RGBA 인포그래픽 생성 (5개 범용 타입)
5. `edge-tts` — 씬별 TTS 나레이션 + 단어 타이밍 메타데이터 추출
6. `src/bgm_generator.py` — 뉴스 BGM 합성
7. `src/video_renderer.py` — 프레임별 렌더링 (배경 일러스트 + 오버레이 + 인포그래픽 합성)
8. `src/video_composer.py` — FFmpeg로 프레임 + 오디오 합성 (TTS 볼륨 3배)
9. `src/youtube_uploader.py` — YouTube 쇼츠 자동 업로드 (#Shorts 자동 태그)

## 영상 레이아웃 (1080x1920)
- 배경: mflux 풀스크린 일러스트 + 얇은 오버레이(alpha 60)
- 상단 헤더 0~250px: 빨간 태그 + 제목 + 날짜
- 씬 요약 자막 250~470px: 외곽선 자막 (WHITE/GOLD, 46px Black)
- 인포그래픽 470~1310px: 투명 RGBA 오버레이 (1080×840, 배경 위에 합성)
- TTS 실시간 자막 1570~1865px: 교보 손글씨 필기체, 현재 문장만 표시
- 하단 AI 고지 1865~1920px: "AI로 생성되어 사실과 다를 수 있습니다."

## 일러스트 배경 규칙
- mflux dev 모델, 20스텝, 4bit 양자화
- bg_prompt: "Flat editorial illustration of ..." 형식
- **사람, 동물, 새 등 생명체 절대 포함 금지**
- 항상 끝에 ", no text, no watermark" 추가
- 생성 후 품질 검증 → 미리보기 확인 → 수락/재생성

## 코딩 규칙
- 한글 주석 사용
- type hints 적극 활용
- 각 모듈은 독립적으로 테스트 가능하게 구성
- config/settings.py에서 모든 설정 중앙 관리

## 현재 상태
- [x] 풀스크린 일러스트 배경 (mflux dev, 확인/재생성 루프)
- [x] 투명 RGBA 인포그래픽 오버레이 (5개 범용 타입: headline, numbers, list, quote, comparison)
- [x] BGM 합성기
- [x] 영상 렌더러 (배경 일러스트 + 오버레이 + RGBA 인포그래픽 합성 + TTS자막)
- [x] TTS 연동 (edge-tts 남성 음성, +15% 속도, 단어 타이밍 동기화)
- [x] TTS 실시간 자막 (교보 손글씨 필기체, 현재 문장만 표시)
- [x] 씬 전환 최적화 (페이드인/아웃 0.2초, TTS 기반 씬 동기화)
- [x] 범용 파이프라인 (run_news_shorts.py + news_data.json)
- [x] YouTube 쇼츠 자동 공개 업로드 (OAuth 2.0, #Shorts 태그, 기본 공개)
- [x] 스킬 등록 (.claude/skills/news-shorts/)
- [x] Agent Teams 활성화

## GitHub
- https://github.com/wowjangpro/ai-news-shorts
