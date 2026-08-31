# -*- coding: utf-8 -*-
"""한국 지류 증빙 문서 샘플 PDF 일괄 생성기.

사용법:  python3 src/generate.py [모듈접두사 ...]
  예)   python3 src/generate.py            # 전체 생성
        python3 src/generate.py g1 g3      # 특정 그룹만 생성
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys

SRC = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SRC)
HTML_DIR = os.path.join(BASE, "build", "html")
PDF_DIR = os.path.join(BASE, "pdf")
CHROME = "/opt/pw-browsers/chromium"

MODULES = ["g1_qualified", "g2_commerce", "g3_internal", "g4_payroll",
           "g5_tax_utility", "g6_finance", "g7_travel", "g8_trade", "g9_attach"]

sys.path.insert(0, SRC)


def collect(prefixes=None):
    docs = []
    for m in MODULES:
        if prefixes and not any(m.startswith(p) for p in prefixes):
            continue
        if not os.path.exists(os.path.join(SRC, m + ".py")):
            continue
        mod = importlib.import_module(m)
        for d in mod.build():
            d["module"] = m
            docs.append(d)
    docs.sort(key=lambda d: d["no"])
    return docs


def render(doc):
    os.makedirs(HTML_DIR, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)
    hp = os.path.join(HTML_DIR, doc["slug"] + ".html")
    pp = os.path.join(PDF_DIR, doc["slug"] + ".pdf")
    with open(hp, "w", encoding="utf-8") as f:
        f.write(doc["html"])
    cmd = [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
           "--no-pdf-header-footer", "--font-render-hinting=none",
           "--run-all-compositor-stages-before-draw",
           "--virtual-time-budget=2000",
           f"--print-to-pdf={pp}", "file://" + hp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    ok = os.path.exists(pp) and os.path.getsize(pp) > 1000
    if not ok:
        print("  !! FAILED:", doc["slug"], r.stderr[-400:])
    return pp, ok


def build_index(docs):
    """전체 목록(카탈로그) 문서를 생성한다."""
    from common import html_doc
    from index_meta import META

    css = """
