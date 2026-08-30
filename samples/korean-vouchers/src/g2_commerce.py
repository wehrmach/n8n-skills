# -*- coding: utf-8 -*-
"""그룹 2. 상거래 증빙 - 견적서/발주서/거래명세서/청구서/입금표/검수확인서/인수증/계약서"""
from common import (SUPPLIER, BUYER, DEAL, ITEMS, won, kor_won, stamp,
                    html_doc, barcode)

CSS = """
h1.title { border-bottom:2.4pt double #111; padding-bottom:2mm; }
.hdr { display:flex; gap:4mm; margin:3mm 0 2mm; }
.hdr > div { flex:1; }
table.party td { padding:1.1mm 1.6mm; }
table.party td.lbl { width:22mm; }
.total-box { border:1.2pt solid #111; padding:2mm 3mm; margin-top:2mm;
             display:flex; justify-content:space-between; align-items:center; }
.total-box .k { font-weight:700; letter-spacing:2px; }
.total-box .v { font-size:14pt; font-weight:700; }
.terms td { font-size:8pt; }
.seal-line { display:flex; justify-content:flex-end; gap:6mm; align-items:center;
             margin-top:4mm; font-size:10pt; }
"""


def party_table(p, title, right=None, extra=()):
    """좌: 상대처 / 우: 당사 형태의 2단 정보 표"""
    rowsx = "".join(f'<tr><td class="lbl">{k}</td><td>{v}</td></tr>' for k, v in extra)
    return f"""
<table class="grid party">
<tr><td class="lbl" colspan="2" style="background:#e8e8e8">{title}</td></tr>
<tr><td class="lbl">등록번호</td><td class="mono">{p['bno']}</td></tr>
<tr><td class="lbl">상호(법인명)</td><td>{p['name']}</td></tr>
<tr><td class="lbl">대표자</td><td>{p['ceo']} {stamp('대표이사',30)}</td></tr>
<tr><td class="lbl">사업장 주소</td><td class="small">{p['addr']}</td></tr>
<tr><td class="lbl">업태 / 종목</td><td class="small">{p['biz']} / {p['item']}</td></tr>
<tr><td class="lbl">연락처</td><td class="small">TEL {p['tel']} / FAX {p.get('fax','-')}</td></tr>
{rowsx}
</table>"""


def item_table(items, headers=None, empty=3, show_vat=True):
    headers = headers or ["No", "품목 / 규격", "단위", "수량", "단가", "공급가액", "세액", "비고"]
    th = "".join(f"<th>{h}</th>" for h in headers)
    body, sup_t, vat_t = [], 0, 0
    for i, (nm, spec, unit, qty, price, sup, vat) in enumerate(items, 1):
        sup_t += sup
        vat_t += vat
        body.append(
            f'<tr><td class="c" style="width:9mm">{i}</td>'
            f'<td>{nm}<span class="xsmall" style="color:#555"> / {spec}</span></td>'
            f'<td class="c" style="width:13mm">{unit}</td>'
            f'<td class="c" style="width:14mm">{qty}</td>'
            f'<td class="num" style="width:24mm">{won(price)}</td>'
            f'<td class="num" style="width:28mm">{won(sup)}</td>'
            f'<td class="num" style="width:24mm">{won(vat)}</td>'
            f'<td style="width:22mm">&nbsp;</td></tr>')
    for _ in range(empty):
        body.append('<tr>' + '<td style="height:6mm">&nbsp;</td>' * 8 + '</tr>')
    foot = (f'<tr><td class="lbl" colspan="5">합&nbsp;&nbsp;계</td>'
            f'<td class="num b">{won(sup_t)}</td><td class="num b">{won(vat_t)}</td>'
            f'<td>&nbsp;</td></tr>')
    return f'<table class="grid"><tr>{th}</tr>{"".join(body)}{foot}</table>', sup_t, vat_t


DEAL_ITEMS = [
    ("ERP 연동 모듈 개발(설계·구현)", "SI 용역 1식", "식", "1", 8_000_000, 8_000_000, 800_000),
    ("데이터 마이그레이션 용역", "레거시 → ERP", "식", "1", 3_000_000, 3_000_000, 300_000),
    ("사용자 교육 및 매뉴얼 제작", "8H/회", "회", "3", 500_000, 1_500_000, 150_000),
]


