# -*- coding: utf-8 -*-
"""그룹 1. 법정지출증빙(적격증빙) - 세금계산서 계열, 카드전표, 현금영수증"""
from common import (SUPPLIER, BUYER, DEAL, ITEMS, won, kor_won, digit_cells,
                    stamp, barcode, html_doc, biz_no)

TI_CSS = """
table.ti { border-collapse:collapse; width:100%; font-size:8.5pt; }
table.ti td, table.ti th { border:.7pt solid #1a3f8f; padding:1.4mm 1.2mm; }
table.ti.items td { height:7.2mm; }
table.ti .vert { writing-mode:vertical-rl; text-orientation:upright; letter-spacing:3px;
                 font-weight:700; text-align:center; width:6mm; background:#eef2fb; }
table.ti .lbl2 { background:#eef2fb; text-align:center; font-weight:700; white-space:nowrap; }
.ti-wrap { border:1.6pt solid #1a3f8f; padding:1.5mm; }
h1.ti-title { color:#1a3f8f; }
table.ti td.dg { border-left:.5pt solid #7b8db5 !important; }
"""


def _party_rows(sup, buy, buy_stamp=True):
    """공급자/공급받는자 4행을 좌우 나란히 배치한 <tr> 묶음."""
    bs = stamp('대표이사', 32) if buy_stamp else '(인)'
    return f"""
<tr>
  <td class="vert" rowspan="4">공급자</td>
  <td class="lbl2" style="width:14mm">등록번호</td>
  <td colspan="3" class="c b mono" style="letter-spacing:2px">{sup['bno']}</td>
  <td class="vert" rowspan="4">공급받는자</td>
  <td class="lbl2" style="width:14mm">등록번호</td>
  <td colspan="3" class="c b mono" style="letter-spacing:2px">{buy['bno']}</td>
</tr>
<tr>
  <td class="lbl2">상호<br><span class="xsmall">(법인명)</span></td>
  <td style="width:33mm">{sup['name']}</td>
  <td class="lbl2" style="width:12mm">성명</td>
  <td style="width:33mm">{sup['ceo']} {stamp('대표이사', 32)}</td>
  <td class="lbl2">상호<br><span class="xsmall">(법인명)</span></td>
  <td style="width:33mm">{buy['name']}</td>
  <td class="lbl2" style="width:12mm">성명</td>
  <td style="width:33mm">{buy['ceo']} {bs}</td>
</tr>
<tr>
  <td class="lbl2">사업장<br>주소</td>
  <td colspan="3" class="xsmall">{sup['addr']}</td>
  <td class="lbl2">사업장<br>주소</td>
  <td colspan="3" class="xsmall">{buy['addr']}</td>
</tr>
<tr>
  <td class="lbl2">업태</td><td>{sup['biz']}</td>
  <td class="lbl2">종목</td><td class="xsmall">{sup['item']}</td>
  <td class="lbl2">업태</td><td>{buy['biz']}</td>
  <td class="lbl2">종목</td><td class="xsmall">{buy['item']}</td>
</tr>"""


def _item_rows(items, empty=2):
    out = []
    for m, d, nm, spec, qty, price, sup, vat in items:
        out.append(
            f'<tr><td class="c" style="width:8mm">{m}</td><td class="c" style="width:8mm">{d}</td>'
            f'<td style="width:64mm">{nm}</td><td class="c" style="width:14mm">{spec}</td>'
            f'<td class="c" style="width:12mm">{qty}</td>'
            f'<td class="num" style="width:22mm">{won(price)}</td>'
            f'<td class="num" style="width:26mm">{won(sup)}</td>'
            f'<td class="num" style="width:22mm">{won(vat)}</td>'
            f'<td style="width:16mm">&nbsp;</td></tr>')
    for _ in range(empty):
        out.append('<tr>' + '<td>&nbsp;</td>' * 9 + '</tr>')
    return "\n".join(out)


