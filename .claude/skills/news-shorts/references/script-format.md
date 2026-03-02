# 뉴스 데이터 JSON 형식

## JSON 구조

```json
{
    "title": "15자 이내 제목",
    "tone": {
        "bg_top": [12, 22, 32],
        "bg_bottom": [6, 14, 22],
        "glow": [70, 170, 140],
        "card_bg": [14, 26, 34],
        "card_outline": [30, 58, 62]
    },
    "bg_prompt": "Flat editorial illustration of ...",
    "youtube_title": "70자 이내",
    "youtube_description": "설명",
    "youtube_tags": ["태그1", "태그2"],
    "scenes": [ ... ]
}
```

| 필드 | 설명 |
|------|------|
| `title` | 한글 뉴스 제목 (15자 이내) |
| `tone` | 커스텀 RGB 색상 (기사마다 새롭게 지정) |
| `bg_prompt` | 영문 일러스트 프롬프트 (생명체 포함 가능, 국기/종교/브랜드 제외) |
| `youtube_title` | 유튜브 제목 (클릭 유도, 70자 이내) |
| `youtube_description` | 기사 요약 + 하단에 `\n\n※ 본 영상은 공개된 언론 보도를 참고하여 재구성되었습니다.` 필수 |
| `youtube_tags` | 관련 태그 배열 |

### tone 색상 가이드
- `bg_top`, `bg_bottom`: 배경 그라데이션 (어두운 톤, 인포그래픽 fallback용)
- `glow`: 글로우 효과 색상
- `card_bg`: 카드 배경 색상
- `card_outline`: 카드 테두리 색상

### bg_prompt 작성 규칙
- 형식: "Flat editorial illustration of ..."
- 기사 핵심 장면/분위기 묘사 (사람, 동물 등 생명체 포함 가능)
- 색감은 기사 분위기 반영 (밝은 뉴스=warm, 어두운 뉴스=cool dark)
- **부정 지시("no text" 등) 사용 금지** — 원치 않는 요소는 아예 언급하지 않기
- **사회적·윤리적 민감 요소 제외** — 국기, 종교 상징, 브랜드 로고 등

## 씬 구조

```json
{
    "tag": "속보",
    "subtitle": "첫째 줄\n둘째 줄",
    "highlight_lines": [1],
    "tts_text": "TTS로 읽을 문장",
    "image_prompt": "인포그래픽 타입 키워드",
    "duration": 6,
    "infographic_data": { ... }
}
```

| 필드 | 설명 |
|------|------|
| `tag` | 헤더 빨간 태그 (2~5자) |
| `subtitle` | 씬 요약 자막 (`\n` 줄바꿈, 15자×3줄 max) |
| `highlight_lines` | GOLD 색상 줄 인덱스 (나머지 WHITE) |
| `tts_text` | 자연스러운 한국어 존댓말 |
| `image_prompt` | 인포그래픽 타입 키워드 (headline, numbers, list, quote, comparison) |
| `duration` | 씬 길이 (초) |
| `infographic_data` | 인포그래픽 렌더링 데이터 — 타입별 구조는 [infographic-types.md](infographic-types.md) 참조 |

## highlight_lines 패턴

- 핵심 데이터/숫자 줄 → GOLD (인덱스 포함)
- 일반 설명/맥락 줄 → WHITE (인덱스 미포함)
- 빈 리스트 `[]` → 모든 줄 WHITE

## 실행 방법

```bash
# 기본 (scripts/news_data.json 사용)
python scripts/run_news_shorts.py

# 다른 JSON 파일 지정
python scripts/run_news_shorts.py path/to/data.json

# 수동 업로드
python scripts/upload.py output/영상파일.mp4
```

출력: `output/` 폴더에 MP4 + script JSON 저장.
