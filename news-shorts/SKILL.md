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

### 3. 팩트체크
영상 생성 **전**, 작성한 `news_data.json`을 원본 기사와 대조:

1. `WebSearch`로 해당 뉴스 원문 재검색
2. 아래 항목을 원문과 비교:
   - **숫자/통계**: 금액, 인원, 비율, 날짜 등 정확한지
   - **고유명사**: 인물명, 기관명, 법안명 등 오탈자 없는지
   - **인용문**: 발언 내용이 원문과 일치하는지
   - **맥락**: 사실관계가 왜곡·과장되지 않았는지
3. 불일치 발견 시 `news_data.json` 수정 후 진행

### 4. 영상 생성 실행
```bash
python scripts/run_news_shorts.py
```
`scripts/news_data.json`을 읽어 영상 생성. 출력: `output/` 폴더에 MP4 + script JSON 저장.
다른 JSON 파일 지정도 가능: `python scripts/run_news_shorts.py path/to/data.json`

### 5. 결과 확인
```bash
ffmpeg -i output/영상파일.mp4 -vf "select='eq(n,프레임번호)'" -vsync vfr -frames:v 1 /tmp/check.png
```
프레임 추출 후 `Read`로 시각 확인.

## 영상 레이아웃 (1080×1920)

| 영역 | 위치 | 내용 |
|------|------|------|
| 헤더 | 0~250px | 빨간 태그 + 메인 제목 + 날짜 |
| 이미지 | 250~1570px | 인포그래픽 (1080×1320) |
| 자막 | 1570~1865px | 외곽선 자막 (WHITE/GOLD 혼합) |
| 하단바 | 1865~1920px | 해시태그 |

## 파이프라인 모듈

| 모듈 | 경로 | 역할 |
|------|------|------|
| VideoRenderer | `src/video_renderer.py` | 프레임별 렌더링 |
| VideoComposer | `src/video_composer.py` | FFmpeg 합성 |
| BGMGenerator | `src/bgm_generator.py` | 뉴스 BGM 합성 |
| infographic | `src/graphics/infographic.py` | 인포그래픽 생성 (5개 범용 타입) |

TTS: edge-tts (`ko-KR-InJoonNeural` 남성, 속도 +15%), 설정: `config/settings.py`

## 파일 구조
- `scripts/run_news_shorts.py` — 범용 파이프라인 (수정 불필요)
- `scripts/news_data.json` — 뉴스 데이터 (매번 새로 작성)
- `scripts/generate_kospi_shorts.py` — 코스피 6000 뉴스 (기존 완성 영상, 참고용)