def _doc_meta(pairs):
    return ('<table class="grid tight" style="width:74mm;margin-left:auto">'
            + "".join(f'<tr><td class="lbl" style="width:26mm">{k}</td>'
                      f'<td class="c mono">{v}</td></tr>' for k, v in pairs)
            + "</table>")


def build():
    docs = []
    tbl, sup, vat = item_table(DEAL_ITEMS)
    total = sup + vat

    # 09. 견적서
    body = f"""
<h1 class="title">견 적 서</h1>
{_doc_meta([("견적번호", DEAL['est_no']), ("견적일자", "2026-02-27"),
            ("유효기간", "견적일로부터 30일")])}
<div class="hdr">
  <div>{party_table(BUYER, "수 신 처 (공급받는자)")}</div>
  <div>{party_table(SUPPLIER, "발 신 처 (공급자)")}</div>
</div>
<p class="small">아래와 같이 견적합니다. &nbsp;— {DEAL['subject']}</p>
{tbl}
<div class="total-box"><span class="k">견적금액 합계 (부가세 포함)</span>
  <span class="v">￦ {won(total)} <span class="small">({kor_won(total)})</span></span></div>
<table class="grid terms" style="margin-top:3mm">
<tr><td class="lbl" style="width:26mm">납품기한</td><td>계약 체결일로부터 60일 이내</td>
    <td class="lbl" style="width:26mm">결제조건</td><td>검수 완료 후 익월 말일 현금 결제</td></tr>
<tr><td class="lbl">인도장소</td><td>{BUYER['addr']}</td>
    <td class="lbl">하자보증</td><td>검수일로부터 12개월</td></tr>
<tr><td class="lbl">특기사항</td><td colspan="3" class="small">
    · 상기 금액은 부가가치세 10%가 포함된 금액입니다.<br>
    · 요구사항 변경 시 별도 협의하여 견적을 재산출합니다.</td></tr>
</table>
<div class="seal-line">위와 같이 견적서를 제출합니다. &nbsp;&nbsp; 2026년 02월 27일</div>
<div class="footer-org">{SUPPLIER['name']} &nbsp; 대표이사 {SUPPLIER['ceo']} {stamp('한빛테크',44)}</div>
"""
    docs.append(dict(no=9, slug="09_견적서", size="A4", title="견적서",
                     html=html_doc("견적서", body, extra_css=CSS)))

    # 10. 발주서(주문서)
    body = f"""
<h1 class="title">발 주 서</h1>
<div class="subtitle">PURCHASE ORDER</div>
{_doc_meta([("발주번호", DEAL['po_no']), ("발주일자", "2026-03-02"),
            ("관련견적", DEAL['est_no'])])}
<div class="hdr">
  <div>{party_table(SUPPLIER, "수 신 (공급자)")}</div>
  <div>{party_table(BUYER, "발 주 처 (발주자)")}</div>
</div>
<p class="small">귀사의 견적({DEAL['est_no']})에 의거 아래와 같이 발주합니다.</p>
{tbl}
<div class="total-box"><span class="k">발주금액 합계 (부가세 포함)</span>
  <span class="v">￦ {won(total)}</span></div>
<table class="grid terms" style="margin-top:3mm">
<tr><td class="lbl" style="width:26mm">납기일</td><td>2026-03-31</td>
    <td class="lbl" style="width:26mm">납품장소</td><td>{BUYER['addr']}</td></tr>
<tr><td class="lbl">대금지급</td><td>검수 후 세금계산서 수취, 익월 25일 계좌이체</td>
    <td class="lbl">담당자</td><td>구매팀 이발주 과장 / 031-777-8812</td></tr>
<tr><td class="lbl">발주조건</td><td colspan="3" class="small">
    · 납기 지연 시 지체상금(1일당 발주금액의 0.1%)을 부과할 수 있습니다.<br>
    · 검수 불합격 품목은 재작업 또는 반품 처리합니다.</td></tr>
</table>
<div class="footer-org">{BUYER['name']} &nbsp; 대표이사 {BUYER['ceo']} {stamp('미래유통',44)}</div>
"""
    docs.append(dict(no=10, slug="10_발주서", size="A4", title="발주서(주문서)",
                     html=html_doc("발주서", body, extra_css=CSS)))

    # 11. 거래명세서
    tbl2, sup2, vat2 = item_table(
        [("ERP 연동 모듈 개발(설계·구현)", "SI 용역 1식", "식", "1", 8_000_000, 8_000_000, 800_000),
         ("데이터 마이그레이션 용역", "레거시 → ERP", "식", "1", 3_000_000, 3_000_000, 300_000),
         ("사용자 교육 및 매뉴얼 제작", "8H/회", "회", "3", 500_000, 1_500_000, 150_000)],
        empty=5)
    body = f"""
<h1 class="title sm">거 래 명 세 서</h1>
<div class="subtitle">(공급받는자 보관용) &nbsp;|&nbsp; 거래기간 2026-03-01 ~ 2026-03-31</div>
{_doc_meta([("명세서번호", "TS-2026-0331-07"), ("작성일자", DEAL['date']),
            ("관련 발주", DEAL['po_no'])])}
<div class="hdr">
  <div>{party_table(SUPPLIER, "공 급 자")}</div>
  <div>{party_table(BUYER, "공 급 받 는 자")}</div>
</div>
{tbl2}
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:24mm">전월이월</td><td class="num" style="width:30mm">0</td>
    <td class="lbl" style="width:24mm">당월매출</td><td class="num" style="width:30mm">{won(total)}</td>
    <td class="lbl" style="width:24mm">당월입금</td><td class="num" style="width:30mm">0</td>
    <td class="lbl" style="width:24mm">미수잔액</td><td class="num b">{won(total)}</td></tr>
</table>
<div class="total-box"><span class="k">거래금액 합계</span>
  <span class="v">￦ {won(total)}</span></div>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:26mm">입금계좌</td>
    <td>{SUPPLIER['bank']} {SUPPLIER['acct']} (예금주 : {SUPPLIER['name']})</td></tr>
<tr><td class="lbl">인수확인</td>
    <td>상기 물품/용역을 정히 인수하였음. &nbsp;&nbsp; 인수자 : 정인수 (서명/인) {stamp('정인수',32)}</td></tr>
</table>
<div class="footer-org">{SUPPLIER['name']} {stamp('한빛테크',44)}</div>
"""
    docs.append(dict(no=11, slug="11_거래명세서", size="A4", title="거래명세서",
                     html=html_doc("거래명세서", body, extra_css=CSS)))

    # 12. 청구서
    body = f"""
<h1 class="title">청 구 서</h1>
<div class="subtitle">INVOICE (대금 청구)</div>
{_doc_meta([("청구번호", "IV-2026-0331-02"), ("청구일자", DEAL['date']),
            ("결제기한", "2026-04-25")])}
<div class="hdr">
  <div>{party_table(BUYER, "청 구 처 (지급인)")}</div>
  <div>{party_table(SUPPLIER, "청 구 인 (수취인)")}</div>
</div>
<p class="small">아래와 같이 대금을 청구하오니 기일 내 납입하여 주시기 바랍니다.</p>
{tbl}
<div class="total-box"><span class="k">청구금액 (부가세 포함)</span>
  <span class="v">￦ {won(total)}</span></div>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:26mm">입금계좌</td>
    <td class="b">{SUPPLIER['bank']} {SUPPLIER['acct']} &nbsp;|&nbsp; 예금주 {SUPPLIER['name']}</td></tr>
<tr><td class="lbl">세금계산서</td><td>2026-03-31자 전자세금계산서 발행 완료 (승인번호 {DEAL['ti_no']})</td></tr>
<tr><td class="lbl">유의사항</td><td class="small">
    · 결제기한 경과 시 지연이자(연 6%)가 가산될 수 있습니다.<br>
    · 입금 시 반드시 청구번호를 기재하여 주시기 바랍니다.</td></tr>
</table>
<div class="footer-org">{SUPPLIER['name']} &nbsp; 대표이사 {SUPPLIER['ceo']} {stamp('한빛테크',44)}</div>
"""
    docs.append(dict(no=12, slug="12_청구서", size="A4", title="청구서(인보이스)",
                     html=html_doc("청구서", body, extra_css=CSS)))

    # 13. 입금표
    body = f"""
<h1 class="title">입 금 표</h1>
<div class="subtitle">(공급받는자 보관용)</div>
<table class="grid" style="margin-top:4mm">
<tr><td class="lbl" style="width:28mm">NO.</td><td class="mono" style="width:52mm">RC-2026-0425-11</td>
    <td class="lbl" style="width:28mm">입금일자</td><td class="mono">2026년 04월 25일</td></tr>
<tr><td class="lbl">입금자(지급인)</td><td>{BUYER['name']} ({BUYER['bno']})</td>
    <td class="lbl">입금방법</td><td>계좌이체</td></tr>
<tr><td class="lbl">수령자(공급자)</td><td>{SUPPLIER['name']} ({SUPPLIER['bno']})</td>
    <td class="lbl">입금은행</td><td>{SUPPLIER['bank']} {SUPPLIER['acct']}</td></tr>
</table>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:28mm;height:16mm">금&nbsp;&nbsp;&nbsp;액</td>
    <td class="c" style="font-size:16pt;font-weight:700">
      ￦ {won(total)}<br><span style="font-size:10pt">({kor_won(total)})</span></td></tr>
<tr><td class="lbl">내&nbsp;&nbsp;&nbsp;역</td>
    <td>{DEAL['subject']} 대금 (2026-03-31자 세금계산서분)</td></tr>
<tr><td class="lbl">비&nbsp;&nbsp;&nbsp;고</td>
    <td class="small">공급가액 {won(sup)} + 부가세 {won(vat)} = {won(total)}</td></tr>
</table>
<div class="sign-area" style="margin-top:8mm">
  위 금액을 정히 <b>영수</b>합니다.<br>
  2026년 04월 25일
</div>
<div class="footer-org">{SUPPLIER['name']} &nbsp; 대표이사 {SUPPLIER['ceo']} {stamp('한빛테크',46)}</div>
"""
    docs.append(dict(no=13, slug="13_입금표", size="A5", title="입금표",
                     html=html_doc("입금표", body, size="A5", extra_css=CSS)))

    # 14. 검수(납품)확인서
    body = f"""
<h1 class="title sm">납 품 · 검 수 확 인 서</h1>
{_doc_meta([("검수번호", "IN-2026-0331-05"), ("검수일자", "2026-03-31"),
            ("관련 발주", DEAL['po_no'])])}
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:26mm">공급자</td><td>{SUPPLIER['name']} ({SUPPLIER['bno']})</td>
    <td class="lbl" style="width:26mm">발주자</td><td>{BUYER['name']} ({BUYER['bno']})</td></tr>
<tr><td class="lbl">계약(발주)명</td><td colspan="3">{DEAL['subject']}</td></tr>
<tr><td class="lbl">계약금액</td><td class="b">￦ {won(total)} (부가세 포함)</td>
    <td class="lbl">납품기한</td><td>2026-03-31</td></tr>
</table>
<table class="grid" style="margin-top:3mm">
<tr><th style="width:9mm">No</th><th>검수 항목</th><th style="width:20mm">기준</th>
    <th style="width:18mm">결과</th><th style="width:34mm">비고</th></tr>
<tr><td class="c">1</td><td>ERP 연동 모듈 기능 요건 충족 여부</td><td class="c">요구사항정의서</td>
    <td class="c b">합격</td><td class="small">전 항목 시험 통과</td></tr>
<tr><td class="c">2</td><td>데이터 마이그레이션 정합성 (건수/금액 대사)</td><td class="c">100%</td>
    <td class="c b">합격</td><td class="small">오차 0건</td></tr>
<tr><td class="c">3</td><td>사용자 교육 실시 및 매뉴얼 제출</td><td class="c">3회 / 1종</td>
    <td class="c b">합격</td><td class="small">교육일지 첨부</td></tr>
<tr><td class="c">4</td><td>산출물 인도 (소스코드, 설계서)</td><td class="c">일체</td>
    <td class="c b">합격</td><td class="small">USB 및 형상서버 등록</td></tr>
<tr><td class="lbl" colspan="3">종 합 판 정</td><td class="c b" style="font-size:11pt">합&nbsp;격</td>
    <td class="small">대금 지급 가능</td></tr>
</table>
<div class="note">위와 같이 납품물에 대한 검수를 실시하고 그 결과를 확인합니다.</div>
<table class="grid" style="margin-top:5mm">
<tr><th style="width:33%">검 수 자</th><th style="width:33%">검 수 입 회 자</th><th>승 인 자</th></tr>
<tr><td class="c" style="height:24mm">전산팀 정검수 대리<br>{stamp('정검수',38)}</td>
    <td class="c">구매팀 이발주 과장<br>{stamp('이발주',38)}</td>
    <td class="c">경영지원본부장 한승인<br>{stamp('한승인',38)}</td></tr>
</table>
<div class="footer-org">{BUYER['name']}</div>
"""
    docs.append(dict(no=14, slug="14_납품검수확인서", size="A4", title="납품·검수확인서",
                     html=html_doc("검수확인서", body, extra_css=CSS)))

    # 15. 물품 인수증 / 거래 운송장
    body = f"""
<h1 class="title sm">물 품 인 수 증</h1>
<div class="subtitle">(운송장 겸용 · 수하인 보관용)</div>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:24mm">운송장번호</td>
    <td class="mono b" style="width:46mm">6412-8890-3371</td>
    <td rowspan="4" class="c" style="width:66mm">{barcode('641288903371', 58)}</td></tr>
<tr><td class="lbl">출고일자</td><td class="mono">2026-03-30 15:40</td></tr>
<tr><td class="lbl">운송사</td><td>대한물류(주) / 기사 김운송 010-0000-0000</td></tr>
<tr><td class="lbl">배송구분</td><td>일반 화물 (착불 아님 · 선불)</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:24mm">보내는 분</td>
    <td>{SUPPLIER['name']} / 서울 강남구 테헤란로 123 / 02-555-1234</td></tr>
<tr><td class="lbl">받는 분</td>
    <td>{BUYER['name']} 물류팀 / {BUYER['addr']} / 031-777-8800</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:9mm">No</th><th>품명</th><th style="width:20mm">규격</th>
    <th style="width:16mm">수량</th><th style="width:20mm">단위</th><th style="width:34mm">비고</th></tr>
<tr><td class="c">1</td><td>서버 장비 (구축용)</td><td class="c">2U Rack</td>
    <td class="c">2</td><td class="c">대</td><td class="small">파손주의</td></tr>
<tr><td class="c">2</td><td>산출물 문서 일체 (설계서·매뉴얼)</td><td class="c">A4 바인더</td>
    <td class="c">5</td><td class="c">권</td><td>&nbsp;</td></tr>
<tr><td class="c">3</td><td>소스코드 저장매체</td><td class="c">USB 256GB</td>
    <td class="c">1</td><td class="c">EA</td><td class="small">봉인</td></tr>
<tr><td class="lbl" colspan="3">합&nbsp;계</td><td class="c b">8</td><td colspan="2">&nbsp;</td></tr>
</table>
<div class="sign-area" style="margin-top:6mm">
  상기 물품을 이상 없이 <b>인수</b>하였음을 확인합니다.<br>
  2026년 03월 31일<br>
  인수자 : {BUYER['name']} 물류팀 &nbsp; 정인수 (서명) {stamp('정인수',40)}
</div>
"""
    docs.append(dict(no=15, slug="15_물품인수증_운송장", size="A5",
                     title="물품인수증(운송장)",
                     html=html_doc("물품인수증", body, size="A5", extra_css=CSS)))

    # 16. 용역계약서
    body = f"""
<h1 class="title sm">용 역 계 약 서</h1>
<div class="subtitle">계약번호 : CT-2026-0032</div>
<p class="small" style="margin-top:3mm">
{BUYER['name']}(이하 "갑"이라 한다)과 {SUPPLIER['name']}(이하 "을"이라 한다)은
아래 용역의 수행에 관하여 다음과 같이 계약을 체결한다.</p>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:28mm">계약명</td><td colspan="3">{DEAL['subject']}</td></tr>
<tr><td class="lbl">계약금액</td><td class="b">￦ {won(total)} (공급가액 {won(sup)} + 부가세 {won(vat)})</td>
    <td class="lbl" style="width:24mm">한글표기</td><td>{kor_won(total)}</td></tr>
<tr><td class="lbl">계약기간</td><td>2026-03-02 ~ 2026-03-31</td>
    <td class="lbl">하자보수</td><td>검수일로부터 12개월</td></tr>
<tr><td class="lbl">대금지급</td><td colspan="3">검수 완료 후 세금계산서 수취, 익월 25일 계좌이체 (선급금 없음)</td></tr>
</table>
<div class="myeong" style="margin-top:3mm;font-size:9pt;line-height:1.7">
<b>제1조 (목적)</b> 본 계약은 "갑"이 "을"에게 위탁하는 용역의 수행 조건과 양 당사자의 권리·의무를 정함을 목적으로 한다.<br>
<b>제2조 (용역의 범위)</b> 용역의 범위는 별첨 과업지시서 및 요구사항정의서에 따른다.<br>
<b>제3조 (계약금액 및 지급)</b> ① 계약금액은 위 표와 같다. ② "갑"은 검수 합격 후 "을"이 발행한 세금계산서를 수취하고 익월 25일에 대금을 지급한다.<br>
<b>제4조 (검수)</b> "갑"은 납품일로부터 7일 이내에 검수를 완료하고 그 결과를 "을"에게 통지한다.<br>
<b>제5조 (지체상금)</b> "을"이 납기를 준수하지 못한 경우 지연 1일당 계약금액의 1,000분의 1을 지체상금으로 "갑"에게 지급한다.<br>
<b>제6조 (비밀유지)</b> 양 당사자는 본 계약의 수행 과정에서 알게 된 상대방의 영업비밀을 계약 종료 후 3년간 제3자에게 누설하지 아니한다.<br>
<b>제7조 (지식재산권)</b> 본 용역의 산출물에 대한 지식재산권은 대금 완납 시 "갑"에게 귀속한다. 다만 "을"의 기존 보유 기술은 예외로 한다.<br>
<b>제8조 (계약의 해지)</b> 당사자 일방이 본 계약을 위반하고 시정요구 후 14일 이내에 시정하지 아니한 때에는 상대방은 계약을 해지할 수 있다.<br>
<b>제9조 (분쟁의 해결)</b> 본 계약과 관련한 분쟁은 상호 협의로 해결하되, 협의가 이루어지지 않을 경우 "갑"의 주소지 관할 법원을 전속관할로 한다.<br>
<b>제10조 (기타)</b> 본 계약에 정하지 아니한 사항은 관계 법령 및 일반 상관례에 따른다.
</div>
<p class="small" style="margin-top:3mm">본 계약의 성립을 증명하기 위하여 계약서 2통을 작성하여
"갑"과 "을"이 기명날인 후 각 1통씩 보관한다.</p>
<div class="sign-area">2026년 03월 02일</div>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:50%">"갑" (발주자)</th><th>"을" (수급자)</th></tr>
<tr><td style="height:30mm" class="small">
     상호 : {BUYER['name']}<br>사업자등록번호 : {BUYER['bno']}<br>
     주소 : {BUYER['addr']}<br>대표이사 : {BUYER['ceo']} (인) {stamp('미래유통',40)}</td>
    <td class="small">
     상호 : {SUPPLIER['name']}<br>사업자등록번호 : {SUPPLIER['bno']}<br>
     주소 : {SUPPLIER['addr']}<br>대표이사 : {SUPPLIER['ceo']} (인) {stamp('한빛테크',40)}</td></tr>
</table>
"""
    docs.append(dict(no=16, slug="16_용역계약서", size="A4", title="용역계약서",
                     html=html_doc("용역계약서", body, extra_css=CSS)))
    return docs
