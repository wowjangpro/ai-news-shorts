# AI 뉴스 쇼츠 자동 생성기 - Claude Code 프로젝트 컨텍스트

## 프로젝트 개요
오늘의 뉴스를 검색하여 유튜브 쇼츠(9:16, 1080x1920, 최대 3분) 영상을 자동 생성하는 파이프라인.
Mac M1 Pro Max 환경에서 로컬 실행.

## 기술 스택
- Python 3.11+, Pillow, edge-tts, FFmpeg
- 이미지: 코드 인포그래픽 (Pillow)
- TTS: edge-tts (ko-KR-InJoonNeural 남성)
- 업로드: YouTube Data API v3

## 핵심 파이프라인
`scripts/run_news_shorts.py` — 범용 파이프라인 (JSON 데이터 입력 → 영상 출력)

1. `scripts/news_data.json` — 뉴스 데이터 (매번 새로 작성)
2. `src/graphics/infographic.py` — 인포그래픽 배경 생성 (5개 범용 타입)
3. `edge-tts` — 씬별 TTS 나레이션
4. `src/bgm_generator.py` — 뉴스 BGM 합성
5. `src/video_renderer.py` — 프레임별 렌더링 (헤더 + 이미지 + 자막)
6. `src/video_composer.py` — FFmpeg로 프레임 + 오디오 합성

## 영상 레이아웃 (1080x1920)
- 상단 0~250px: 검정 배경, 빨간 태그 + 제목 + 날짜
- 중앙 250~1570px: 인포그래픽 (1080×1320)
- 하단 1570~1920px: 반투명 검정 + 외곽선 자막 (WHITE/GOLD 혼합)

## 코딩 규칙
- 한글 주석 사용
- type hints 적극 활용
- 각 모듈은 독립적으로 테스트 가능하게 구성
- config/settings.py에서 모든 설정 중앙 관리

## 현재 상태
- [x] 코드 인포그래픽 배경 렌더러 (5개 범용 타입: headline, numbers, list, quote, comparison)
- [x] BGM 합성기
- [x] 영상 렌더러 (헤더 + 자막 + highlight_lines)
- [x] TTS 연동 (edge-tts 남성 음성)
- [x] 범용 파이프라인 (run_news_shorts.py + news_data.json)
- [ ] YouTube 업로드 연동

## 참고 샘플
- YouTube Shorts 샘플: https://www.youtube.com/shorts/J1lCB7hYdBg
- 포맷: 세로, 상단 제목, 중앙 이미지, 하단 자막 (큰 글씨, 외곽선)