h1.title { border-top:2.4pt solid #111; border-bottom:2.4pt solid #111; padding:2.5mm 0; }
table.grid td, table.grid th { font-size:7.6pt; padding:1mm 1.4mm; }
tr.cat td { background:#dfe6f2; font-weight:700; font-size:8.2pt; letter-spacing:1px; }
.badge { display:inline-block; border-radius:2mm; padding:.2mm 1.4mm; font-size:6.8pt;
         font-weight:700; color:#fff; }
.b-q { background:#1a6b3f; }  /* 적격증빙 */
.b-l { background:#16457a; }  /* 법정서류 */
.b-s { background:#7a5a16; }  /* 보조·기타 */
.b-i { background:#6b2f6b; }  /* 내부증빙 */
.legend span { margin-right:4mm; }
"""
    def badge(kind):
        if "적격" in kind:
            c = "b-q"
        elif "법정" in kind:
            c = "b-l"
        elif "내부" in kind:
            c = "b-i"
        else:
            c = "b-s"
        return f'<span class="badge {c}">{kind}</span>'

    rows, cur = [], None
    for d in docs:
        cat, kind, law, keep = META.get(d["no"], ("기타", "-", "-", "-"))
        if cat != cur:
            rows.append(f'<tr class="cat"><td colspan="6">{cat}</td></tr>')
            cur = cat
        rows.append(
            f'<tr><td class="c">{d["no"]:02d}</td><td>{d["title"]}</td>'
            f'<td class="c">{badge(kind)}</td><td class="small">{law}</td>'
            f'<td class="c">{keep}</td><td class="c xsmall">{d["size"]}</td></tr>')

    body = f"""
<h1 class="title sm">한국 지류(종이) 증빙 문서 샘플 목록</h1>
<div class="subtitle">Korean Paper Voucher / Supporting Document Samples &nbsp;|&nbsp;
  총 {len(docs)}종 &nbsp;|&nbsp; 생성일 2026-08-30</div>
<div class="legend small" style="margin:2mm 0">
  <span>{badge("적격증빙")} 법정지출증빙 (매입세액 공제·손금 인정)</span>
  <span>{badge("법정서류")} 법령상 발급·교부 의무 서류</span>
  <span>{badge("보조증빙")} 거래사실 보강 서류</span>
  <span>{badge("내부증빙")} 내부통제·결재 서류</span>
</div>
<table class="grid">
<tr><th style="width:10mm">No</th><th>문서명</th><th style="width:22mm">성격</th>
    <th style="width:62mm">근거 법령 / 실무 기준</th><th style="width:16mm">보관<br>기간</th>
    <th style="width:14mm">용지</th></tr>
{"".join(rows)}
</table>
<div class="note" style="margin-top:3mm">
<b>[ 적격증빙(법정지출증빙) 수취 원칙 ]</b><br>
· 사업자와의 거래에서 건당 3만원(접대비는 3만원) 초과 지출 시 세금계산서·계산서·
  신용카드매출전표·현금영수증(지출증빙용) 중 하나를 반드시 수취해야 합니다.<br>
· 적격증빙을 수취하지 않으면 증빙불비가산세 2%가 부과됩니다(법인세법 §75의5).<br>
· 모든 증빙서류는 법정신고기한 종료일부터 <b>5년간</b> 보관해야 합니다(국세기본법 §85의3).<br>
· 전자세금계산서·전자계산서는 국세청 전송분에 한해 별도 보관의무가 면제됩니다.<br><br>
<b>[ 본 샘플 자료에 대하여 ]</b><br>
· 모든 상호·성명·번호·금액은 가상의 값이며, 실제 개인·법인·기관과 무관합니다.<br>
· 사업자등록번호는 형식 검증(체크디지트)만 통과하도록 생성된 가상 번호입니다.<br>
· 주민등록번호는 뒷자리를 마스킹(******) 처리하였습니다.<br>
· 용도 : OCR·문서분류 모델 학습, 회계 시스템 테스트, 실무 교육 자료.
</div>
"""
    return dict(no=0, slug="00_증빙문서_목차", size="A4", title="증빙 문서 샘플 목록(목차)",
                html=html_doc("한국 지류 증빙 샘플 목록", body, extra_css=css,
                              watermark="샘플 SAMPLE"))


def merge_all(docs):
    """전체 문서를 하나의 샘플북 PDF로 병합한다."""
    try:
        from pypdf import PdfWriter
    except ImportError:
        print("  (pypdf 미설치 - 통합본 생략)")
        return
    out = os.path.join(PDF_DIR, "_한국_지류증빙_샘플북_전체.pdf")
    w = PdfWriter()
    for d in docs:
        p = os.path.join(PDF_DIR, d["slug"] + ".pdf")
        if os.path.exists(p):
            w.append(p, outline_item=f'{d["no"]:02d}. {d["title"]}')
    with open(out, "wb") as f:
        w.write(f)
    print(f"통합본: {out} ({os.path.getsize(out)/1024:.0f} KB)")


def main():
    prefixes = sys.argv[1:] or None
    docs = collect(prefixes)
    print(f"총 {len(docs)}종 생성 시작")
    okc = 0
    for d in docs:
        pp, ok = render(d)
        okc += ok
        if ok:
            kb = os.path.getsize(pp) / 1024
            print(f"  [{d['no']:02d}] {d['title']:<34} {d['size']:<7} {kb:6.0f} KB")
    if not prefixes:
        idx = build_index(docs)
        render(idx)
        print(f"  [00] {idx['title']}")
        merge_all([idx] + docs)
    print(f"완료: {okc}/{len(docs)}  ->  {PDF_DIR}")
    return 0 if okc == len(docs) else 1


if __name__ == "__main__":
    sys.exit(main())
