# -*- coding: utf-8 -*-
"""한국 지류(종이) 증빙 문서 샘플 PDF 생성 - 공통 유틸리티.

모든 데이터는 가상의 내용이며, 문서마다 '샘플/SAMPLE' 워터마크가 인쇄된다.
"""
from __future__ import annotations

import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(BASE, "fonts")

# ---------------------------------------------------------------- 숫자/문자 유틸

def won(n) -> str:
    """1234567 -> '1,234,567'"""
    return f"{int(round(float(n))):,}"


_DIGIT = "영일이삼사오육칠팔구"
_SMALL_UNIT = ["", "십", "백", "천"]
_BIG_UNIT = ["", "만", "억", "조"]


def kor_amount(n: int) -> str:
    """1375000 -> '일백삼십칠만오천' (금액 한글 표기, 갖은자 아님)"""
    n = int(n)
    if n == 0:
        return "영"
    parts, gi = [], 0
    while n > 0:
        chunk, n = n % 10000, n // 10000
        if chunk:
            s = ""
            for pos in range(3, -1, -1):
                d = (chunk // (10 ** pos)) % 10
                if d:
                    s += _DIGIT[d] + _SMALL_UNIT[pos]
            parts.append(s + _BIG_UNIT[gi])
        gi += 1
    return "".join(reversed(parts))


def kor_won(n: int) -> str:
    """정형 문구: '일금 일천삼백칠십오만원정'"""
    return f"일금 {kor_amount(n)}원정"


def biz_no(nine: str) -> str:
    """앞 9자리로 검증번호(체크디지트)를 계산해 000-00-00000 형식으로 반환."""
    nine = nine.replace("-", "")
    assert len(nine) == 9, nine
    w = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    s = sum(int(d) * k for d, k in zip(nine, w))
    s += (int(nine[8]) * 5) // 10
    chk = (10 - s % 10) % 10
    full = nine + str(chk)
    return f"{full[0:3]}-{full[3:5]}-{full[5:10]}"


def corp_no(v: str) -> str:
    """법인등록번호 표기(가상): 000000-0000000"""
    return v


# ---------------------------------------------------------------- HTML 조각

def digit_cells(amount: int, cells: int, blank_label: bool = True) -> str:
    """세금계산서식 금액 칸(공란수 + 자릿수 칸)을 <td> 문자열로 반환."""
    digits = f"{int(amount)}"
    pad = cells - len(digits)
    out = []
    if blank_label:
        out.append(f'<td class="dg blank">{pad if pad > 0 else 0}</td>')
    for i in range(cells):
        idx = i - pad
        ch = digits[idx] if idx >= 0 else ""
        out.append(f'<td class="dg">{ch}</td>')
    return "".join(out)


def rows(data, cols, empty_rows=0, cls=""):
    """리스트 데이터를 <tr>로. data: list[list[str]] / cols: list[(class, )]"""
    out = []
    for r in data:
        tds = "".join(f'<td class="{c}">{v}</td>' for v, c in zip(r, cols))
        out.append(f'<tr class="{cls}">{tds}</tr>')
    for _ in range(empty_rows):
        tds = "".join(f'<td class="{c}">&nbsp;</td>' for c in cols)
        out.append(f'<tr class="{cls}">{tds}</tr>')
    return "\n".join(out)


def stamp(name: str, size: int = 46) -> str:
    """원형 인감(도장) 이미지 대체 - 붉은 원 안에 이름."""
    fs = 13 if len(name) <= 3 else 11
    return (
        f'<span class="stamp" style="width:{size}px;height:{size}px;font-size:{fs}px">'
        f'<span>{name}</span></span>'
    )


def barcode(text: str, width_mm: int = 55) -> str:
    """의사(pseudo) 바코드 - 문자열 해시로 막대 생성."""
    bars = []
    h = 0
    for ch in text:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    for i in range(58):
        h = (h * 1103515245 + 12345) & 0x7FFFFFFF
        w = 1 + (h >> 8) % 3
        col = "#000" if i % 2 == 0 else "#fff"
        bars.append(f'<i style="width:{w}px;background:{col}"></i>')
    return (
        f'<span class="barcode" style="width:{width_mm}mm">{"".join(bars)}</span>'
        f'<span class="barcode-txt">{text}</span>'
    )


# ---------------------------------------------------------------- 페이지 CSS

PAGE_SIZES = {
    "A4": ("210mm", "297mm", "10mm"),
    "A4L": ("297mm", "210mm", "10mm"),
    "A5": ("148mm", "210mm", "8mm"),
    "A5L": ("210mm", "148mm", "8mm"),
    "SLIP": ("80mm", "200mm", "4mm"),     # POS 감열지 영수증
    "SLIP_L": ("80mm", "260mm", "4mm"),
    "CARD": ("100mm", "150mm", "5mm"),    # 카드 전표
}


def base_css(size: str = "A4") -> str:
    w, h, m = PAGE_SIZES[size]
    return f"""
@font-face {{ font-family:'NG'; font-weight:400;
  src:url('file://{FONT_DIR}/NanumGothic-Regular.ttf') format('truetype'); }}
@font-face {{ font-family:'NG'; font-weight:700;
  src:url('file://{FONT_DIR}/NanumGothic-Bold.ttf') format('truetype'); }}
@font-face {{ font-family:'NM'; font-weight:400;
  src:url('file://{FONT_DIR}/NanumMyeongjo-Regular.ttf') format('truetype'); }}
@font-face {{ font-family:'NM'; font-weight:700;
  src:url('file://{FONT_DIR}/NanumMyeongjo-Bold.ttf') format('truetype'); }}

@page {{ size:{w} {h}; margin:{m}; }}
* {{ box-sizing:border-box; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
html,body {{ margin:0; padding:0; }}
body {{ font-family:'NG',sans-serif; font-size:9pt; color:#111; line-height:1.35;
        position:relative; padding-bottom:5mm; }}
.mono {{ font-variant-numeric:tabular-nums; }}
.myeong {{ font-family:'NM',serif; }}

/* ------- 워터마크 ------- */
.wm {{ position:fixed; inset:0; z-index:999; pointer-events:none;
       display:flex; align-items:center; justify-content:center; }}
.wm span {{ transform:rotate(-28deg); font-size:52pt; font-weight:700; letter-spacing:8px;
            color:rgba(200,30,30,.10); border:6px solid rgba(200,30,30,.10);
            padding:10px 34px; border-radius:8px; white-space:nowrap; }}
.wm-note {{ position:fixed; left:0; right:0; bottom:0; z-index:999; text-align:center;
            font-size:6.5pt; color:#b03030; letter-spacing:.3px; }}

/* ------- 공통 타이틀 ------- */
h1.title {{ font-size:20pt; font-weight:700; letter-spacing:14px; text-align:center;
            margin:2mm 0 1mm; }}
h1.title.sm {{ font-size:15pt; letter-spacing:8px; }}
.subtitle {{ text-align:center; font-size:8.5pt; color:#444; margin-bottom:3mm; }}
.doc-meta {{ display:flex; justify-content:space-between; font-size:8pt; color:#333;
             margin-bottom:1.5mm; }}

/* ------- 표 ------- */
table {{ border-collapse:collapse; width:100%; }}
table.grid, table.grid th, table.grid td {{ border:.7pt solid #222; }}
table.grid th, table.grid td {{ padding:1.2mm 1.5mm; vertical-align:middle; }}
table.grid th {{ background:#f0f0f0; font-weight:700; text-align:center; }}
td.c, th.c {{ text-align:center; }}
td.r, th.r {{ text-align:right; }}
td.l, th.l {{ text-align:left; }}
td.lbl {{ background:#f2f2f2; text-align:center; font-weight:700; white-space:nowrap; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.small {{ font-size:7.5pt; }}
.xsmall {{ font-size:6.8pt; }}
.big {{ font-size:12pt; font-weight:700; }}
.b {{ font-weight:700; }}
.red {{ color:#c02020; }}
.blue {{ color:#1a3f8f; }}
.tight td, .tight th {{ padding:.7mm 1mm; }}

/* 세금계산서 금액 칸 */
td.dg {{ width:5.2mm; text-align:center; font-family:'NG'; font-size:9pt;
         border-left:.5pt solid #888 !important; }}
td.dg.blank {{ background:#f7f7f7; }}

/* 도장 */
.stamp {{ display:inline-flex; align-items:center; justify-content:center;
          border:1.6pt solid #d02b2b; color:#d02b2b; border-radius:50%;
          font-weight:700; line-height:1.05; text-align:center;
          transform:rotate(-8deg); opacity:.85; }}

/* 바코드 */
.barcode {{ display:inline-flex; align-items:flex-end; height:11mm; overflow:hidden; }}
.barcode i {{ display:block; height:100%; }}
.barcode-txt {{ display:block; font-size:7pt; letter-spacing:2px; text-align:center; }}

/* 영수증(감열지) */
.slip {{ font-family:'NG'; font-size:8pt; }}
.slip .ttl {{ text-align:center; font-weight:700; font-size:11pt; margin:1mm 0 2mm;
              letter-spacing:2px; }}
.slip hr {{ border:0; border-top:1px dashed #444; margin:1.5mm 0; }}
.slip .row {{ display:flex; justify-content:space-between; }}
.slip .row span:last-child {{ font-variant-numeric:tabular-nums; }}

.note {{ font-size:7.5pt; color:#333; margin-top:2mm; }}
.sign-area {{ margin-top:5mm; text-align:center; font-size:9.5pt; line-height:2.1; }}
.footer-org {{ text-align:center; font-size:13pt; font-weight:700; letter-spacing:6px;
               margin-top:4mm; }}
"""


def html_doc(title: str, body: str, size: str = "A4", extra_css: str = "",
             watermark: str = "샘플 SAMPLE",
             note: str = "본 문서는 시스템 테스트·교육용으로 생성된 가상의 샘플입니다. 실제 거래·법적 효력이 없습니다.") -> str:
    wm = f'<div class="wm"><span>{watermark}</span></div>' if watermark else ""
    nt = f'<div class="wm-note">{note}</div>' if note else ""
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>{title}</title>
<style>{base_css(size)}
{extra_css}</style></head>
<body>{wm}{nt}
{body}
</body></html>"""


# ---------------------------------------------------------------- 가상 거래 당사자

SUPPLIER = dict(
    name="(주)한빛테크놀로지", ceo="김한빛",
    bno=biz_no("214810111"), corpno="110111-1234567",
    addr="서울특별시 강남구 테헤란로 123, 8층 (역삼동, 한빛빌딩)",
    biz="서비스", item="소프트웨어 개발, 시스템 유지보수",
    tel="02-555-1234", fax="02-555-1235", email="tax@hanbit-tech.example",
    bank="대한은행", acct="123-456789-01-001",
)

BUYER = dict(
    name="(주)미래유통", ceo="박미래",
    bno=biz_no("137812345"), corpno="110111-7654321",
    addr="경기도 성남시 분당구 판교로 45, 3층 (삼평동)",
    biz="도소매", item="전자제품, 사무용기기",
    tel="031-777-8800", fax="031-777-8801", email="account@mirae-dist.example",
)

# 하나의 거래 스토리로 문서들을 연결한다.
DEAL = dict(
    date="2026-03-31", date_k="2026년 03월 31일",
    supply=12_500_000, vat=1_250_000, total=13_750_000,
    subject="ERP 연동 모듈 개발 및 구축 용역",
    po_no="PO-2026-0198", est_no="QT-2026-0173", ti_no="20260331-41000012-88776655",
)

ITEMS = [
    # 월, 일, 품목, 규격, 수량, 단가, 공급가액, 세액
    ("03", "10", "ERP 연동 모듈 개발(설계·구현)", "1식", "1", 8_000_000, 8_000_000, 800_000),
    ("03", "24", "데이터 마이그레이션 용역", "1식", "1", 3_000_000, 3_000_000, 300_000),
    ("03", "31", "사용자 교육 및 매뉴얼 제작", "회", "3", 500_000, 1_500_000, 150_000),
]