def _tax_invoice(kind, copy_label, color_note, sn, items, supply, vat,
                 title="세금계산서", remark="", receipt=True, extra_top=""):
    total = supply + vat
    body = f"""
<div class="ti-wrap">
<table style="border:0"><tr style="border:0">
  <td style="border:0;width:62%">
    <h1 class="title sm ti-title" style="margin:1mm 0">{'&nbsp;'.join(title)}</h1>
    <div class="subtitle" style="margin:0;color:#1a3f8f">({copy_label})</div>
  </td>
  <td style="border:0;vertical-align:top">
    <table class="ti tight">
      <tr><td class="lbl2" rowspan="2" style="width:16mm">책 번 호</td>
          <td class="c" style="width:16mm">권</td><td class="c" style="width:16mm">호</td></tr>
      <tr><td class="c">4</td><td class="c">12</td></tr>
      <tr><td class="lbl2">일련번호</td><td class="c mono" colspan="2">{sn}</td></tr>
    </table>
  </td></tr></table>
{extra_top}
<table class="ti">
{_party_rows(SUPPLIER, BUYER, buy_stamp=False)}
</table>

<table class="ti" style="margin-top:-.7pt">
<tr>
  <td class="lbl2" colspan="3" style="width:34mm">작성</td>
  <td class="lbl2" colspan="12">공급가액</td>
  <td class="lbl2" colspan="10">세액</td>
  <td class="lbl2" rowspan="2" style="width:26mm">비고</td>
</tr>
<tr class="tight">
  <td class="c" style="width:14mm">년<br><span class="b">{DEAL['date'][:4]}</span></td>
  <td class="c" style="width:10mm">월<br><span class="b">{DEAL['date'][5:7]}</span></td>
  <td class="c" style="width:10mm">일<br><span class="b">{DEAL['date'][8:]}</span></td>
  {digit_cells(supply, 11)}
  {digit_cells(vat, 10, blank_label=False)}
</tr>
</table>

<table class="ti items" style="margin-top:-.7pt">
<tr><th style="width:8mm">월</th><th style="width:8mm">일</th><th>품목</th>
    <th style="width:14mm">규격</th><th style="width:12mm">수량</th>
    <th style="width:22mm">단가</th><th style="width:26mm">공급가액</th>
    <th style="width:22mm">세액</th><th style="width:16mm">비고</th></tr>
{_item_rows(items, empty=max(1, 6 - len(items)))}
</table>

<table class="ti" style="margin-top:-.7pt">
<tr><td class="lbl2" style="width:22mm">합계금액</td>
    <td class="num b" style="width:30mm">{won(total)}</td>
    <td class="lbl2" style="width:16mm">현금</td><td class="num" style="width:26mm">{won(total) if receipt else '&nbsp;'}</td>
    <td class="lbl2" style="width:16mm">수표</td><td style="width:24mm">&nbsp;</td>
    <td class="lbl2" style="width:16mm">어음</td><td style="width:24mm">&nbsp;</td>
    <td class="lbl2" style="width:22mm">외상미수금</td>
    <td class="num" style="width:26mm">{'&nbsp;' if receipt else won(total)}</td>
    <td class="c xsmall">이 금액을 <b>{'영수' if receipt else '청구'}</b>함</td></tr>
</table>
<div class="xsmall" style="margin-top:1mm;color:#1a3f8f">
{color_note} &nbsp;|&nbsp; 부가가치세법 시행규칙 [별지 제14호서식] 준용 &nbsp;|&nbsp; {remark}
</div>
</div>
"""
    return body


