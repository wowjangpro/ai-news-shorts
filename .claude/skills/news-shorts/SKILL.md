---
name: news-shorts
description: "오늘의 뉴스를 검색하고 유튜브 쇼츠 영상을 자동 생성하는 스킬. 사용 시점: (1) 사용자가 뉴스 영상, 쇼츠 영상 제작을 요청할 때, (2) 오늘 뉴스로 영상 만들어줘, 뉴스 쇼츠 만들어줘 등의 요청, (3) 특정 뉴스 주제로 영상을 만들어 달라고 할 때. 트리거 키워드: 뉴스 영상, 쇼츠, 영상 제작, 뉴스 쇼츠, news shorts, 영상 만들어줘."
---

# AI 뉴스 쇼츠 영상 제작

프로젝트 루트: `/Users/jeniel/Works/ai-news-shorts`

## 워크플로우

### 1. 뉴스 선정
- `WebSearch`로 오늘 한국 주요 뉴스 검색
- **여러 매체가 동시에 보도하는 뉴스 우선** (대중 관심도 ↑, 조회수에 유리)
- 카테고리 우선순위: 정치 > 경제 > 사회
- 숫자/데이터가 풍부한 기사 우선 선택 (인포그래픽 시각화에 유리)
- `memory/generated_topics.md`에서 이미 다룬 주제인지 확인 — 중복 시 다른 주제 선택

### 2. 뉴스 데이터 JSON 작성
`scripts/news_data.json`을 새 뉴스 내용으로 작성. JSON 구조는 [references/script-format.md](references/script-format.md) 참조.

핵심 규칙:
- **씬 개수는 뉴스 분량에 맞게 유동적으로 결정** (3~10개), TTS 합계 **3분 이내** (유튜브 쇼츠 제한)
  - 짧은 단신: 3~4개 씬
  - 일반 뉴스: 4~6개 씬
  - 심층/데이터 많은 뉴스: 6~10개 씬
- 자막: **15자 이내 × 최대 3줄**, `\n`으로 줄바꿈
- `highlight_lines`: 핵심 데이터/숫자 줄은 GOLD, 설명 줄은 WHITE
- `tts_text`: 자연스러운 한국어 존댓말
- `image_prompt`: 인포그래픽 타입 키워드 (headline, numbers, list, quote, comparison)
- `infographic_data`: 인포그래픽 렌더링 데이터 — 타입별 구조는 [references/infographic-types.md](references/infographic-types.md) 참조
- `tone`: dict로 커스텀 RGB 색상 지정 (기사마다 새롭게)
  - `bg_top`, `bg_bottom`: 배경 그라데이션 (어두운 톤)
  - `glow`: 글로우 색상
  - `card_bg`, `card_outline`: 카드 배경/테두리
- `bg_prompt`: 영문 일러스트 프롬프트
  - 형식: "Flat editorial illustration of ..."
  - 기사 핵심 장면/분위기 묘사 (사람, 동물 등 생명체 포함 가능)
  - **부정 지시("no text" 등) 사용 금지** — 원치 않는 요소는 아예 언급하지 않기
  - **텍스트 유발 요소 제외** — 간판, 현수막, 스크린, 책, 문서 등 글자가 나올 수 있는 요소는 빼기
  - **사회적·윤리적 민감 요소 제외** — 국기, 종교 상징, 브랜드 로고 등
- `youtube_title`: **날짜 넣지 않기** — 제목만 작성 (70자 이내, 클릭 유도)
- **대통령 호칭**: "이재명" 단독 사용 금지 → "이재명 대통령"으로 표기

### 3. 팩트체크
영상 생성 **전**, 작성한 `news_data.json`을 원본 기사와 대조:

1. `WebSearch`로 해당 뉴스 원문 재검색 — **최소 3개 이상 언론사** 기사 참고
2. 아래 항목을 원문과 비교:
   - **숫자/통계**: 금액, 인원, 비율, 날짜 등 정확한지
   - **고유명사**: 인물명, 기관명, 법안명 등 오탈자 없는지
   - **인용문**: 발언 내용이 원문과 일치하는지
   - **맥락**: 사실관계가 왜곡·과장되지 않았는지
