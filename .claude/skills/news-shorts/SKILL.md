---
name: news-shorts
description: "오늘의 뉴스를 검색하고 유튜브 쇼츠 영상을 자동 생성하는 스킬. 사용 시점: (1) 사용자가 뉴스 영상, 쇼츠 영상 제작을 요청할 때, (2) 오늘 뉴스로 영상 만들어줘, 뉴스 쇼츠 만들어줘 등의 요청, (3) 특정 뉴스 주제로 영상을 만들어 달라고 할 때. 트리거 키워드: 뉴스 영상, 쇼츠, 영상 제작, 뉴스 쇼츠, news shorts, 영상 만들어줘."
---

# AI 뉴스 쇼츠 영상 제작

프로젝트 루트: `/Users/jeniel/Works/ai-news-shorts`

## 워크플로우

### 1. 뉴스 선정
- `WebSearch`로 오늘 한국 주요 뉴스 검색
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
  - **사회적·윤리적 민감 요소 제외** — 국기, 종교 상징, 브랜드 로고 등

### 3. 팩트체크
영상 생성 **전**, 작성한 `news_data.json`을 원본 기사와 대조:

1. `WebSearch`로 해당 뉴스 원문 재검색
2. 아래 항목을 원문과 비교:
   - **숫자/통계**: 금액, 인원, 비율, 날짜 등 정확한지
   - **고유명사**: 인물명, 기관명, 법안명 등 오탈자 없는지
   - **인용문**: 발언 내용이 원문과 일치하는지
   - **맥락**: 사실관계가 왜곡·과장되지 않았는지
3. 불일치 발견 시 `news_data.json` 수정 후 진행

### 4. 배경 일러스트 생성
ollama Z-Image-Turbo로 배경 일러스트를 생성한다 (run_news_shorts.py가 자동 실행).
- 1024x1024 생성 → 1080x1920 center crop (파이프라인 내부 처리)
- 캐시: `output/bg_cache.png` (테스트 시 재사용)

생성 후 품질+윤리 검증:
1. `Read`로 이미지를 시각적으로 확인
2. **사회적·윤리적 민감 요소** 확인 (국기·종교·브랜드 로고 등 부정확한 요소)
3. 워터마크/텍스트 아티팩트 확인
4. 문제가 있으면 프롬프트를 수정하여 재생성
5. 문제없으면 진행 (파이프라인이 자동 사용)

### 5. 영상 생성 실행
```bash
echo "y" | python scripts/run_news_shorts.py
```
`scripts/news_data.json`을 읽어 영상 생성. 캐시된 배경 일러스트를 자동 사용.
출력: `output/` 폴더에 MP4 + script JSON 저장.
다른 JSON 파일 지정도 가능: `python scripts/run_news_shorts.py path/to/data.json`

### 6. 결과 확인
```bash
ffmpeg -y -i output/영상파일.mp4 -vf "select='eq(n,30)'" -frames:v 1 /tmp/check.png
```
프레임 추출 후 `Read`로 시각 확인.

### 7. YouTube 업로드
영상에 문제가 없으면 업로드:
```bash
python scripts/upload.py output/영상파일.mp4
```

### 8. 기록 업데이트
`memory/generated_topics.md`에 날짜와 주제를 추가한다.

## Agent Team 구성 (병렬 실행)

Phase 1(뉴스 리서치 + JSON) 완료 후, 아래를 병렬로 실행:

| Teammate | 역할 | Phase |
|----------|------|-------|
| 메인 에이전트 | 뉴스 검색, JSON 작성, 팩트체크, 최종 업로드 | 1, 3, 7, 8 |
| 일러스트 담당 | ollama 배경 일러스트 생성 + 품질/윤리 검증 | 4 |
| 영상 제작 | 파이프라인 실행 + 프레임 확인 | 5, 6 |

## 영상 레이아웃 (1080×1920)

| 영역 | 위치 | 내용 |
|------|------|------|
| 헤더 | 0~250px | 빨간 태그 + 메인 제목 + 날짜 |
| 씬 요약 자막 | 250~470px | 외곽선 자막 (WHITE/GOLD, 46px Black) |
| 인포그래픽 | 470~1310px | 투명 RGBA 오버레이 (1080×840) |
| TTS 실시간 자막 | 1570~1865px | 교보 손글씨 필기체, 현재 문장만 표시 |
| 하단 AI 고지 | 1865~1920px | "AI로 생성되어 사실과 다를 수 있습니다." |

배경: ollama 풀스크린 일러스트 (1024x1024→1080x1920 center crop)

## 파이프라인 모듈

| 모듈 | 경로 | 역할 |
|------|------|------|
| VideoRenderer | `src/video_renderer.py` | FFmpeg 파이프 렌더링 (stroke_width + 배치, 24fps) |
| VideoComposer | `src/video_composer.py` | FFmpeg 합성 (video_only.mp4 + 오디오 믹싱, TTS 볼륨 3배) |
| BGMGenerator | `src/bgm_generator.py` | 뉴스 BGM 합성 |
| infographic | `src/graphics/infographic.py` | 투명 인포그래픽 생성 (5개 범용 타입) |
| YouTubeUploader | `src/youtube_uploader.py` | YouTube 쇼츠 자동 업로드 |

TTS: edge-tts (`ko-KR-InJoonNeural` 남성, 속도 +15%), 자막 폰트 38/42px (교보 손글씨)
설정: `config/settings.py`
YouTube: 기본 공개 업로드 (`YOUTUBE_UPLOAD=true`), #Shorts 자동 태그

## 파일 구조
- `scripts/run_news_shorts.py` — 범용 파이프라인 (수정 불필요)
- `scripts/news_data.json` — 뉴스 데이터 (매번 새로 작성)
- `scripts/upload.py` — 수동 YouTube 업로드
- `config/settings.py` — 전역 설정 (레이아웃, 색상, 폰트, ollama/mflux 등)