def build():
    docs = []

    # 01. 종이 세금계산서 (공급받는자 보관용)
    docs.append(dict(no=1, slug="01_세금계산서_공급받는자보관용", size="A4L",
                     title="세금계산서 (공급받는자 보관용)",
                     html=html_doc("세금계산서", _tax_invoice(
                         "paper", "공급받는자 보관용", "청색 : 공급받는자 보관용",
                         "2026-000412", ITEMS, DEAL['supply'], DEAL['vat'],
                         remark="지류(종이) 세금계산서 2매 1조 중 청색"),
                         size="A4L", extra_css=TI_CSS)))

    # 02. 종이 세금계산서 (공급자 보관용)
    docs.append(dict(no=2, slug="02_세금계산서_공급자보관용", size="A4L",
                     title="세금계산서 (공급자 보관용)",
                     html=html_doc("세금계산서(공급자)", _tax_invoice(
                         "paper", "공급자 보관용", "적색 : 공급자 보관용",
                         "2026-000412", ITEMS, DEAL['supply'], DEAL['vat'],
                         remark="지류(종이) 세금계산서 2매 1조 중 적색", receipt=False),
                         size="A4L", extra_css=TI_CSS)))

    # 03. 전자세금계산서 출력본
    etop = f"""
<table class="ti tight" style="margin-bottom:1mm">
<tr><td class="lbl2" style="width:24mm">승인번호</td>
    <td class="c mono b" style="width:60mm">{DEAL['ti_no']}</td>
    <td class="lbl2" style="width:24mm">전송일시</td>
    <td class="c mono">2026-04-01 09:12:33</td>
    <td class="lbl2" style="width:20mm">종류</td>
    <td class="c">일반 / 영수</td></tr>
</table>"""
    docs.append(dict(no=3, slug="03_전자세금계산서_출력본", size="A4L",
                     title="전자세금계산서 (출력본)",
                     html=html_doc("전자세금계산서", _tax_invoice(
                         "e", "공급받는자 보관용 · 전자발행", "국세청 전자세금계산서 (e-Tax Invoice) 출력본",
                         "2026-000412", ITEMS, DEAL['supply'], DEAL['vat'],
                         title="전자세금계산서",
                         remark="국세청 홈택스 발급분 출력물 (원본은 전자문서)",
                         extra_top=etop),
                         size="A4L", extra_css=TI_CSS)))

    # 04. 수정세금계산서 (기재사항 착오정정 - 마이너스 발행)
    m_items = [("03", "31", "ERP 연동 모듈 개발(당초분 취소)", "1식", "-1",
                12_500_000, -12_500_000, -1_250_000)]
    mtop = f"""
<table class="ti tight" style="margin-bottom:1mm">
<tr><td class="lbl2" style="width:24mm">당초 승인번호</td>
    <td class="c mono" style="width:58mm">{DEAL['ti_no']}</td>
    <td class="lbl2" style="width:22mm">수정사유</td>
    <td class="c b" style="width:40mm">기재사항 착오·정정 (코드 04)</td>
    <td class="lbl2" style="width:20mm">당초 작성일</td>
    <td class="c mono">2026-03-31</td></tr>
</table>"""
    body = _tax_invoice("m", "공급받는자 보관용 · 수정발행", "수정세금계산서 (당초분 취소 후 재발행)",
                        "2026-000418", m_items, -12_500_000, -1_250_000,
                        title="수정세금계산서", extra_top=mtop, receipt=False,
                        remark="음(-)의 금액으로 당초분을 취소하고 정정분을 별도 발행")
    body = body.replace('class="dg blank">0<', 'class="dg blank">△<')
    docs.append(dict(no=4, slug="04_수정세금계산서", size="A4L",
                     title="수정세금계산서", html=html_doc("수정세금계산서", body,
                                                     size="A4L", extra_css=TI_CSS)))

    # 05. 계산서 (면세)
    f_items = [("03", "20", "직업능력개발 위탁교육(면세)", "회", "2", 1_500_000, 3_000_000, 0),
               ("03", "27", "도서 구입 (기술서적)", "권", "40", 25_000, 1_000_000, 0)]
    fbody = _tax_invoice("f", "공급받는자 보관용", "계산서 - 부가가치세 면세 재화·용역",
                         "2026-000031", f_items, 4_000_000, 0, title="계산서",
                         remark="세액란 없음(면세). 부가가치세법 시행규칙 [별지 제15호서식] 준용",
                         receipt=False)
    # 계산서에는 세액 칸이 없다 -> 세액 열 헤더/값을 '비고'로 대체
    fbody = fbody.replace('<td class="lbl2" colspan="10">세액</td>',
                          '<td class="lbl2" colspan="10">비고 (면세)</td>')
    docs.append(dict(no=5, slug="05_계산서_면세", size="A4L", title="계산서 (면세)",
                     html=html_doc("계산서", fbody, size="A4L", extra_css=TI_CSS)))

    # 06. 수입세금계산서 (세관장 발행)
    i_items = [("03", "18", "수입물품 (HS 8471.30-0000, 노트북컴퓨터 50대)", "EA", "50",
                420_000, 21_000_000, 2_100_000)]
    itop = """
<table class="ti tight" style="margin-bottom:1mm">
<tr><td class="lbl2" style="width:24mm">수입신고번호</td>
    <td class="c mono" style="width:52mm">41099-26-0123456M</td>
    <td class="lbl2" style="width:20mm">신고수리일</td><td class="c mono">2026-03-18</td>
    <td class="lbl2" style="width:20mm">발행세관</td><td class="c">인천세관장</td></tr>
</table>"""
    ibody = _tax_invoice("imp", "수입자 보관용", "수입세금계산서 - 세관장 발행분",
                         "2026-IMP-0451", i_items, 21_000_000, 2_100_000,
                         title="수입세금계산서", extra_top=itop, receipt=False,
                         remark="공급자란은 세관장, 공급받는자란은 수입자를 기재")
    ibody = ibody.replace(SUPPLIER['name'], "인천세관장")
    ibody = ibody.replace(SUPPLIER['bno'], biz_no("121830011"))
    ibody = ibody.replace(SUPPLIER['ceo'], "인천세관장")
    ibody = ibody.replace(SUPPLIER['addr'], "인천광역시 중구 서해대로 339 (항동7가)")
    ibody = ibody.replace(SUPPLIER['item'], "관세행정")
    ibody = ibody.replace(">서비스<", ">국가기관<")
    docs.append(dict(no=6, slug="06_수입세금계산서", size="A4L", title="수입세금계산서",
                     html=html_doc("수입세금계산서", ibody, size="A4L", extra_css=TI_CSS)))

    # 07. 신용카드 매출전표
    slip = f"""
<div class="slip">
  <div class="ttl">신용카드 매출전표</div>
  <div class="row"><span>[ 고객용 ]</span><span>승인</span></div>
  <hr>
  <div class="row"><span>가맹점명</span><span>한빛문구 역삼점</span></div>
  <div class="row"><span>사업자번호</span><span>{biz_no('220150987')}</span></div>
  <div class="row"><span>대표자</span><span>이문구</span></div>
  <div class="row"><span>주소</span><span>서울 강남구 테헤란로 130</span></div>
  <div class="row"><span>전화</span><span>02-556-7788</span></div>
  <div class="row"><span>가맹점번호</span><span>3210987654</span></div>
  <hr>
  <div class="row"><span>카드종류</span><span>대한카드(법인)</span></div>
  <div class="row"><span>카드번호</span><span>5327-88**-****-1234</span></div>
  <div class="row"><span>거래일시</span><span>2026/03/17 14:22:05</span></div>
  <div class="row"><span>거래유형</span><span>신용승인 / 일시불</span></div>
  <div class="row"><span>승인번호</span><span>30117742</span></div>
  <div class="row"><span>단말기번호</span><span>CAT 1204 5581</span></div>
  <hr>
  <div class="row"><span>공 급 가 액</span><span>{won(345455)}</span></div>
  <div class="row"><span>부 가 세</span><span>{won(34545)}</span></div>
  <div class="row"><span>봉 사 료</span><span>0</span></div>
  <div class="row b" style="font-size:10pt"><span>합 계</span><span>{won(380000)}</span></div>
  <hr>
  <div class="xsmall">· 본 전표는 부가가치세법상 매입세액 공제가 가능한
     신용카드매출전표(지출증빙)입니다.</div>
  <div class="xsmall">· 이용해 주셔서 감사합니다.</div>
  <hr>
  <div style="text-align:center">{barcode('30117742-20260317', 62)}</div>
</div>"""
    docs.append(dict(no=7, slug="07_신용카드매출전표", size="SLIP",
                     title="신용카드 매출전표",
                     html=html_doc("신용카드매출전표", slip, size="SLIP",
                                   watermark="샘플", note="")))

    # 08. 현금영수증 (지출증빙용)
    cash = f"""
<div class="slip">
  <div class="ttl">현금영수증</div>
  <div style="text-align:center" class="b">[ 지출증빙용 ]</div>
  <hr>
  <div class="row"><span>가맹점명</span><span>대한사무기기(주)</span></div>
  <div class="row"><span>사업자번호</span><span>{biz_no('106810222')}</span></div>
  <div class="row"><span>대표자</span><span>최사무</span></div>
  <div class="row"><span>주소</span><span>서울 중구 을지로 100</span></div>
  <div class="row"><span>전화</span><span>02-2233-4455</span></div>
  <hr>
  <div class="row"><span>거래일시</span><span>2026/03/25 11:05:41</span></div>
  <div class="row"><span>거래구분</span><span>현금(승인거래)</span></div>
  <div class="row"><span>식별번호</span><span>{BUYER['bno']}</span></div>
  <div class="row"><span>승인번호</span><span>848112390</span></div>
  <hr>
  <div class="row"><span>품 목</span><span>A4 복사용지 외 3건</span></div>
  <div class="row"><span>공 급 가 액</span><span>{won(163636)}</span></div>
  <div class="row"><span>부 가 세</span><span>{won(16364)}</span></div>
  <div class="row b" style="font-size:10pt"><span>합 계</span><span>{won(180000)}</span></div>
  <hr>
  <div class="xsmall">· 지출증빙용 현금영수증은 사업자의 매입세액 공제 및
     지출증빙으로 사용됩니다.</div>
  <div class="xsmall">· 국세청 홈택스(hometax.go.kr)에서 발급내역을 확인할 수 있습니다.</div>
  <div class="xsmall">· 현금영수증 문의 : 국세청 상담센터 126</div>
  <hr>
  <div style="text-align:center">{barcode('848112390-CASH', 62)}</div>
</div>"""
    docs.append(dict(no=8, slug="08_현금영수증_지출증빙용", size="SLIP",
                     title="현금영수증 (지출증빙용)",
                     html=html_doc("현금영수증", cash, size="SLIP",
                                   watermark="샘플", note="")))
    return docs