3. 불일치 발견 시 `news_data.json` 수정 후 진행

### 4. 영상 생성 + 업로드
```bash
rm -f output/bg_cache.png && yes | python scripts/run_news_shorts.py
```
- `output/bg_cache.png`를 삭제해야 새 배경 일러스트 생성 (이전 영상 캐시 방지)
- `yes`로 모든 확인 프롬프트 자동 응답 (일러스트 수락 + 업로드 수락)
- **기본 비공개(private)** 업로드
- 출력: `output/` 폴더에 MP4 + script JSON 저장
- 여러 영상 생성 시: JSON 작성 → 실행을 반복 (매번 bg_cache.png 삭제)

### 5. 결과 확인
파이프라인 로그에서 YouTube URL 확인. 필요 시 프레임 추출로 시각 확인:
```bash
ffmpeg -y -i output/영상파일.mp4 -vf "select='eq(n,30)'" -frames:v 1 /tmp/check.png
```
프레임 추출 후 `Read`로 시각 확인.

### 6. 기록 업데이트
`memory/generated_topics.md`에 날짜와 주제를 추가한다.

## Agent Team 구성 (병렬 실행)

여러 영상 제작 시, 팩트체크를 병렬로 실행:

| Teammate | 역할 |
|----------|------|
| 메인 에이전트 | 뉴스 검색, JSON 작성, 파이프라인 실행, 기록 업데이트 |
| 팩트체크 에이전트(들) | 각 뉴스 주제별 병렬 팩트체크 (WebSearch) |

## 영상 레이아웃 (1080×1920)

| 영역 | 위치 | 내용 |
|------|------|------|
| 헤더 | 0~250px | 반투명 검정(50%) + 빨간 태그 + GOLD 제목 + 날짜 |
| 인포그래픽 | 250~1310px | 투명 RGBA 오버레이 (1080×1060, 5종 카드 스타일 랜덤) |
| TTS 실시간 자막 | 1275~1570px | 교보 손글씨 필기체, 현재 문장만 표시 |
| 하단 바 | 1865~1920px | 좌: "AI로 생성되어 사실과 다를 수 있습니다." / 우: "공개된 언론 보도를 참고하여 재구성되었습니다." |

배경: ollama 풀스크린 일러스트 (1024x1024→1080x1920 center crop)

## 카드 스타일 (영상마다 랜덤 선택)
- Classic: 라운드 사각형 카드
- Circle: 원형 컨테이너
- Banner: 가로 풀폭 배너
- Timeline: 좌측 수직선 + 노드
- Grid: 세로 타일 배치

## 파이프라인 모듈

| 모듈 | 경로 | 역할 |
|------|------|------|
| VideoRenderer | `src/video_renderer.py` | FFmpeg 파이프 렌더링 (stroke_width + 배치, 24fps) |
| VideoComposer | `src/video_composer.py` | FFmpeg 합성 (video_only.mp4 + 오디오 믹싱, TTS 볼륨 3배) |
| BGMGenerator | `src/bgm_generator.py` | 뉴스 BGM 합성 |
| infographic | `src/graphics/infographic.py` | 투명 인포그래픽 생성 (5개 타입 × 5종 카드 스타일) |
| YouTubeUploader | `src/youtube_uploader.py` | YouTube 쇼츠 비공개 업로드 |

TTS: edge-tts (ko-KR 남성/여성 랜덤, 속도 +15%), 자막 폰트 38/42px (교보 손글씨)
설정: `config/settings.py`
YouTube: 기본 비공개 업로드, #Shorts 자동 태그

## 파일 구조
- `scripts/run_news_shorts.py` — 범용 파이프라인 (수정 불필요)
- `scripts/news_data.json` — 뉴스 데이터 (매번 새로 작성, git 커밋 금지)
- `scripts/discord_bot.py` — 디스코드 봇 데몬 (LaunchAgent 자동 시작)
- `config/settings.py` — 전역 설정 (레이아웃, 색상, 폰트, ollama 등)
