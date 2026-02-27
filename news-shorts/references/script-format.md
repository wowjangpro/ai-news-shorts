# 뉴스 데이터 JSON 형식

## JSON 구조

```json
{
    "title": "15자 이내 제목",
    "youtube_title": "50자 이내",
    "youtube_description": "설명",
    "youtube_tags": ["태그1", "태그2"],
    "scenes": [ ... ]
}
```

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
| `subtitle` | 하단 자막 (`\n` 줄바꿈, 15자×3줄 max) |
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
```

출력: `output/` 폴더에 MP4 + script JSON 저장.
