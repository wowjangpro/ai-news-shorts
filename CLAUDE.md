# AI 뉴스 쇼츠 자동 생성기 - Claude Code 프로젝트 컨텍스트

## 프로젝트 개요
오늘의 뉴스를 검색하여 유튜브 쇼츠(9:16, 1080x1920, 최대 3분) 영상을 자동 생성하는 파이프라인.
Mac M1 Pro Max 환경에서 로컬 실행.

## 기술 스택
- Python 3.11+, Pillow, edge-tts, FFmpeg
- 배경 일러스트: ollama Z-Image-Turbo (로컬 생성, ~2분, 1024x1024→1080x1920 center crop)
- 인포그래픽: Pillow RGBA 투명 오버레이 (stroke_width 최적화, 5종 카드 스타일 랜덤)
- TTS: edge-tts (ko-KR 남성/여성 랜덤, 속도 +15%)
- 영상 렌더링: FFmpeg 파이프 (raw RGB24 stdin) + 배치 렌더링
- 업로드: YouTube Data API v3 (기본 비공개)
- 텔레그램 봇: 메시지 수신 → Claude Code 비대화 모드 실행

## 핵심 파이프라인
`scripts/run_news_shorts.py` — 범용 파이프라인 (JSON 데이터 입력 → 영상 출력 → 비공개 업로드)

