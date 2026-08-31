# -*- coding: utf-8 -*-
"""그룹 9. 첨부·보조 증빙 - 사업자등록증 사본 / 통장 사본 / 지출증빙 부착대지"""
from common import SUPPLIER, won, stamp, html_doc, barcode

CSS = """
.cert { border:2.4pt solid #2a5c3a; padding:5mm 6mm; }
.cert h1 { text-align:center; font-size:19pt; font-weight:700; letter-spacing:12px;
           margin:2mm 0 1mm; font-family:'NM',serif; }
.cert .kind { text-align:center; font-size:9.5pt; margin-bottom:4mm; }
.cert .no { text-align:center; font-size:12pt; font-weight:700; letter-spacing:3px;
            margin-bottom:4mm; }
.cert dl { margin:0; }
.cert .fld { display:flex; border-bottom:.6pt dotted #666; padding:1.6mm 0; font-size:9pt; }
.cert .fld .k { width:44mm; font-weight:700; }
.cert .fld .v { flex:1; }
.copy-mark { border:1.6pt solid #b03030; color:#b03030; font-weight:700; padding:1mm 3mm;
             display:inline-block; letter-spacing:4px; transform:rotate(-4deg); }
.bank-cover { border:1.4pt solid #16457a; border-radius:3mm; padding:4mm;
              background:linear-gradient(180deg,#f2f7fd,#ffffff); }
.bank-cover .nm { font-size:14pt; font-weight:700; color:#16457a; letter-spacing:4px; }
.acct-no { font-size:15pt; font-weight:700; letter-spacing:2px; font-family:'NG'; }
.paste { border:1.2pt dashed #888; height:52mm; background:#fbfbfb; position:relative; }
.paste span { position:absolute; inset:0; display:flex; align-items:center;
              justify-content:center; color:#999; font-size:9pt; letter-spacing:3px; }
table.grid td, table.grid th { font-size:8pt; }
"""


