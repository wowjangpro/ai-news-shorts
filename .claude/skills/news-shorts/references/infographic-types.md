# 인포그래픽 타입별 데이터 구조

각 씬의 `infographic_data`에 `type` 필드로 타입 지정. `generate_infographic(w, h, prompt, tag, data=...)` 호출 시 자동 디스패치.

## headline — 대형 헤드라인

```python
{
    "type": "headline",
    "text": "메인 텍스트\n줄바꿈 가능",
    "sub_text": "보조 설명",          # 하단 작은 텍스트
    "style": "breaking",              # breaking | positive | negative | neutral
    "accent_color": [255, 60, 60]     # RGB (선택)
}
```

`style`에 따라 배경 그라데이션/글로우 색상 자동 변경.

## numbers — 핵심 수치 카드

```python
{
    "type": "numbers",
    "items": [
        {"label": "라벨", "value": "1,234만", "color": [80, 200, 255]},
        {"label": "라벨2", "value": "56%", "color": [255, 100, 100]},
    ],
    "accent_color": [80, 160, 255]    # 기본 글로우 색 (선택)
}
```

카드 높이·폰트 크기 자동 조절. items 2~4개 권장.

## list — 불릿 리스트

```python
{
    "type": "list",
    "title": "리스트 제목",            # 선택
    "items": [
        {"text": "항목 텍스트", "icon": "red"},
        {"text": "항목 텍스트", "icon": "green"},
    ],
    "accent_color": [60, 120, 255]    # 선택
}
```

`icon` 색상: `red` | `yellow` | `green` | `blue` | `gray`. items 3~6개 권장.

## quote — 인용문 카드

```python
{
    "type": "quote",
    "text": "인용문 텍스트\n줄바꿈 가능",
    "speaker": "화자 이름",
    "affiliation": "소속/직함",
    "accent_color": [100, 180, 255]   # 선택
}
```

좌측 악센트 바 + 대형 따옴표 장식.

## comparison — 비교 바 차트

```python
{
    "type": "comparison",
    "items": [
        {"label": "항목A", "value": 1200, "color": [255, 80, 80]},
        {"label": "항목B", "value": 950, "color": [80, 160, 255]},
    ],
    "baseline": {"label": "기준선", "value": 1000},  # 선택
    "unit": "원",                      # 선택 (값 뒤에 붙는 단위)
    "accent_color": [255, 100, 60]    # 선택
}
```

`value`는 숫자(int/float). 바 길이 자동 비례 계산. `baseline` 있으면 초록색 기준선 표시.

## 타입 선택 가이드

| 뉴스 유형 | 추천 타입 |
|-----------|----------|
| 속보/핵심 한줄 요약 | headline |
| 통계/수치 비교 | numbers |
| 사양/특징 나열 | list |
| 인물 발언/코멘트 | quote |
| 가격/수치 비교 | comparison |

하나의 영상(4~6씬)에서 2~3가지 타입을 섞어 사용하면 시각적으로 다채로움.
