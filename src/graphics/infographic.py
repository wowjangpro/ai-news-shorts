"""코드 기반 인포그래픽 배경 생성기 — 강화 버전
글로우, 그라데이션, 카드 레이아웃으로 고품질 뉴스 비주얼 생성"""
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import os


# ── 카드 스타일 (5종) ──
_card_style = 0
# 0: Classic(둥근카드), 1: Circle(원형), 2: Banner(배너바),
# 3: Timeline(타임라인), 4: Grid(그리드타일)

def set_card_style(style: int):
    """카드 스타일 설정 (0~4)"""
    global _card_style
    _card_style = style % 5

def get_random_card_style() -> int:
    """랜덤 카드 스타일 선택 후 반환"""
    global _card_style
    _card_style = random.randint(0, 4)
    return _card_style

CARD_STYLE_NAMES = ["Classic", "Circle", "Banner", "Timeline", "Grid"]


# ── 유틸리티 ──

FONT_SCALE = 1.25  # 인포그래픽 전체 폰트 스케일

def _get_font(size, weight="Bold"):
    """시스템 한글 폰트 로드 (.ttc 인덱스 지원)"""
    size = int(size * FONT_SCALE)
    paths = {
        "Black": [("/System/Library/Fonts/AppleSDGothicNeo.ttc", 16),
                   "/Library/Fonts/NanumSquareRoundEB.ttf",
                   "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"],
        "Bold": [("/System/Library/Fonts/AppleSDGothicNeo.ttc", 6),
                  "/Library/Fonts/NanumSquareRoundB.ttf",
                  "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"],
        "Medium": [("/System/Library/Fonts/AppleSDGothicNeo.ttc", 4),
                    "/Library/Fonts/NanumSquareRound.ttf",
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"],
        "Regular": [("/System/Library/Fonts/AppleSDGothicNeo.ttc", 0),
                     "/Library/Fonts/NanumSquareRoundR.ttf",
                     "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"],
    }
    for entry in paths.get(weight, paths["Bold"]):
        if isinstance(entry, tuple):
            p, idx = entry
        else:
            p, idx = entry, 0
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size, index=idx)
            except Exception:
                continue
    return ImageFont.load_default()


def _lerp(c1, c2, t):
    """두 색상 선형 보간"""
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _gradient(draw, x0, y0, x1, y1, c_top, c_bottom):
    """수직 그라데이션"""
    for y in range(int(y0), int(y1)):
        t = (y - y0) / max(1, y1 - y0)
        draw.line([(x0, y), (x1, y)], fill=_lerp(c_top, c_bottom, t))


def _add_glow(img, draw_fn, blur_radius=15):
    """글로우 레이어를 생성·블러·합성, 새 Image 반환"""
    glow = Image.new("RGB", img.size, (0, 0, 0))
    draw_fn(ImageDraw.Draw(glow))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    return ImageChops.add(img, glow)


def _center_glow(draw, cx, cy, radius, color):
    """중앙에서 퍼지는 은은한 빛"""
    steps = 40
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(radius * t)
        brightness = 1.0 - t
        c = tuple(int(v * brightness * 0.3) for v in color)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)



def _right_text(draw, text, x_right, y, font, fill):
    """오른쪽 정렬 텍스트"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((x_right - tw, y), text, font=font, fill=fill)


# ── 톤 (기사 분위기별 색상) ──

# 기본 톤 (tone 미지정 시 사용)
_DEFAULT_TONE = {
    "bg_top": [8, 12, 30],
    "bg_bottom": [5, 5, 20],
    "glow": [50, 80, 140],
    "card_bg": [15, 18, 32],
    "card_outline": [30, 38, 55],
}


def _get_tone(data: dict) -> dict:
    """데이터에서 톤 추출 — JSON에서 직접 RGB 값을 받아 사용
    tone이 dict면 커스텀 색상, 미지정이면 기본값 사용"""
    tone = data.get("tone")
    if isinstance(tone, dict):
        merged = dict(_DEFAULT_TONE)
        merged.update(tone)
        return {k: tuple(v) for k, v in merged.items()}
    return {k: tuple(v) for k, v in _DEFAULT_TONE.items()}


def _make_base(w: int, h: int, tone: dict, bg_img: Image.Image | None = None) -> Image.Image:
    """배경 생성 — bg_img 있으면 투명 RGBA 캔버스, 없으면 그라데이션"""
    if bg_img is not None:
        return Image.new("RGBA", (w, h), (0, 0, 0, 0))
    else:
        img = Image.new("RGB", (w, h), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        _gradient(draw, 0, 0, w, h, tone["bg_top"], tone["bg_bottom"])
        return img


def _text_outline(draw, text, x, y, font, fill, outline=(0, 0, 0), width=3):
    """텍스트에 외곽선 추가 (밝은 배경 위 가독성)"""
    draw.text((x, y), text, font=font, fill=fill, stroke_width=width, stroke_fill=outline)


def _right_text_outline(draw, text, x_right, y, font, fill, outline=(0, 0, 0), width=3):
    """오른쪽 정렬 + 외곽선 텍스트"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    _text_outline(draw, text, x_right - tw, y, font, fill, outline, width)


# ── 메인 디스패치 ──

def generate_infographic(w: int, h: int, prompt: str, tag: str = "",
                         data: dict | None = None, bg_img: Image.Image | None = None) -> Image.Image:
    """프롬프트 키워드 또는 data.type으로 인포그래픽 생성"""

    # data.type 기반 디스패치 (새 방식)
    if data and "type" in data:
        dispatch = {
            "headline": _draw_headline_visual,
            "numbers": _draw_key_numbers,
            "list": _draw_info_list,
            "quote": _draw_quote_visual,
            "comparison": _draw_comparison,
        }
        fn = dispatch.get(data["type"])
        if fn:
            return fn(w, h, data, bg_img)

    # 기존 prompt 키워드 매칭 (하위 호환)
    p = prompt.lower()
    if any(kw in p for kw in ["ticker", "price table", "stock list"]):
        return _draw_stock_ticker(w, h)
    elif any(kw in p for kw in ["chart", "stock", "market", "trading", "surge"]):
        return _draw_stock_chart(w, h)
    elif any(kw in p for kw in ["semiconductor", "chip", "hbm", "dram"]):
        return _draw_semiconductor(w, h)
    elif any(kw in p for kw in ["investor", "people", "crowd"]):
        return _draw_investor_visual(w, h)
    elif any(kw in p for kw in ["forecast", "target", "prediction"]):
        return _draw_forecast(w, h)
    elif any(kw in p for kw in ["warning", "caution", "risk"]):
        return _draw_warning(w, h)
    else:
        return _draw_generic_news(w, h)


# ── 씬 1: 급등 주식 차트 ──

