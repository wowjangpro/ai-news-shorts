"""코드 기반 인포그래픽 배경 생성기 — 강화 버전
글로우, 그라데이션, 카드 레이아웃으로 고품질 뉴스 비주얼 생성"""
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import os


# ── 유틸리티 ──

def _get_font(size, weight="Bold"):
    """시스템 한글 폰트 로드 (.ttc 인덱스 지원)"""
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


def _particles(draw, w, h, count=30, seed=42, color=(40, 60, 100)):
    """미세 입자 효과"""
    rng = random.Random(seed)
    for _ in range(count):
        x, y = rng.randint(0, w), rng.randint(0, h)
        r = rng.randint(1, 4)
        b = rng.uniform(0.3, 1.0)
        c = tuple(int(v * b) for v in color)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=c)


def _right_text(draw, text, x_right, y, font, fill):
    """오른쪽 정렬 텍스트"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((x_right - tw, y), text, font=font, fill=fill)


# ── 메인 디스패치 ──

def generate_infographic(w: int, h: int, prompt: str, tag: str = "") -> Image.Image:
    """프롬프트 키워드로 적절한 인포그래픽 생성"""
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

    _particles(draw, w, h, 20, seed=7, color=(30, 50, 90))
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

    _particles(draw, w, h, 25, seed=33, color=(25, 55, 100))
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

    _particles(draw, w, h, 15, seed=77, color=(50, 20, 20))
    return img


# ── 일반 뉴스 배경 ──

def _draw_generic_news(w, h):
    """일반 뉴스 배경"""
    img = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    _gradient(draw, 0, 0, w, h, (10, 15, 35), (5, 5, 20))
    _center_glow(draw, w // 2, h // 2, 500, (30, 45, 80))
    _particles(draw, w, h, 40, seed=99, color=(40, 60, 100))

    return img