1. 뉴스 검색 → `scripts/news_data.json` 작성 (매번 새로 작성)
2. **팩트체크** — 원본 기사와 JSON 데이터 대조 (숫자, 고유명사, 인용문, 맥락)
3. **배경 일러스트 생성** — ollama Z-Image-Turbo로 일러스트 (1024→1080x1920 리사이즈)
4. `src/graphics/infographic.py` — 투명 RGBA 인포그래픽 생성 (5개 범용 타입, 5종 카드 스타일)
5. `edge-tts` — 씬별 TTS 나레이션 + 단어 타이밍 메타데이터 추출
6. `src/bgm_generator.py` — 뉴스 BGM 합성
7. `src/video_renderer.py` — 프레임별 렌더링 (배경 일러스트 + 오버레이 + 인포그래픽 합성)
8. `src/video_composer.py` — FFmpeg로 프레임 + 오디오 합성 (TTS 볼륨 3배)
9. `src/youtube_uploader.py` — YouTube 쇼츠 비공개 업로드 (#Shorts 자동 태그)

## 영상 레이아웃 (1080x1920)
- 배경: ollama 풀스크린 일러스트 (1024x1024→1080x1920 center crop)
- 상단 헤더 0~250px: 반투명 검정(50%) + 빨간 태그 + GOLD 제목 + 날짜
- 인포그래픽 250~1310px: 투명 RGBA 오버레이 (1080×1060, 폰트 1.25배)
- TTS 실시간 자막 1275~1570px: 교보 손글씨 필기체 (38/42px), 현재 문장만 표시
- 하단 바 1865~1920px: 좌 "AI로 생성되어 사실과 다를 수 있습니다." / 우 "공개된 언론 보도를 참고하여 재구성되었습니다."

## 인포그래픽 카드 스타일 (5종, 영상마다 랜덤)
- Classic: 라운드 사각형 카드
- Circle: 원형 컨테이너
- Banner: 가로 풀폭 배너
- Timeline: 좌측 수직선 + 노드
- Grid: 세로 타일 배치

## 일러스트 배경 규칙
- **ollama Z-Image-Turbo** (~2분, 1024x1024 → 1080x1920 center crop)
- bg_prompt: "Flat editorial illustration of ..." 형식
- **생명체(사람, 동물) 포함 가능** — 정상적 형태+품질 좋으면 오히려 좋음
- **부정 지시("no text" 등) 사용 금지** — 원치 않는 요소는 아예 언급하지 않기
- **텍스트 유발 요소 제외** — 간판, 현수막, 스크린, 책, 문서 등 글자가 나올 수 있는 요소는 프롬프트에서 빼기
- **사회적·윤리적 민감 요소 검수** — 국기·종교 상징·브랜드 로고 등 부정확 생성 시 문제되는 요소 확인
- 기사 분위기 반영 필수 — 위기/부정 기사는 어둡고 긴장감 있게, 긍정 기사는 밝고 따뜻하게

## 뉴스 선택 기준
- 오늘 날짜 기준 최신 뉴스
- **여러 매체가 동시에 보도하는 뉴스 우선 선택** (관련 기사 수가 많을수록 대중 관심도 높음, 조회수에 유리)
- 카테고리 우선순위: 정치 > 경제 > 사회

## 뉴스 검색 우선 참고 언론사
- 방송사: KBS, MBC, SBS, JTBC, YTN, MBN, TV조선, 채널A
- 통신사: 연합뉴스, 뉴스1, 뉴시스
- 종합일간지: 조선일보, 중앙일보, 동아일보, 한겨레, 경향신문, 한국일보
- 경제지: 한국경제, 매일경제, 서울경제
- 포털: 네이버뉴스, 다음뉴스

## YouTube 업로드 규칙
- **기본 비공개(private)** 업로드
- `youtube_title`에 **날짜 넣지 않기** — 제목만 작성 (70자 이내)
- #Shorts 태그 자동 부착

## JSON 작성 규칙
- **대통령 호칭**: "이재명" 단독 사용 금지 → 제목·자막·TTS 등 모든 곳에서 "이재명 대통령"으로 표기
- `tone`: dict로 커스텀 RGB 색상 (기사마다 새롭게)
- `bg_prompt`: 영문 일러스트 프롬프트 (텍스트 유발 요소·민감 요소 제외)
- `scripts/news_data.json`은 **git 커밋 금지** (.gitignore에 추가됨, 매번 덮어쓰는 파일)

## 텔레그램 봇
- `scripts/telegram_bot.py` — 메시지 수신 → Claude Code 비대화 모드로 작업 실행
- macOS LaunchAgent로 자동 시작 (`~/Library/LaunchAgents/com.ainews.telegram-bot.plist`)
- KeepAlive + RunAtLoad → 부팅/덮개 열 때 자동 실행
- 사용자 요청을 그대로 전달 (검색만 요청하면 검색만, 생성 요청하면 생성)

## 코딩 규칙
- 한글 주석 사용
- type hints 적극 활용
- 각 모듈은 독립적으로 테스트 가능하게 구성
- config/settings.py에서 모든 설정 중앙 관리

## 성능 최적화 (적용 완료)
- stroke_width: Pillow 내장 외곽선 (81회 draw→1회)
- FFmpeg 파이프: raw RGB24 프레임 stdin 전송 (PNG 디스크 I/O 제거)
- 배치 렌더링: os.cpu_count() 단위 프레임 묶어 처리
- 24fps: VIDEO_FPS 30→24 (파일 크기 20% 절감)

## 현재 상태
- [x] 풀스크린 일러스트 배경 (ollama Z-Image-Turbo)
- [x] 투명 RGBA 인포그래픽 오버레이 (5개 타입 × 5종 카드 스타일)
- [x] BGM 합성기
- [x] 영상 렌더러 (FFmpeg 파이프 + 배치 렌더링)
- [x] TTS 연동 (edge-tts 남성/여성 랜덤, +15% 속도)
- [x] TTS 실시간 자막 (교보 손글씨 필기체 38/42px)
- [x] 씬 전환 최적화 (페이드인/아웃 0.2초, TTS 기반 씬 동기화)
- [x] 범용 파이프라인 (run_news_shorts.py + news_data.json)
- [x] YouTube 쇼츠 비공개 업로드 (OAuth 2.0, #Shorts 태그)
- [x] 스킬 등록 (.claude/skills/news-shorts/)
- [x] Agent Teams 활성화
- [x] 텔레그램 봇 (LaunchAgent 자동 시작, Claude Code 비대화 모드 연동)

## GitHub
- https://github.com/wowjangpro/ai-news-shorts