def build():
    docs = []

    # 48. 사업자등록증 (사본)
    f = lambda k, v: f'<div class="fld"><span class="k">{k}</span><span class="v">{v}</span></div>'
    body = f"""
<div style="text-align:right;margin-bottom:2mm"><span class="copy-mark">사 &nbsp;본</span></div>
<div class="cert">
  <div class="small">[별지 제7호서식] &lt;부가가치세법 시행규칙&gt;</div>
  <h1>사업자등록증</h1>
  <div class="kind">( 법인사업자 : 영리법인의 본점 )</div>
  <div class="no">등록번호 : {SUPPLIER['bno']}</div>
  {f('법 인 명 (단 체 명)', SUPPLIER['name'])}
  {f('대 표 자', SUPPLIER['ceo'])}
  {f('개 업 연 월 일', '2015 년 04 월 01 일')}
  {f('법 인 등 록 번 호', SUPPLIER['corpno'])}
  {f('사업장 소재지', SUPPLIER['addr'])}
  {f('본 점 소 재 지', SUPPLIER['addr'])}
  {f('사 업 의 종 류', f"<b>업태</b> {SUPPLIER['biz']} &nbsp;&nbsp; <b>종목</b> {SUPPLIER['item']}")}
  {f('발 급 사 유', '정정 (사업장 이전)')}
  {f('공동사업자', '없음')}
  {f('주류판매신고번호', '해당 없음')}
  {f('사업자 단위 과세 적용사업자 여부', '부(&nbsp;✔&nbsp;) &nbsp; 여(&nbsp;&nbsp;)')}
  {f('전자세금계산서 전용 전자우편주소', SUPPLIER['email'])}
  <div style="text-align:center;margin-top:7mm;font-size:10pt">
    2023 년 03 월 02 일</div>
  <div style="text-align:center;margin-top:4mm;font-size:15pt;font-weight:700;
       letter-spacing:8px;font-family:'NM',serif">
    ○ ○ 세 무 서 장 {stamp('세무서장',52)}</div>
  <div class="small" style="margin-top:6mm;line-height:1.6">
    ※ 사업자등록증에 기재된 내용이 사실과 다른 경우 정정신고를 하여야 합니다.<br>
    ※ 사업자등록증은 타인에게 대여할 수 없으며, 대여 시 「조세범 처벌법」에 따라 처벌받습니다.<br>
    ※ 본 사본은 거래처 제출용으로 원본과 상위 없음을 확인합니다.
  </div>
</div>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:30mm">원본대조필</td>
    <td>위 사본은 원본과 틀림없음을 확인합니다. &nbsp;&nbsp; 2026년 03월 31일 &nbsp;&nbsp;
        {SUPPLIER['name']} {stamp('원본대조',34)}</td></tr>
</table>
"""
    docs.append(dict(no=48, slug="48_사업자등록증_사본", size="A4",
                     title="사업자등록증 사본",
                     html=html_doc("사업자등록증", body, extra_css=CSS)))

    # 49. 통장 사본
    body = f"""
<div style="text-align:right;margin-bottom:2mm"><span class="copy-mark">사 &nbsp;본</span></div>
<h1 class="title sm" style="text-align:center;letter-spacing:8px">통 장 사 본</h1>
<div class="subtitle">(대금 입금계좌 확인용 · 거래처 제출용)</div>
<div class="bank-cover" style="margin-top:3mm">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <span class="nm">대 한 은 행</span>
    <span class="small">DAEHAN BANK &nbsp;|&nbsp; 기업자유예금</span></div>
  <table style="width:100%;margin-top:4mm">
  <tr><td style="width:26mm" class="small">계 좌 번 호</td>
      <td class="acct-no">123 - 456789 - 01 - 001</td></tr>
  <tr><td class="small">예 금 주</td><td class="b" style="font-size:11pt">{SUPPLIER['name']}</td></tr>
  <tr><td class="small">개 설 점</td><td>강남지점 (02-000-0000)</td></tr>
  <tr><td class="small">개 설 일</td><td class="mono">2015-04-06</td></tr>
  </table>
  <div style="margin-top:4mm;text-align:right">{barcode('12345678901001', 60)}</div>
</div>
<table class="grid" style="margin-top:3mm">
<tr><th colspan="5">통 장 거 래 면 (일부)</th></tr>
<tr><th style="width:24mm">거래일</th><th style="width:34mm">적요</th>
    <th style="width:30mm">맡기신금액</th><th style="width:30mm">찾으신금액</th><th>잔액</th></tr>
<tr><td class="c mono">2026-03-10</td><td>㈜대한상사</td><td class="num">22,000,000</td>
    <td class="num">-</td><td class="num">69,080,000</td></tr>
<tr><td class="c mono">2026-03-25</td><td>급여이체</td><td class="num">-</td>
    <td class="num">51,240,000</td><td class="num">13,522,000</td></tr>
<tr><td class="c mono">2026-03-27</td><td>㈜세종물산</td><td class="num">18,700,000</td>
    <td class="num">-</td><td class="num">29,321,000</td></tr>
<tr><td class="c mono">2026-03-31</td><td>이자</td><td class="num">42,310</td>
    <td class="num">-</td><td class="num">29,363,310</td></tr>
</table>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:30mm">용&nbsp;&nbsp;도</td>
    <td>거래대금 입금계좌 등록용 (세금계산서 발행 및 대금 수령)</td></tr>
<tr><td class="lbl">사업자등록번호</td><td class="mono">{SUPPLIER['bno']}</td></tr>
<tr><td class="lbl">원본대조필</td>
    <td>위 사본은 원본과 틀림없음을 확인합니다. &nbsp;&nbsp; 2026년 03월 31일 &nbsp;&nbsp;
        {SUPPLIER['name']} {stamp('원본대조',34)}</td></tr>
</table>
<div class="note">· 통장 사본은 계좌 진위 확인 목적으로만 사용하며, 계좌번호 외 개인정보는 마스킹 처리합니다.<br>
· 「전자금융거래법」상 통장 대여·양도는 금지되어 있습니다.</div>
"""
    docs.append(dict(no=49, slug="49_통장사본", size="A4", title="통장 사본",
                     html=html_doc("통장사본", body, extra_css=CSS)))

    # 50. 지출증빙 부착대지
    body = f"""
<h1 class="title sm" style="text-align:center;letter-spacing:8px">지 출 증 빙 부 착 대 지</h1>
<div class="subtitle">(영수증·카드전표 등 소액 증빙 첨부용) &nbsp;|&nbsp; 지출결의서 첨부서류</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:24mm">소속 부서</td><td style="width:34mm">경영지원팀</td>
    <td class="lbl" style="width:24mm">작성자</td><td style="width:26mm">김담당 {stamp('김담당',28)}</td>
    <td class="lbl" style="width:24mm">작성일</td><td class="mono">2026-03-31</td></tr>
<tr><td class="lbl">관련 문서번호</td><td class="mono">경지-2026-0331-14</td>
    <td class="lbl">증빙 매수</td><td>2매</td>
    <td class="lbl">합계 금액</td><td class="num b">412,000</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:9mm">No</th><th style="width:24mm">지출일자</th><th>적요</th>
    <th style="width:24mm">계정과목</th><th style="width:26mm">금액(원)</th>
    <th style="width:26mm">증빙 종류</th></tr>
<tr><td class="c">1</td><td class="c mono">2026-03-17</td><td>택배·퀵서비스 운송료</td>
    <td class="c">운반비</td><td class="num">28,000</td><td class="c">간이영수증</td></tr>
<tr><td class="c">2</td><td class="c mono">2026-03-25</td><td>사무용품 구입(A4용지 외)</td>
    <td class="c">소모품비</td><td class="num">384,000</td><td class="c">현금영수증</td></tr>
<tr><td class="lbl" colspan="4">합&nbsp;계</td><td class="num b">412,000</td><td>&nbsp;</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:50%">증빙 ① 부착란</th><th>증빙 ② 부착란</th></tr>
<tr><td class="paste"><span>여 기 에 영 수 증 원 본 을 부 착 하 십 시 오</span></td>
    <td class="paste"><span>여 기 에 영 수 증 원 본 을 부 착 하 십 시 오</span></td></tr>
</table>
<div class="note">
<b>[ 지출증빙 수취 기준 요약 ]</b><br>
· 건당 3만원 초과 : 세금계산서 · 계산서 · 신용카드매출전표 · 현금영수증(지출증빙용) 중 하나를 반드시 수취<br>
· 건당 3만원 이하 : 간이영수증 등 일반 영수증으로 갈음 가능<br>
· 접대비 : 건당 3만원 초과 시 반드시 법인카드(적격증빙) 사용, 경조사비는 건당 20만원 이내<br>
· 적격증빙 미수취 시 : 증빙불비가산세 2% 부과 (법인세법 제75조의5)<br>
· 증빙서류는 신고기한 종료일부터 <b>5년간</b> 보관 (국세기본법 제85조의3)
</div>
<table class="grid" style="margin-top:3mm">
<tr><th style="width:33%">작 성 자</th><th style="width:33%">검 토 (회계팀)</th><th>승 인 (부서장)</th></tr>
<tr><td class="c" style="height:20mm">{stamp('김담당',36)}</td>
    <td class="c">{stamp('이회계',36)}</td><td class="c">{stamp('박부장',36)}</td></tr>
</table>
<div class="footer-org">{SUPPLIER['name']}</div>
"""
    docs.append(dict(no=50, slug="50_지출증빙부착대지", size="A4",
                     title="지출증빙 부착대지",
                     html=html_doc("지출증빙부착대지", body, extra_css=CSS)))
    return docs