def _draw_stock_chart(w, h):
    """KOSPI 급등 차트 — 글로우 라인 + 볼륨 바"""
    img = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 배경 그라데이션 + 중앙 빛
    _gradient(draw, 0, 0, w, h, (5, 12, 35), (8, 5, 22))
    _center_glow(draw, w // 2, h // 3, min(w, h), (40, 60, 120))

    # 격자
    for y in range(60, h - 40, 90):
        draw.line([(50, y), (w - 50, y)], fill=(22, 32, 50), width=1)
    for x in range(50, w - 40, 110):
        draw.line([(x, 60), (x, h - 50)], fill=(22, 32, 50), width=1)

    # 차트 포인트 계산
    mx, mb = 65, 130
    chart_w, chart_h = w - mx * 2, h - 250
    pts = []
    for i in range(300):
        t = i / 300
        x = mx + int(t * chart_w)
        if t < 0.55:
            val = t * 0.25 + math.sin(t * 25) * 0.015 + math.sin(t * 7) * 0.03
        else:
            p = (t - 0.55) / 0.45
            val = 0.14 + p ** 1.6 * 0.86
        y = h - mb - int(val * chart_h)
        pts.append((x, y))

    # 차트 아래 채우기 (어두운 빨강)
    fill_pts = list(pts) + [(pts[-1][0], h - mb), (pts[0][0], h - mb)]
    draw.polygon(fill_pts, fill=(25, 6, 8))

    # 볼륨 바 (하단)
    rng = random.Random(42)
    vol_base_y = h - mb + 10
    for i in range(0, len(pts), 4):
        x = pts[i][0]
        vol_h = rng.randint(8, 50)
        bar_color = (80, 25, 25) if rng.random() > 0.3 else (25, 50, 25)
        draw.rectangle([x - 1, vol_base_y, x + 1, vol_base_y + vol_h], fill=bar_color)

    # 차트 라인 글로우
    img = _add_glow(img, lambda d: d.line(pts, fill=(255, 50, 50), width=8), blur_radius=12)
    draw = ImageDraw.Draw(img)

    # 선명한 차트 라인
    draw.line(pts, fill=(255, 70, 70), width=3)

    # 끝점 마커
    lx, ly = pts[-1]
    draw.ellipse([lx - 10, ly - 10, lx + 10, ly + 10], fill=(255, 255, 255))
    draw.ellipse([lx - 6, ly - 6, lx + 6, ly + 6], fill=(255, 70, 70))

    # "KOSPI" 라벨
    f_label = _get_font(32, "Bold")
    draw.text((w // 2 - 80, h // 2 - 160), "KOSPI", font=f_label, fill=(180, 180, 200))

    # "6,022" 대형 수치 글로우
    f_big = _get_font(110, "Black")
    bbox = draw.textbbox((0, 0), "6,022", font=f_big)
    tw = bbox[2] - bbox[0]
    num_x, num_y = (w - tw) // 2, h // 2 - 130
    img = _add_glow(img, lambda d: d.text((num_x, num_y), "6,022", font=f_big, fill=(255, 50, 50)), blur_radius=18)
    draw = ImageDraw.Draw(img)
    draw.text((num_x, num_y), "6,022", font=f_big, fill=(255, 80, 80))

    # "+0.89%" 변동률
    f_pct = _get_font(36, "Bold")
    bbox2 = draw.textbbox((0, 0), "+53.06  (+0.89%)", font=f_pct)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((w - tw2) // 2, num_y + 120), "+53.06  (+0.89%)", font=f_pct, fill=(255, 120, 120))

    return img


# ── 씬 2: 주식 티커 테이블 (신규) ──

def _draw_stock_ticker(w, h):
    """주요 종목 가격표 — 카드 스타일 테이블"""
    img = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    _gradient(draw, 0, 0, w, h, (8, 10, 28), (5, 5, 18))

    stocks = [
        ("KOSPI", "6,022.70", "+53.06", "+0.89%"),
        ("삼성전자", "204,000", "+4,000", "+2.00%"),
        ("SK하이닉스", "1,029,000", "+24,000", "+2.39%"),
        ("현대차", "573,000", "+49,000", "+9.35%"),
        ("기아", "198,300", "+24,300", "+13.97%"),
        ("KOSDAQ", "1,892.45", "+12.33", "+0.66%"),
    ]

    margin = 40
    gap = 10
    row_h = (h - margin * 2 - gap * (len(stocks) - 1)) // len(stocks)
    card_x0, card_x1 = margin, w - margin

    f_name = _get_font(38, "Bold")
    f_price = _get_font(48, "Black")
    f_change = _get_font(26, "Medium")

    for i, (name, price, change, pct) in enumerate(stocks):
        y = margin + i * (row_h + gap)

        # 카드 배경 (첫 번째 행 강조)
        card_fill = (18, 22, 38) if i > 0 else (25, 18, 22)
        card_outline = (35, 45, 65) if i > 0 else (80, 40, 45)
        draw.rounded_rectangle(
            [card_x0, y, card_x1, y + row_h],
            radius=10, fill=card_fill, outline=card_outline, width=1
        )

        # 왼쪽: 종목명
        name_y = y + row_h // 2 - 45
        draw.text((card_x0 + 25, name_y), name, font=f_name, fill=(240, 240, 250))

        # 왼쪽 하단: 변동폭
        change_text = f"{change} ({pct})"
        draw.text((card_x0 + 25, name_y + 50), change_text, font=f_change, fill=(255, 90, 90))

        # 오른쪽: 현재가
        price_y = y + row_h // 2 - 32
        _right_text(draw, price, card_x1 - 25, price_y, f_price, (255, 255, 255))

        # 상승 화살표
        arrow_x = card_x1 - 20
        arrow_y = price_y + 55
        draw.polygon(
            [(arrow_x, arrow_y), (arrow_x - 8, arrow_y + 12), (arrow_x + 8, arrow_y + 12)],
            fill=(255, 70, 70)
        )

    # 첫 행에 글로우
    img = _add_glow(img, lambda d: d.rounded_rectangle(
        [card_x0, margin, card_x1, margin + row_h],
        radius=10, fill=(60, 15, 15)
    ), blur_radius=20)

    return img


# ── 씬 3: 반도체 칩 + 주가 카드 ──

def _draw_semiconductor(w, h):
    """AI 반도체 비주얼 — 칩 + 회로 + 주가 카드"""
    img = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    _gradient(draw, 0, 0, w, h, (5, 8, 28), (2, 5, 18))

    # 회로 패턴 (배경)
    rng = random.Random(42)
    for _ in range(50):
        x, y = rng.randint(0, w), rng.randint(0, h)
        length = rng.randint(40, 250)
        color = (15, 40, 75)
        if rng.choice([True, False]):
            draw.line([(x, y), (x + length, y)], fill=color, width=1)
        else:
            draw.line([(x, y), (x, y + length)], fill=color, width=1)
        # 교차점 노드
        draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(25, 65, 120))

    # 중앙 칩
    cx, cy = w // 2, h // 3
    sz = 170

    # 칩 글로우
    img = _add_glow(img, lambda d: d.rectangle(
        [cx - sz, cy - sz, cx + sz, cy + sz], fill=(30, 70, 140)
    ), blur_radius=25)
    draw = ImageDraw.Draw(img)

    # 칩 본체
    draw.rectangle([cx - sz, cy - sz, cx + sz, cy + sz],
                   fill=(12, 22, 45), outline=(50, 110, 190), width=3)

    # 내부 격자
    inner = sz - 30
    for off in range(-inner, inner + 1, 40):
        draw.line([(cx + off, cy - inner), (cx + off, cy + inner)], fill=(20, 40, 70), width=1)
        draw.line([(cx - inner, cy + off), (cx + inner, cy + off)], fill=(20, 40, 70), width=1)

    # 연결 핀 (상하좌우)
    pin_color = (80, 160, 240)
    for i in range(12):
        off = -sz + int(2 * sz / 13) * (i + 1)
        # 상단
        draw.line([(cx + off, cy - sz), (cx + off, cy - sz - 30)], fill=pin_color, width=2)
        draw.ellipse([cx + off - 3, cy - sz - 33, cx + off + 3, cy - sz - 27], fill=pin_color)
        # 하단
        draw.line([(cx + off, cy + sz), (cx + off, cy + sz + 30)], fill=pin_color, width=2)
        draw.ellipse([cx + off - 3, cy + sz + 27, cx + off + 3, cy + sz + 33], fill=pin_color)
    for i in range(12):
        off = -sz + int(2 * sz / 13) * (i + 1)
        # 좌
        draw.line([(cx - sz, cy + off), (cx - sz - 30, cy + off)], fill=pin_color, width=2)
        # 우
        draw.line([(cx + sz, cy + off), (cx + sz + 30, cy + off)], fill=pin_color, width=2)

    # 칩 텍스트
    f_chip = _get_font(50, "Black")
    f_sub = _get_font(30, "Medium")
    bbox = draw.textbbox((0, 0), "AI", font=f_chip)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) // 2, cy - 35), "AI", font=f_chip, fill=(120, 200, 255))
    bbox2 = draw.textbbox((0, 0), "HBM · DRAM", font=f_sub)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((w - tw2) // 2, cy + 20), "HBM · DRAM", font=f_sub, fill=(80, 160, 220))

    # 하단 주가 카드 2개
    card_y = h - 320
    card_w = (w - 80 - 20) // 2  # 2개 카드 + 간격
    cards = [
        ("삼성전자", "204,000", "+33.78%"),
        ("SK하이닉스", "1,029,000", "+35.81%"),
    ]
    for i, (name, price, pct) in enumerate(cards):
        cx0 = 40 + i * (card_w + 20)
        draw.rounded_rectangle(
            [cx0, card_y, cx0 + card_w, card_y + 200],
            radius=12, fill=(15, 22, 42), outline=(40, 65, 110), width=1
        )
        f_cn = _get_font(28, "Medium")
        f_cp = _get_font(44, "Black")
        f_cc = _get_font(24, "Medium")
        draw.text((cx0 + 20, card_y + 20), name, font=f_cn, fill=(180, 190, 210))
        draw.text((cx0 + 20, card_y + 65), price, font=f_cp, fill=(255, 255, 255))
        draw.text((cx0 + 20, card_y + 130), pct, font=f_cc, fill=(255, 90, 90))

    return img


# ── 씬 4: 투자자 파이차트 ──

def _draw_investor_visual(w, h):
    """투자자별 순매수 — 큰 도넛 차트 + 범례"""
    img = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    _gradient(draw, 0, 0, w, h, (12, 6, 22), (5, 8, 20))
    _center_glow(draw, w // 2, h // 3, 500, (60, 20, 30))

    # 도넛 차트
    cx, cy = w // 2, h // 3 + 20
    r = 210
    inner_r = 80

    # 데이터: 개인 65%, 외국인 22%, 기관 13%
    segments = [
        (-90, -90 + 234, (220, 55, 55)),   # 개인 (65%)
        (-90 + 234, -90 + 313, (50, 80, 190)),  # 외국인 (22%)
        (-90 + 313, -90 + 360, (90, 95, 110)),  # 기관 (13%)
    ]

    # 파이 글로우 (빨간 세그먼트)
    img = _add_glow(img, lambda d: d.pieslice(
        [cx - r, cy - r, cx + r, cy + r], -90, -90 + 234, fill=(180, 30, 30)
    ), blur_radius=20)
    draw = ImageDraw.Draw(img)

    for start, end, color in segments:
        draw.pieslice([cx - r, cy - r, cx + r, cy + r], start, end, fill=color)

    # 내부 원 (도넛 효과)
    draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=(12, 12, 22))

    # 중앙 텍스트
    f_center = _get_font(28, "Bold")
    label = "순매수"
    bbox = draw.textbbox((0, 0), label, font=f_center)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) // 2, cy - 15), label, font=f_center, fill=(200, 200, 210))

    # 범례 (차트 아래)
    legend_y = cy + r + 60
    items = [
        ("●  개인", "+8,291억", "65%", (220, 55, 55)),
        ("●  외국인", "-7,356억", "22%", (50, 80, 190)),
        ("●  기관", "-5,372억", "13%", (90, 95, 110)),
    ]
    f_legend = _get_font(34, "Bold")
    f_val = _get_font(34, "Black")
    f_pct = _get_font(28, "Medium")

    for i, (label, val, pct, color) in enumerate(items):
        y = legend_y + i * 75

        # 카드 배경
        draw.rounded_rectangle(
            [60, y - 5, w - 60, y + 55],
            radius=8, fill=(18, 20, 32), outline=(30, 35, 50), width=1
        )

        draw.text((85, y + 5), label, font=f_legend, fill=color)
        _right_text(draw, val, w - 200, y + 5, f_val, color)
        _right_text(draw, pct, w - 85, y + 8, f_pct, (150, 150, 165))

    return img


# ── 씬 5: 전문가 전망 바 차트 ──

def _draw_forecast(w, h):
    """증권사 목표가 바 차트 — 현재 지수 기준선 포함"""
    img = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    _gradient(draw, 0, 0, w, h, (8, 15, 10), (3, 5, 15))

    targets = [
        ("노무라", 8000, (255, 80, 80)),
        ("하나증권", 7870, (255, 110, 60)),
        ("KB증권", 7500, (255, 150, 40)),
        ("키움증권", 7300, (255, 190, 50)),
        ("한국투자", 7250, (210, 210, 70)),
    ]

    y_start = 60
    bar_gap = (h - y_start - 80) // (len(targets) + 1)
    max_val = 8500
    bar_x = 220
    max_bar_w = w - bar_x - 80

    f_name = _get_font(32, "Bold")
    f_val = _get_font(36, "Black")

    # "현재 6,000" 기준선
    current_val = 6000
    current_x = bar_x + int(current_val / max_val * max_bar_w)
    draw.line([(current_x, y_start - 10), (current_x, h - 40)], fill=(80, 200, 120), width=2)
    f_cur = _get_font(24, "Medium")
    draw.text((current_x - 40, y_start - 35), "현재 6,000", font=f_cur, fill=(80, 200, 120))

    for i, (name, val, color) in enumerate(targets):
        y = y_start + (i + 1) * bar_gap
        bw = int(val / max_val * max_bar_w)

        # 바 배경 (어두운)
        draw.rounded_rectangle(
            [bar_x, y + 8, bar_x + max_bar_w, y + 55],
            radius=6, fill=(15, 18, 25)
        )

        # 바 (그라데이션 시뮬레이션)
        draw.rounded_rectangle(
            [bar_x, y + 8, bar_x + bw, y + 55],
            radius=6, fill=color
        )

        # 바 위에 하이라이트
        highlight = tuple(min(255, c + 50) for c in color)
        draw.line([(bar_x + 6, y + 12), (bar_x + bw - 6, y + 12)], fill=highlight, width=1)

        # 증권사명
        draw.text((25, y + 14), name, font=f_name, fill=(240, 240, 250))

        # 목표가
        val_text = f"{val:,}"
        _right_text(draw, val_text, w - 30, y + 10, f_val, (255, 255, 255))

    # 바 글로우 (첫 번째 바)
    first_y = y_start + bar_gap
    first_bw = int(targets[0][1] / max_val * max_bar_w)
    img = _add_glow(img, lambda d: d.rounded_rectangle(
        [bar_x, first_y + 8, bar_x + first_bw, first_y + 55],
        radius=6, fill=(120, 30, 30)
    ), blur_radius=15)

    return img


# ── 씬 6: 경고 화면 ──

def _draw_warning(w, h):
    """시장 과열 경고 — 삼각형 + 불릿 포인트"""
    img = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    _gradient(draw, 0, 0, w, h, (30, 10, 8), (12, 5, 10))

    # 상단 빨간 빛
    _center_glow(draw, w // 2, h // 5, 400, (100, 20, 10))

    # 경고 삼각형
    cx, cy = w // 2, h // 4 + 20
    sz = 150
    triangle = [
        (cx, cy - sz),
        (cx - int(sz * 0.95), cy + int(sz * 0.6)),
        (cx + int(sz * 0.95), cy + int(sz * 0.6))
    ]

    # 삼각형 글로우
    img = _add_glow(img, lambda d: d.polygon(triangle, fill=(200, 140, 0)), blur_radius=25)
    draw = ImageDraw.Draw(img)

    draw.polygon(triangle, fill=(255, 190, 0))

    # 느낌표
    f_bang = _get_font(100, "Black")
    bbox = draw.textbbox((0, 0), "!", font=f_bang)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw // 2, cy - sz + 40), "!", font=f_bang, fill=(35, 15, 0))

    # 불릿 포인트 목록
    items = [
        ("🔴", "사이드카 연이어 발동"),
        ("🟡", "투자자예탁금 111조원 역대 최대"),
        ("⚫", "신용거래융자 31.7조원"),
    ]

    bullet_y = cy + int(sz * 0.6) + 80
    f_bullet = _get_font(32, "Bold")

    for i, (dot, text) in enumerate(items):
        y = bullet_y + i * 80

        # 카드 배경
        draw.rounded_rectangle(
            [50, y - 8, w - 50, y + 52],
            radius=8, fill=(20, 12, 14), outline=(50, 25, 28), width=1
        )

        # 상태 원
        dot_colors = [(220, 50, 50), (220, 180, 50), (80, 80, 90)]
        draw.ellipse([75, y + 10, 95, y + 30], fill=dot_colors[i])

        draw.text((115, y + 3), text, font=f_bullet, fill=(230, 230, 235))

    return img


# ── 일반 뉴스 배경 ──

def _draw_generic_news(w, h):
    """일반 뉴스 배경"""
    img = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    _gradient(draw, 0, 0, w, h, (10, 15, 35), (5, 5, 20))
    _center_glow(draw, w // 2, h // 2, 500, (30, 45, 80))

    return img


# ═══════════════════════════════════════════
# 범용 데이터 기반 인포그래픽 (어떤 뉴스에도 대응)
# ═══════════════════════════════════════════


def _draw_headline_visual(w, h, data, bg_img=None):
    """대형 헤드라인 텍스트 (5개 스타일)"""
    accent = tuple(data.get("accent_color", [255, 60, 60]))
    tone = _get_tone(data)
    transparent = bg_img is not None

    img = _make_base(w, h, tone, bg_img)
    draw = ImageDraw.Draw(img)
    if not transparent:
        _center_glow(draw, w // 2, h // 3, min(w, h), tone["glow"])

    text = data.get("text", "")
    lines = text.split("\n")
    sub_text = data.get("sub_text", "")
    max_len = max(len(l) for l in lines) if lines else 1

    def _render_sub(draw, sub_text, center_x, y, transparent, accent):
        if not sub_text:
            return
        f_sub = _get_font(34, "Medium")
        bbox = draw.textbbox((0, 0), sub_text, font=f_sub)
        tw = bbox[2] - bbox[0]
        sx = center_x - tw // 2
        if transparent:
            _text_outline(draw, sub_text, sx, y, f_sub, accent, (0, 0, 0), 3)
        else:
            draw.text((sx, y), sub_text, font=f_sub, fill=accent)

    if _card_style == 0:
        # Classic: 중앙 대형 텍스트 + 글로우
        font_size = min(100, max(60, w // max(max_len, 1) - 10))
        f_main = _get_font(font_size, "Black")
        total_line_h = len(lines) * (font_size + 20)
        start_y = (h - total_line_h) // 2 - 40

        if not transparent:
            def glow_fn(gd):
                for i, line in enumerate(lines):
                    bbox = gd.textbbox((0, 0), line, font=f_main)
                    tw = bbox[2] - bbox[0]
                    gd.text(((w - tw) // 2, start_y + i * (font_size + 20)), line, font=f_main, fill=accent)
            img = _add_glow(img, glow_fn, blur_radius=20)
            draw = ImageDraw.Draw(img)

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=f_main)
            tw = bbox[2] - bbox[0]
            x, y = (w - tw) // 2, start_y + i * (font_size + 20)
            if transparent:
                _text_outline(draw, line, x, y, f_main, (255, 255, 255), (0, 0, 0), 5)
            else:
                draw.text((x, y), line, font=f_main, fill=(255, 255, 255))

        _render_sub(draw, sub_text, w // 2, start_y + total_line_h + 30, transparent, accent)

    elif _card_style == 1:
        # Circle: 대형 원 안에 텍스트
        cx, cy = w // 2, h // 2 - 30
        radius = min(w, h) // 2 - 60
        circle_bg = (*accent[:3], 35) if transparent else tuple(c // 8 for c in accent)
        circle_ol = (*accent[:3], 120) if transparent else accent
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     fill=circle_bg, outline=circle_ol, width=4)
        inner_r = radius - 30
        inner_ol = (*accent[:3], 60) if transparent else tuple(c // 3 for c in accent)
        draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
                     outline=inner_ol, width=2)

        font_size = min(80, max(50, (radius * 2) // max(max_len + 1, 1)))
        f_main = _get_font(font_size, "Black")
        total_line_h = len(lines) * (font_size + 15)
        start_y = cy - total_line_h // 2
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=f_main)
            tw = bbox[2] - bbox[0]
            x, y = (w - tw) // 2, start_y + i * (font_size + 15)
            if transparent:
                _text_outline(draw, line, x, y, f_main, (255, 255, 255), (0, 0, 0), 5)
            else:
                draw.text((x, y), line, font=f_main, fill=(255, 255, 255))
        _render_sub(draw, sub_text, w // 2, cy + radius + 25, transparent, accent)

    elif _card_style == 2:
        # Banner: 가로 풀폭 배너 바
        font_size = min(90, max(55, w // max(max_len, 1) - 10))
        f_main = _get_font(font_size, "Black")
        total_line_h = len(lines) * (font_size + 30)
        banner_h = total_line_h + 60
        banner_y = (h - banner_h) // 2 - 20
        banner_bg = (*accent[:3], 50) if transparent else tuple(c // 6 for c in accent)
        draw.rectangle([0, banner_y, w, banner_y + banner_h], fill=banner_bg)
        draw.rectangle([0, banner_y, w, banner_y + 5], fill=accent)
        draw.rectangle([0, banner_y + banner_h - 5, w, banner_y + banner_h], fill=accent)

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=f_main)
            tw = bbox[2] - bbox[0]
            x, y = (w - tw) // 2, banner_y + 30 + i * (font_size + 30)
            if transparent:
                _text_outline(draw, line, x, y, f_main, (255, 255, 255), (0, 0, 0), 5)
            else:
                draw.text((x, y), line, font=f_main, fill=(255, 255, 255))
        _render_sub(draw, sub_text, w // 2, banner_y + banner_h + 25, transparent, accent)

    elif _card_style == 3:
        # Timeline: 왼쪽 수직선 + 큰 노드 + 텍스트
        font_size = min(85, max(55, w // max(max_len + 2, 1)))
        f_main = _get_font(font_size, "Black")
        total_line_h = len(lines) * (font_size + 20)
        start_y = (h - total_line_h) // 2 - 30
        line_x = 80
        line_color = (*accent[:3], 100) if transparent else tuple(c // 2 for c in accent)
        draw.rectangle([line_x - 2, start_y - 40, line_x + 2, start_y + total_line_h + 60], fill=line_color)
        node_y = start_y + total_line_h // 2
        draw.ellipse([line_x - 18, node_y - 18, line_x + 18, node_y + 18], fill=accent)
        draw.ellipse([line_x - 8, node_y - 8, line_x + 8, node_y + 8], fill=(255, 255, 255))

        text_x = line_x + 50
        for i, line in enumerate(lines):
            y = start_y + i * (font_size + 20)
            if transparent:
                _text_outline(draw, line, text_x, y, f_main, (255, 255, 255), (0, 0, 0), 5)
            else:
                draw.text((text_x, y), line, font=f_main, fill=(255, 255, 255))
        if sub_text:
            f_sub = _get_font(32, "Medium")
            if transparent:
                _text_outline(draw, sub_text, text_x, start_y + total_line_h + 30, f_sub, accent, (0, 0, 0), 3)
            else:
                draw.text((text_x, start_y + total_line_h + 30), sub_text, font=f_sub, fill=accent)

    elif _card_style == 4:
        # Grid: 격자 프레임 + 꼭짓점 L자 장식
        font_size = min(90, max(55, w // max(max_len, 1) - 10))
        f_main = _get_font(font_size, "Black")
        total_line_h = len(lines) * (font_size + 20)
        frame_pad = 50
        frame_x0 = 40
        frame_y0 = (h - total_line_h) // 2 - frame_pad - 20
        frame_x1 = w - 40
        frame_y1 = (h + total_line_h) // 2 + frame_pad - 20
        frame_bg = (*tone["card_bg"], 150) if transparent else tone["card_bg"]
        draw.rectangle([frame_x0, frame_y0, frame_x1, frame_y1], fill=frame_bg)
        corner_len = 50
        for (cx, cy, dx, dy) in [
            (frame_x0, frame_y0, 1, 1), (frame_x1, frame_y0, -1, 1),
            (frame_x0, frame_y1, 1, -1), (frame_x1, frame_y1, -1, -1),
        ]:
            draw.line([(cx, cy), (cx + corner_len * dx, cy)], fill=accent, width=4)
            draw.line([(cx, cy), (cx, cy + corner_len * dy)], fill=accent, width=4)

        start_y = (h - total_line_h) // 2 - 20
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=f_main)
            tw = bbox[2] - bbox[0]
            x, y = (w - tw) // 2, start_y + i * (font_size + 20)
            if transparent:
                _text_outline(draw, line, x, y, f_main, (255, 255, 255), (0, 0, 0), 5)
            else:
                draw.text((x, y), line, font=f_main, fill=(255, 255, 255))
        _render_sub(draw, sub_text, w // 2, frame_y1 + 25, transparent, accent)

    return img


def _draw_key_numbers(w, h, data, bg_img=None):
    """핵심 수치 강조 (5개 스타일)"""
    accent = tuple(data.get("accent_color", [80, 160, 255]))
    items = data.get("items", [])
    tone = _get_tone(data)
    transparent = bg_img is not None

    img = _make_base(w, h, tone, bg_img)
    draw = ImageDraw.Draw(img)
    if not transparent:
        _center_glow(draw, w // 2, h // 3, 500, tone["glow"])

    n = len(items)
    if n == 0:
        return img
    margin = 50

    if _card_style == 0:
        # Classic: 둥근 사각형 카드 세로 배치
        gap = 30
        card_h = min(240, (h - margin * 2 - gap * (n - 1)) // n)
        val_size = min(80, card_h - 70)
        f_label = _get_font(30, "Medium")
        f_val = _get_font(val_size, "Black")
        total_block = n * card_h + (n - 1) * gap
        start_y = (h - total_block) // 2
        card_bg = (*tone["card_bg"], 180) if transparent else tone["card_bg"]
        card_ol = (*tone["card_outline"], 200) if transparent else tone["card_outline"]

        for i, item in enumerate(items):
            y = start_y + i * (card_h + gap)
            color = tuple(item.get("color", list(accent)))
            draw.rounded_rectangle([margin, y, w - margin, y + card_h],
                                   radius=14, fill=card_bg, outline=card_ol, width=2)
            label_text = item.get("label", "")
            if transparent:
                _text_outline(draw, label_text, margin + 25, y + 18, f_label, (200, 210, 230), (0, 0, 0), 2)
            else:
                draw.text((margin + 25, y + 18), label_text, font=f_label, fill=(160, 170, 190))
            val_text = item.get("value", "")
            bbox = draw.textbbox((0, 0), val_text, font=f_val)
            tw = bbox[2] - bbox[0]
            if transparent:
                _text_outline(draw, val_text, (w - tw) // 2, y + card_h - val_size - 20, f_val, color, (0, 0, 0), 3)
            else:
                draw.text(((w - tw) // 2, y + card_h - val_size - 20), val_text, font=f_val, fill=color)

        if not transparent:
            first_color = tuple(items[0].get("color", list(accent)))
            img = _add_glow(img, lambda d: d.rounded_rectangle(
                [margin, start_y, w - margin, start_y + card_h],
                radius=14, fill=tuple(c // 4 for c in first_color)
            ), blur_radius=18)

    elif _card_style == 1:
        # Circle: 각 수치를 원 안에 배치
        circle_r = min(160, (h - 60) // (n + 1) // 2)
        gap = circle_r * 2 + 30
        total_h = n * gap - 30
        start_y = (h - total_h) // 2 + circle_r

        for i, item in enumerate(items):
            cy = start_y + i * gap
            cx = w // 2
            color = tuple(item.get("color", list(accent)))
            circle_bg = (*color[:3], 30) if transparent else tuple(c // 8 for c in color)
            circle_ol = (*color[:3], 150) if transparent else color
            draw.ellipse([cx - circle_r, cy - circle_r, cx + circle_r, cy + circle_r],
                         fill=circle_bg, outline=circle_ol, width=3)
            val_text = item.get("value", "")
            val_size = min(55, circle_r - 20)
            f_val = _get_font(val_size, "Black")
            bbox = draw.textbbox((0, 0), val_text, font=f_val)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if transparent:
                _text_outline(draw, val_text, cx - tw // 2, cy - th // 2 - 10, f_val, color, (0, 0, 0), 3)
            else:
                draw.text((cx - tw // 2, cy - th // 2 - 10), val_text, font=f_val, fill=color)
            label_text = item.get("label", "")
            f_label = _get_font(26, "Medium")
            bbox2 = draw.textbbox((0, 0), label_text, font=f_label)
            tw2 = bbox2[2] - bbox2[0]
            if transparent:
                _text_outline(draw, label_text, cx - tw2 // 2, cy + th // 2 + 5, f_label, (200, 210, 230), (0, 0, 0), 2)
            else:
                draw.text((cx - tw2 // 2, cy + th // 2 + 5), label_text, font=f_label, fill=(180, 190, 210))

    elif _card_style == 2:
        # Banner: 풀폭 가로 배너 바
        bar_h = min(150, (h - 40) // n - 20)
        gap = bar_h + 20
        total_h = n * gap - 20
        start_y = (h - total_h) // 2

        for i, item in enumerate(items):
            y = start_y + i * gap
            color = tuple(item.get("color", list(accent)))
            bar_bg = (*color[:3], 40) if transparent else tuple(c // 7 for c in color)
            draw.rectangle([0, y, w, y + bar_h], fill=bar_bg)
            draw.rectangle([0, y, 8, y + bar_h], fill=color)
            f_label = _get_font(28, "Medium")
            label_text = item.get("label", "")
            if transparent:
                _text_outline(draw, label_text, 30, y + 15, f_label, (200, 210, 230), (0, 0, 0), 2)
            else:
                draw.text((30, y + 15), label_text, font=f_label, fill=(160, 170, 190))
            val_text = item.get("value", "")
            val_size = min(65, bar_h - 50)
            f_val = _get_font(val_size, "Black")
            if transparent:
                _right_text_outline(draw, val_text, w - 30, y + bar_h - val_size - 20, f_val, color, (0, 0, 0), 3)
            else:
                _right_text(draw, val_text, w - 30, y + bar_h - val_size - 20, f_val, color)

    elif _card_style == 3:
        # Timeline: 수직 타임라인 + 노드에 수치
        line_x = 100
        gap = min(250, (h - 80) // n)
        total_h = n * gap
        start_y = (h - total_h) // 2 + 30
        line_color = (*accent[:3], 80) if transparent else tuple(c // 3 for c in accent)
        draw.rectangle([line_x - 2, start_y - 30, line_x + 2, start_y + total_h - 30], fill=line_color)

        for i, item in enumerate(items):
            node_y = start_y + i * gap
            color = tuple(item.get("color", list(accent)))
            draw.ellipse([line_x - 14, node_y - 14, line_x + 14, node_y + 14], fill=color)
            draw.ellipse([line_x - 6, node_y - 6, line_x + 6, node_y + 6], fill=(255, 255, 255))
            conn_color = (*color[:3], 60) if transparent else tuple(c // 4 for c in color)
            draw.line([(line_x + 14, node_y), (line_x + 50, node_y)], fill=conn_color, width=2)
            f_label = _get_font(28, "Medium")
            label_text = item.get("label", "")
            if transparent:
                _text_outline(draw, label_text, line_x + 55, node_y - 35, f_label, (200, 210, 230), (0, 0, 0), 2)
            else:
                draw.text((line_x + 55, node_y - 35), label_text, font=f_label, fill=(180, 190, 210))
            val_text = item.get("value", "")
            val_size = min(60, gap - 80)
            f_val = _get_font(val_size, "Black")
            if transparent:
                _text_outline(draw, val_text, line_x + 55, node_y + 5, f_val, color, (0, 0, 0), 3)
            else:
                draw.text((line_x + 55, node_y + 5), val_text, font=f_val, fill=color)

    elif _card_style == 4:
        # Grid: 세로 타일 배치
        pad = 20
        tile_w = w - margin * 2
        tile_h = min(280, (h - margin * 2 - pad * (n - 1)) // n)
        total_h = n * tile_h + (n - 1) * pad
        base_x = margin
        base_y = (h - total_h) // 2

        for slot in range(n):
            tx = base_x
            ty = base_y + slot * (tile_h + pad)

            item = items[slot]
            color = tuple(item.get("color", list(accent)))
            tile_bg = (*tone["card_bg"], 180) if transparent else tone["card_bg"]
            tile_ol = (*color[:3], 150) if transparent else color
            draw.rounded_rectangle([tx, ty, tx + tile_w, ty + tile_h],
                                   radius=10, fill=tile_bg, outline=tile_ol, width=2)
            draw.rectangle([tx, ty, tx + tile_w, ty + 6], fill=color)

            # 콘텐츠 높이 계산 (라벨 + 수치 + unit) → 상하 가운데 정렬
            f_label = _get_font(24, "Medium")
            f_val = _get_font(min(50, tile_h - 80), "Black")
            label_text = item.get("label", "")
            val_text = item.get("value", "")
            unit_text = item.get("unit", "")

            label_bbox = draw.textbbox((0, 0), label_text, font=f_label)
            label_h = label_bbox[3] - label_bbox[1]
            val_bbox = draw.textbbox((0, 0), val_text, font=f_val)
            val_h = val_bbox[3] - val_bbox[1]
            val_tw = val_bbox[2] - val_bbox[0]
            unit_h = 0
            if unit_text:
                f_unit = _get_font(20, "Regular")
                unit_bbox = draw.textbbox((0, 0), unit_text, font=f_unit)
                unit_h = unit_bbox[3] - unit_bbox[1]

            content_gap = 12
            content_h = label_h + content_gap + val_h + (content_gap + unit_h if unit_text else 0)
            top_pad = 6  # 상단 컬러 바 높이
            content_y = ty + top_pad + (tile_h - top_pad - content_h) // 2

            if transparent:
                _text_outline(draw, label_text, tx + 15, content_y, f_label, (200, 210, 230), (0, 0, 0), 2)
            else:
                draw.text((tx + 15, content_y), label_text, font=f_label, fill=(160, 170, 190))

            val_y = content_y + label_h + content_gap
            if transparent:
                _text_outline(draw, val_text, tx + (tile_w - val_tw) // 2, val_y, f_val, color, (0, 0, 0), 3)
            else:
                draw.text((tx + (tile_w - val_tw) // 2, val_y), val_text, font=f_val, fill=color)

            if unit_text:
                unit_bbox2 = draw.textbbox((0, 0), unit_text, font=f_unit)
                unit_tw = unit_bbox2[2] - unit_bbox2[0]
                unit_y = val_y + val_h + content_gap
                if transparent:
                    _text_outline(draw, unit_text, tx + (tile_w - unit_tw) // 2, unit_y, f_unit, (150, 160, 180), (0, 0, 0), 2)
                else:
                    draw.text((tx + (tile_w - unit_tw) // 2, unit_y), unit_text, font=f_unit, fill=(120, 130, 150))

    return img


def _draw_info_list(w, h, data, bg_img=None):
    """불릿 리스트 (5개 스타일)"""
    accent = tuple(data.get("accent_color", [60, 120, 255]))
    items = data.get("items", [])
    title = data.get("title", "")
    tone = _get_tone(data)
    transparent = bg_img is not None

    icon_colors = {
        "red": (220, 55, 55), "yellow": (220, 180, 50),
        "green": (60, 190, 100), "blue": (60, 120, 255), "gray": (100, 105, 120),
    }

    img = _make_base(w, h, tone, bg_img)
    draw = ImageDraw.Draw(img)

    margin = 50
    n = len(items)
    if n == 0:
        return img

    def _draw_title(draw, title, x, y, transparent, accent):
        if not title:
            return
        f_title = _get_font(38, "Bold")
        if transparent:
            _text_outline(draw, title, x, y, f_title, accent, (0, 0, 0), 3)
        else:
            draw.text((x, y), title, font=f_title, fill=accent)

    if _card_style == 0:
        # Classic: 둥근 사각형 카드 + 상태 원
        gap = 15
        title_h = 70 if title else 0
        card_h = min(85, (h - title_h - margin * 2 - gap * (n - 1)) // max(n, 1))
        total_block_h = title_h + n * card_h + (n - 1) * gap
        y_offset = (h - total_block_h) // 2
        _draw_title(draw, title, margin + 10, y_offset, transparent, accent)
        y_offset += title_h
        f_text = _get_font(min(34, card_h - 30), "Bold")
        card_bg = (*tone["card_bg"], 180) if transparent else tone["card_bg"]
        card_ol = (*tone["card_outline"], 200) if transparent else tone["card_outline"]

        for i, item in enumerate(items):
            y = y_offset + i * (card_h + gap)
            icon = icon_colors.get(item.get("icon", "blue"), (60, 120, 255))
            draw.rounded_rectangle([margin, y, w - margin, y + card_h],
                                   radius=10, fill=card_bg, outline=card_ol, width=2)
            dot_x = margin + 20
            dot_y = y + card_h // 2
            draw.ellipse([dot_x, dot_y - 10, dot_x + 20, dot_y + 10], fill=icon)
            item_text = item.get("text", "")
            if transparent:
                _text_outline(draw, item_text, dot_x + 35, y + (card_h - 34) // 2, f_text, (240, 240, 250), (0, 0, 0), 2)
            else:
                draw.text((dot_x + 35, y + (card_h - 34) // 2), item_text, font=f_text, fill=(230, 230, 240))

        if not transparent:
            img = _add_glow(img, lambda d: d.rounded_rectangle(
                [margin, y_offset, w - margin, y_offset + card_h],
                radius=10, fill=tuple(c // 5 for c in accent)
            ), blur_radius=15)

    elif _card_style == 1:
        # Circle: 번호 원 + 텍스트
        title_h = 70 if title else 0
        gap = min(120, (h - title_h - margin * 2) // n)
        total_h = title_h + n * gap
        y_offset = (h - total_h) // 2
        _draw_title(draw, title, margin + 10, y_offset, transparent, accent)
        y_offset += title_h
        f_text = _get_font(32, "Bold")

        for i, item in enumerate(items):
            y = y_offset + i * gap
            icon = icon_colors.get(item.get("icon", "blue"), (60, 120, 255))
            cx, cy = margin + 40, y + gap // 2
            r = 28
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=icon)
            f_num = _get_font(28, "Black")
            num_text = str(i + 1)
            bbox = draw.textbbox((0, 0), num_text, font=f_num)
            tw = bbox[2] - bbox[0]
            draw.text((cx - tw // 2, cy - 18), num_text, font=f_num, fill=(255, 255, 255))
            item_text = item.get("text", "")
            if transparent:
                _text_outline(draw, item_text, cx + r + 25, cy - 18, f_text, (240, 240, 250), (0, 0, 0), 2)
            else:
                draw.text((cx + r + 25, cy - 18), item_text, font=f_text, fill=(230, 230, 240))

    elif _card_style == 2:
        # Banner: 풀폭 가로 배너 스트립
        title_h = 70 if title else 0
        bar_h = min(90, (h - title_h - 40) // n - 15)
        gap = bar_h + 15
        total_h = title_h + n * gap - 15
        y_offset = (h - total_h) // 2
        _draw_title(draw, title, 30, y_offset, transparent, accent)
        y_offset += title_h
        f_text = _get_font(min(32, bar_h - 25), "Bold")

        for i, item in enumerate(items):
            y = y_offset + i * gap
            icon = icon_colors.get(item.get("icon", "blue"), (60, 120, 255))
            bar_bg = (*icon[:3], 35) if transparent else tuple(c // 8 for c in icon)
            draw.rectangle([0, y, w, y + bar_h], fill=bar_bg)
            draw.rectangle([0, y, 6, y + bar_h], fill=icon)
            item_text = item.get("text", "")
            if transparent:
                _text_outline(draw, item_text, 30, y + (bar_h - 32) // 2, f_text, (240, 240, 250), (0, 0, 0), 2)
            else:
                draw.text((30, y + (bar_h - 32) // 2), item_text, font=f_text, fill=(230, 230, 240))

    elif _card_style == 3:
        # Timeline: 수직 타임라인 + 노드
        title_h = 70 if title else 0
        line_x = 80
        gap = min(150, (h - title_h - 80) // n)
        total_h = title_h + n * gap
        y_offset = (h - total_h) // 2
        _draw_title(draw, title, line_x + 40, y_offset, transparent, accent)
        y_offset += title_h

        line_color = (*accent[:3], 80) if transparent else tuple(c // 3 for c in accent)
        draw.rectangle([line_x - 2, y_offset, line_x + 2, y_offset + n * gap - 20], fill=line_color)
        f_text = _get_font(30, "Bold")

        for i, item in enumerate(items):
            node_y = y_offset + i * gap + gap // 2
            icon = icon_colors.get(item.get("icon", "blue"), (60, 120, 255))
            draw.ellipse([line_x - 12, node_y - 12, line_x + 12, node_y + 12], fill=icon)
            draw.ellipse([line_x - 5, node_y - 5, line_x + 5, node_y + 5], fill=(255, 255, 255))
            item_text = item.get("text", "")
            if transparent:
                _text_outline(draw, item_text, line_x + 35, node_y - 18, f_text, (240, 240, 250), (0, 0, 0), 2)
            else:
                draw.text((line_x + 35, node_y - 18), item_text, font=f_text, fill=(230, 230, 240))

    elif _card_style == 4:
        # Grid: 세로 타일
        title_h = 70 if title else 0
        pad = 15
        tile_w = w - margin * 2
        tile_h = min(180, (h - title_h - margin * 2 - pad * (n - 1)) // n)
        total_h_block = n * tile_h + (n - 1) * pad
        base_x = margin
        y_offset = (h - title_h - total_h_block) // 2
        _draw_title(draw, title, base_x, y_offset, transparent, accent)
        y_offset += title_h

        f_text = _get_font(min(28, tile_h - 40), "Bold")
        for slot in range(n):
            tx = base_x
            ty = y_offset + slot * (tile_h + pad)
            item = items[slot]
            icon = icon_colors.get(item.get("icon", "blue"), (60, 120, 255))
            tile_bg = (*tone["card_bg"], 180) if transparent else tone["card_bg"]
            draw.rounded_rectangle([tx, ty, tx + tile_w, ty + tile_h],
                                   radius=10, fill=tile_bg, outline=(*icon[:3], 120) if transparent else icon, width=2)
            draw.rectangle([tx, ty, tx + tile_w, ty + 5], fill=icon)
            item_text = item.get("text", "")
            # 텍스트 높이 계산 → 상하 가운데 정렬
            text_bbox = draw.textbbox((0, 0), item_text, font=f_text)
            text_h = text_bbox[3] - text_bbox[1]
            max_chars = max(1, (tile_w - 30) // 20)
            top_pad = 5
            if len(item_text) > max_chars:
                line1 = item_text[:max_chars]
                line2 = item_text[max_chars:]
                total_text_h = text_h * 2 + 8
                text_y = ty + top_pad + (tile_h - top_pad - total_text_h) // 2
                if transparent:
                    _text_outline(draw, line1, tx + 15, text_y, f_text, (240, 240, 250), (0, 0, 0), 2)
                    _text_outline(draw, line2, tx + 15, text_y + text_h + 8, f_text, (240, 240, 250), (0, 0, 0), 2)
                else:
                    draw.text((tx + 15, text_y), line1, font=f_text, fill=(230, 230, 240))
                    draw.text((tx + 15, text_y + text_h + 8), line2, font=f_text, fill=(230, 230, 240))
            else:
                text_y = ty + top_pad + (tile_h - top_pad - text_h) // 2
                if transparent:
                    _text_outline(draw, item_text, tx + 15, text_y, f_text, (240, 240, 250), (0, 0, 0), 2)
                else:
                    draw.text((tx + 15, text_y), item_text, font=f_text, fill=(230, 230, 240))

    return img


def _draw_quote_visual(w, h, data, bg_img=None):
    """인용문 + 화자 정보 (5개 스타일)"""
    accent = tuple(data.get("accent_color", [100, 180, 255]))
    tone = _get_tone(data)
    transparent = bg_img is not None

    img = _make_base(w, h, tone, bg_img)
    draw = ImageDraw.Draw(img)
    if not transparent:
        _center_glow(draw, 80, h // 3, 400, tone["glow"])

    text = data.get("text", "")
    lines = text.split("\n")
    speaker = data.get("speaker", data.get("author", ""))
    affiliation = data.get("affiliation", "")
    max_len = max(len(l) for l in lines) if lines else 1
    font_size = min(48, max(34, w // max(max_len + 2, 1)))
    line_gap = font_size + 18
    total_text_h = len(lines) * line_gap

    def _render_speaker(draw, text_x, speaker_y, transparent, accent):
        if not speaker:
            return
        f_speaker = _get_font(32, "Bold")
        sp_text = f"— {speaker}"
        if transparent:
            _text_outline(draw, sp_text, text_x, speaker_y, f_speaker, accent, (0, 0, 0), 2)
        else:
            draw.text((text_x, speaker_y), sp_text, font=f_speaker, fill=accent)
        if affiliation:
            f_aff = _get_font(28, "Regular")
            bbox = draw.textbbox((0, 0), sp_text, font=f_speaker)
            sw = bbox[2] - bbox[0]
            aff_text = f"| {affiliation}"
            if transparent:
                _text_outline(draw, aff_text, text_x + sw + 15, speaker_y + 4, f_aff, (160, 170, 190), (0, 0, 0), 2)
            else:
                draw.text((text_x + sw + 15, speaker_y + 4), aff_text, font=f_aff, fill=(120, 130, 150))

    if _card_style == 0:
        # Classic: 대형 따옴표 + 좌측 악센트 바
        quote_mark_h = 180
        speaker_h = 80 if speaker else 0
        total_block_h = quote_mark_h + total_text_h + speaker_h
        base_y = (h - total_block_h) // 2
        f_quote_mark = _get_font(160, "Black")
        qm_fill = tuple(c // 3 for c in accent)
        if transparent:
            _text_outline(draw, "\u201C", 60, base_y, f_quote_mark, qm_fill, (0, 0, 0), 3)
        else:
            draw.text((60, base_y), "\u201C", font=f_quote_mark, fill=qm_fill)
        f_text = _get_font(font_size, "Bold")
        text_x, text_y = 90, base_y + quote_mark_h
        draw.rectangle([65, text_y - 5, 72, text_y + total_text_h], fill=accent)
        for i, line in enumerate(lines):
            y = text_y + i * line_gap
            if transparent:
                _text_outline(draw, line, text_x, y, f_text, (240, 240, 250), (0, 0, 0), 3)
            else:
                draw.text((text_x, y), line, font=f_text, fill=(240, 240, 250))
        _render_speaker(draw, text_x, text_y + total_text_h + 50, transparent, accent)

    elif _card_style == 1:
        # Circle: 대형 원 안에 인용문
        cx, cy = w // 2, h // 2 - 20
        radius = min(w, h) // 2 - 50
        circle_bg = (*accent[:3], 25) if transparent else tuple(c // 10 for c in accent)
        circle_ol = (*accent[:3], 80) if transparent else tuple(c // 2 for c in accent)
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     fill=circle_bg, outline=circle_ol, width=3)
        # 따옴표
        f_qm = _get_font(120, "Black")
        qm_fill = (*accent[:3], 80) if transparent else tuple(c // 4 for c in accent)
        bbox = draw.textbbox((0, 0), "\u201C", font=f_qm)
        draw.text((cx - (bbox[2] - bbox[0]) // 2, cy - radius + 30), "\u201C", font=f_qm, fill=qm_fill)
        # 텍스트
        f_text = _get_font(min(font_size, 42), "Bold")
        text_start_y = cy - total_text_h // 2
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=f_text)
            tw = bbox[2] - bbox[0]
            lx = (w - tw) // 2
            ly = text_start_y + i * line_gap
            if transparent:
                _text_outline(draw, line, lx, ly, f_text, (240, 240, 250), (0, 0, 0), 3)
            else:
                draw.text((lx, ly), line, font=f_text, fill=(240, 240, 250))
        _render_speaker(draw, 90, cy + radius + 20, transparent, accent)

    elif _card_style == 2:
        # Banner: 풀폭 배너 안에 인용문
        banner_pad = 40
        speaker_h = 60 if speaker else 0
        banner_h = total_text_h + banner_pad * 2 + 80 + speaker_h
        banner_y = (h - banner_h) // 2
        banner_bg = (*accent[:3], 40) if transparent else tuple(c // 7 for c in accent)
        draw.rectangle([0, banner_y, w, banner_y + banner_h], fill=banner_bg)
        draw.rectangle([0, banner_y, w, banner_y + 4], fill=accent)
        draw.rectangle([0, banner_y + banner_h - 4, w, banner_y + banner_h], fill=accent)
        # 따옴표
        f_qm = _get_font(80, "Black")
        qm_fill = tuple(c // 3 for c in accent)
        if transparent:
            _text_outline(draw, "\u201C", 30, banner_y + 15, f_qm, qm_fill, (0, 0, 0), 2)
        else:
            draw.text((30, banner_y + 15), "\u201C", font=f_qm, fill=qm_fill)
        f_text = _get_font(font_size, "Bold")
        text_y = banner_y + banner_pad + 70
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=f_text)
            tw = bbox[2] - bbox[0]
            lx = (w - tw) // 2
            if transparent:
                _text_outline(draw, line, lx, text_y + i * line_gap, f_text, (240, 240, 250), (0, 0, 0), 3)
            else:
                draw.text((lx, text_y + i * line_gap), line, font=f_text, fill=(240, 240, 250))
        _render_speaker(draw, 60, text_y + total_text_h + 25, transparent, accent)

    elif _card_style == 3:
        # Timeline: 좌측 타임라인 + 인용문
        line_x = 70
        speaker_h = 80 if speaker else 0
        total_block_h = 120 + total_text_h + speaker_h
        base_y = (h - total_block_h) // 2
        line_color = (*accent[:3], 80) if transparent else tuple(c // 3 for c in accent)
        draw.rectangle([line_x - 2, base_y, line_x + 2, base_y + total_block_h], fill=line_color)
        # 큰 노드
        draw.ellipse([line_x - 16, base_y + 40, line_x + 16, base_y + 72], fill=accent)
        # 따옴표
        f_qm = _get_font(100, "Black")
        qm_fill = tuple(c // 3 for c in accent)
        if transparent:
            _text_outline(draw, "\u201C", line_x + 40, base_y, f_qm, qm_fill, (0, 0, 0), 2)
        else:
            draw.text((line_x + 40, base_y), "\u201C", font=f_qm, fill=qm_fill)
        f_text = _get_font(font_size, "Bold")
        text_x = line_x + 40
        text_y = base_y + 120
        for i, line in enumerate(lines):
            if transparent:
                _text_outline(draw, line, text_x, text_y + i * line_gap, f_text, (240, 240, 250), (0, 0, 0), 3)
            else:
                draw.text((text_x, text_y + i * line_gap), line, font=f_text, fill=(240, 240, 250))
        _render_speaker(draw, text_x, text_y + total_text_h + 30, transparent, accent)

    elif _card_style == 4:
        # Grid: 격자 프레임 + 꼭짓점 장식 안에 인용문
        frame_pad = 40
        speaker_h = 60 if speaker else 0
        frame_h = total_text_h + 120 + speaker_h + frame_pad * 2
        frame_x0, frame_y0 = 35, (h - frame_h) // 2
        frame_x1, frame_y1 = w - 35, frame_y0 + frame_h
        frame_bg = (*tone["card_bg"], 150) if transparent else tone["card_bg"]
        draw.rectangle([frame_x0, frame_y0, frame_x1, frame_y1], fill=frame_bg)
        corner_len = 45
        for (cx, cy, dx, dy) in [
            (frame_x0, frame_y0, 1, 1), (frame_x1, frame_y0, -1, 1),
            (frame_x0, frame_y1, 1, -1), (frame_x1, frame_y1, -1, -1),
        ]:
            draw.line([(cx, cy), (cx + corner_len * dx, cy)], fill=accent, width=4)
            draw.line([(cx, cy), (cx, cy + corner_len * dy)], fill=accent, width=4)
        # 따옴표
        f_qm = _get_font(100, "Black")
        qm_fill = tuple(c // 3 for c in accent)
        if transparent:
            _text_outline(draw, "\u201C", frame_x0 + 20, frame_y0 + 15, f_qm, qm_fill, (0, 0, 0), 2)
        else:
            draw.text((frame_x0 + 20, frame_y0 + 15), "\u201C", font=f_qm, fill=qm_fill)
        f_text = _get_font(font_size, "Bold")
        text_x = frame_x0 + 40
        text_y = frame_y0 + frame_pad + 100
        for i, line in enumerate(lines):
            if transparent:
                _text_outline(draw, line, text_x, text_y + i * line_gap, f_text, (240, 240, 250), (0, 0, 0), 3)
            else:
                draw.text((text_x, text_y + i * line_gap), line, font=f_text, fill=(240, 240, 250))
        _render_speaker(draw, text_x, text_y + total_text_h + 25, transparent, accent)

    return img


def _draw_comparison(w, h, data, bg_img=None):
    """범용 비교 바 차트"""
    accent = tuple(data.get("accent_color", [255, 100, 60]))
    items = data.get("items", [])
    baseline = data.get("baseline")
    unit = data.get("unit", "")
    tone = _get_tone(data)
    transparent = bg_img is not None

    img = _make_base(w, h, tone, bg_img)
    draw = ImageDraw.Draw(img)

    if not items:
        return img

    max_val = max(item["value"] for item in items) * 1.15
    bar_x = 220
    max_bar_w = w - bar_x - 80
    bar_h = 47  # 바 높이 (55 - 8)
    bar_gap = 25  # 바 사이 간격
    baseline_h = 45 if baseline else 0  # 기준선 라벨 높이
    total_block_h = baseline_h + len(items) * (bar_h + bar_gap) - bar_gap
    margin_y = (h - total_block_h) // 2  # 세로 가운데 정렬
    gap = bar_h + bar_gap

    f_name = _get_font(32, "Bold")
    f_val = _get_font(36, "Black")

    bar_bg = (*tone["card_bg"], 180) if transparent else tone["card_bg"]

    # 기준선
    if baseline:
        bx = bar_x + int(baseline["value"] / max_val * max_bar_w)
        draw.line([(bx, margin_y), (bx, margin_y + total_block_h)], fill=(80, 200, 120), width=2)
        f_base = _get_font(24, "Medium")
        label = f"{baseline['label']} {baseline['value']:,}{unit}"
        if transparent:
            _text_outline(draw, label, bx - 50, margin_y - 30, f_base, (80, 200, 120), (0, 0, 0), 2)
        else:
            draw.text((bx - 50, margin_y - 30), label, font=f_base, fill=(80, 200, 120))

    # 바 색상 그라데이션 생성
    default_colors = [
        (255, 80, 80), (255, 120, 60), (255, 160, 40),
        (255, 190, 50), (210, 210, 70), (140, 200, 90),
    ]

    bar_start_y = margin_y + baseline_h
    for i, item in enumerate(items):
        y = bar_start_y + i * gap
        bw = int(item["value"] / max_val * max_bar_w)
        color = tuple(item.get("color", list(default_colors[i % len(default_colors)])))

        # 바 배경
        draw.rounded_rectangle(
            [bar_x, y + 8, bar_x + max_bar_w, y + 55],
            radius=6, fill=bar_bg
        )
        # 바
        draw.rounded_rectangle(
            [bar_x, y + 8, bar_x + bw, y + 55],
            radius=6, fill=color
        )
        # 하이라이트
        highlight = tuple(min(255, c + 50) for c in color)
        draw.line([(bar_x + 6, y + 12), (bar_x + bw - 6, y + 12)], fill=highlight, width=1)

        # 라벨
        if transparent:
            _text_outline(draw, item.get("label", ""), 25, y + 14, f_name, (240, 240, 250), (0, 0, 0), 2)
        else:
            draw.text((25, y + 14), item.get("label", ""), font=f_name, fill=(240, 240, 250))

        # 값
        val_text = f"{item['value']:,}{unit}"
        if transparent:
            _right_text_outline(draw, val_text, w - 30, y + 10, f_val, (255, 255, 255), (0, 0, 0), 2)
        else:
            _right_text(draw, val_text, w - 30, y + 10, f_val, (255, 255, 255))

    # 첫 바 글로우 (어두운 배경에서만)
    if not transparent:
        first_y = bar_start_y
        first_bw = int(items[0]["value"] / max_val * max_bar_w)
        first_color = tuple(items[0].get("color", list(default_colors[0])))
        img = _add_glow(img, lambda d: d.rounded_rectangle(
            [bar_x, first_y + 8, bar_x + first_bw, first_y + 55],
            radius=6, fill=tuple(c // 4 for c in first_color)
        ), blur_radius=15)

    return img
