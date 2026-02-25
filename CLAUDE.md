# AI 뉴스 쇼츠 자동 생성기 - Claude Code 프로젝트 컨텍스트

## 프로젝트 개요
오늘의 뉴스를 크롤링하여 유튜브 쇼츠(9:16, 1080x1920) 영상을 자동 생성하는 파이프라인.
Mac M1 Pro Max 환경에서 로컬 실행을 기본으로 하되, 이미지 생성은 API 활용 가능.

## 기술 스택
- Python 3.11+, Pillow, edge-tts, FFmpeg
- 이미지: Replicate API (FLUX) 또는 로컬 Stable Diffusion (MLX)
- TTS: edge-tts (Microsoft, 무료)
- 업로드: YouTube Data API v3

## 핵심 파이프라인
1. `news_fetcher.py` — 뉴스 URL → 기사 텍스트 + AI 요약 (6개 씬)
2. `image_generator.py` — 씬별 프롬프트 → 실사 이미지 생성
3. `tts_generator.py` — 자막 텍스트 → 한국어 TTS 음성
4. `bgm_generator.py` — 뉴스 스타일 배경음악 합성
5. `video_renderer.py` — 프레임별 렌더링 (헤더 + 이미지 + 자막)
6. `video_composer.py` — FFmpeg로 프레임 + 오디오 합성
7. `youtube_uploader.py` — 자동 업로드

## 영상 레이아웃 (1080x1920)
- 상단 0~250px: 검정 배경, 빨간 태그 + 제목
- 중앙 250~1570px: 실사 이미지 또는 인포그래픽
- 하단 1570~1920px: 반투명 검정 + 외곽선 자막

## 코딩 규칙
- 한글 주석 사용
- type hints 적극 활용
- 각 모듈은 독립적으로 테스트 가능하게 구성
- config/settings.py에서 모든 설정 중앙 관리
- 에러 시 graceful fallback (예: API 실패 → 코드 인포그래픽)

## 현재 상태
- [x] 코드 인포그래픽 배경 렌더러 (graphics/infographic.py)
- [x] BGM 합성기
- [x] 영상 렌더러 기본 구조
- [ ] 뉴스 크롤링 모듈
- [ ] Replicate 이미지 생성 연동
- [ ] TTS 연동
- [ ] YouTube 업로드 연동
- [ ] 전체 파이프라인 통합 테스트

## 참고 샘플
- YouTube Shorts 샘플: https://www.youtube.com/shorts/J1lCB7hYdBg
- 포맷: 세로, 상단 제목, 중앙 이미지, 하단 자막 (큰 글씨, 외곽선)
