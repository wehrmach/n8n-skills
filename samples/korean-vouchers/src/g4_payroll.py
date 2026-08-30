# -*- coding: utf-8 -*-
"""그룹 4. 인사·급여 증빙 - 급여명세서/원천징수영수증/지급명세서/4대보험 고지서"""
from common import SUPPLIER, won, kor_won, stamp, html_doc, biz_no, barcode

CSS = """
h1.title { border-top:2pt solid #111; border-bottom:2pt solid #111; padding:2mm 0; }
.form-no { font-size:7pt; color:#444; border:.7pt solid #666; padding:.6mm 1.6mm;
           display:inline-block; }
.sec { background:#e9edf5; font-weight:700; padding:1mm 2mm; border:.7pt solid #222;
       border-bottom:0; margin-top:2.5mm; font-size:8.5pt; }
table.grid td, table.grid th { font-size:8pt; }
.mask { letter-spacing:1px; }
"""

EMP = dict(name="이근로", rrn="850315-1******", pos="영업팀 과장", no="2019-0142",
           addr="서울특별시 송파구 올림픽로 300, 101동 1502호",
           join="2019-03-04", bank="대한은행 555-0101-2233")


def build():
    docs = []

    # 23. 급여명세서
    pay = [("기본급", 4_200_000), ("직책수당", 300_000), ("식대(비과세)", 200_000),
           ("자가운전보조금(비과세)", 200_000), ("연장근로수당", 412_500), ("상여금", 0)]
    ded = [("국민연금", 265_500), ("건강보험", 209_130), ("장기요양보험", 27_070),
           ("고용보험", 44_325), ("소득세", 253_060), ("지방소득세", 25_300)]
    gross = sum(v for _, v in pay)
    dedt = sum(v for _, v in ded)
    net = gross - dedt
    prow = "".join(f'<tr><td>{k}</td><td class="num">{won(v)}</td></tr>' for k, v in pay)
    prow += '<tr><td>&nbsp;</td><td>&nbsp;</td></tr>' * (len(ded) - len(pay))
    drow = "".join(f'<tr><td>{k}</td><td class="num">{won(v)}</td></tr>' for k, v in ded)
    body = f"""
<h1 class="title sm">급 여 명 세 서</h1>
<div class="subtitle">2026년 3월분 (지급일 : 2026-03-25) &nbsp;|&nbsp;
  근로기준법 제48조 제2항에 따른 임금명세서</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:22mm">성명</td><td style="width:32mm">{EMP['name']}</td>
    <td class="lbl" style="width:22mm">사번</td><td style="width:30mm">{EMP['no']}</td>
    <td class="lbl" style="width:22mm">소속/직급</td><td>{EMP['pos']}</td></tr>
<tr><td class="lbl">입사일</td><td class="mono">{EMP['join']}</td>
    <td class="lbl">급여계산기간</td><td colspan="3" class="mono">2026-03-01 ~ 2026-03-31</td></tr>
<tr><td class="lbl">지급은행</td><td colspan="5">{EMP['bank']} (예금주 {EMP['name']})</td></tr>
</table>
<table style="width:100%;margin-top:2mm"><tr>
<td style="width:49%;vertical-align:top">
  <table class="grid"><tr><th colspan="2">지 급 항 목</th></tr>
  <tr><th style="width:60%">항목</th><th>금액(원)</th></tr>
  {prow}
  <tr><td class="lbl">지급액 계</td><td class="num b">{won(gross)}</td></tr></table>
</td>
<td style="width:2%"></td>
<td style="width:49%;vertical-align:top">
  <table class="grid"><tr><th colspan="2">공 제 항 목</th></tr>
  <tr><th style="width:60%">항목</th><th>금액(원)</th></tr>
  {drow}
  <tr><td class="lbl">공제액 계</td><td class="num b">{won(dedt)}</td></tr></table>
</td></tr></table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm;height:12mm">실 지 급 액</td>
    <td class="c b" style="font-size:14pt">￦ {won(net)}
      <span class="small">({kor_won(net)})</span></td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th colspan="6">계 산 방 법 (근로기준법 시행령 제27조의2)</th></tr>
<tr><td class="lbl" style="width:26mm">연장근로수당</td>
    <td colspan="5" class="small">통상시급 20,096원 × 1.5 × 13.7시간 = 412,500원</td></tr>
<tr><td class="lbl">비과세 항목</td>
    <td colspan="5" class="small">식대 200,000원(월 20만원 한도) + 자가운전보조금 200,000원(월 20만원 한도)
      = 400,000원 (소득세법 제12조)</td></tr>
<tr><td class="lbl">소정근로시간</td><td style="width:24mm">209시간</td>
    <td class="lbl" style="width:22mm">연장</td><td style="width:20mm">13.7시간</td>
    <td class="lbl" style="width:20mm">야간/휴일</td><td>0시간</td></tr>
</table>
<div class="note">· 4대보험료는 2026년도 요율 기준으로 산정되었습니다.<br>
· 명세서에 이의가 있는 경우 지급일로부터 14일 이내 경영지원팀으로 문의 바랍니다.</div>
<div class="footer-org">{SUPPLIER['name']} &nbsp; 대표이사 {SUPPLIER['ceo']} {stamp('한빛테크',42)}</div>
"""
    docs.append(dict(no=23, slug="23_급여명세서", size="A4", title="급여명세서",
                     html=html_doc("급여명세서", body, extra_css=CSS)))

    # 24. 근로소득 원천징수영수증
    body = f"""
<div style="display:flex;justify-content:space-between;align-items:flex-start">
  <span class="form-no">[별지 제24호서식(1)] &lt;개정 준용&gt;</span>
  <span class="form-no">(8쪽 중 제1쪽)</span></div>
<h1 class="title sm" style="margin-top:1mm">근로소득 원천징수영수증</h1>
<div class="subtitle">( [&nbsp;✔&nbsp;] 소득자 보관용 &nbsp; [&nbsp;&nbsp;] 발행자 보관용 &nbsp;
  [&nbsp;&nbsp;] 발행자 보고용 ) &nbsp;|&nbsp; 관리번호 : 2026-KR-00142</div>
<div class="sec">① 징 수 의 무 자</div>
<table class="grid">
<tr><td class="lbl" style="width:26mm">법인명(상호)</td><td style="width:56mm">{SUPPLIER['name']}</td>
    <td class="lbl" style="width:26mm">대표자(성명)</td><td>{SUPPLIER['ceo']}</td></tr>
<tr><td class="lbl">사업자등록번호</td><td class="mono">{SUPPLIER['bno']}</td>
    <td class="lbl">법인등록번호</td><td class="mono">{SUPPLIER['corpno']}</td></tr>
<tr><td class="lbl">소재지(주소)</td><td colspan="3">{SUPPLIER['addr']}</td></tr>
</table>
<div class="sec">② 소 득 자</div>
<table class="grid">
<tr><td class="lbl" style="width:26mm">성명</td><td style="width:56mm">{EMP['name']}</td>
    <td class="lbl" style="width:26mm">주민등록번호</td><td class="mono mask">{EMP['rrn']}</td></tr>
<tr><td class="lbl">주소</td><td colspan="3">{EMP['addr']}</td></tr>
<tr><td class="lbl">귀속연도</td><td>2025년</td>
    <td class="lbl">근무기간</td><td class="mono">2025-01-01 ~ 2025-12-31</td></tr>
</table>
<div class="sec">③ 근무처별 소득명세</div>
<table class="grid">
<tr><th style="width:34%">구분</th><th>주(현) 근무지</th><th>종(전) 근무지</th><th>합계</th></tr>
<tr><td class="lbl l">근무처명</td><td class="c">{SUPPLIER['name']}</td><td class="c">-</td><td class="c">-</td></tr>
<tr><td class="lbl l">사업자등록번호</td><td class="c mono">{SUPPLIER['bno']}</td><td class="c">-</td><td>&nbsp;</td></tr>
<tr><td class="lbl l">⑯ 급여</td><td class="num">54,000,000</td><td class="num">0</td><td class="num b">54,000,000</td></tr>
<tr><td class="lbl l">⑰ 상여</td><td class="num">6,000,000</td><td class="num">0</td><td class="num b">6,000,000</td></tr>
<tr><td class="lbl l">⑱ 인정상여</td><td class="num">0</td><td class="num">0</td><td class="num">0</td></tr>
<tr><td class="lbl l">⑳ 계 (총급여)</td><td class="num b">60,000,000</td><td class="num">0</td><td class="num b">60,000,000</td></tr>
<tr><td class="lbl l">비과세소득 계</td><td class="num">4,800,000</td><td class="num">0</td><td class="num b">4,800,000</td></tr>
</table>
<div class="sec">④ 세 액 명 세</div>
<table class="grid">
<tr><th style="width:34%">구분</th><th>소득세</th><th>지방소득세</th><th>농어촌특별세</th></tr>
<tr><td class="lbl l">⑬ 결정세액</td><td class="num">2,184,600</td><td class="num">218,460</td><td class="num">0</td></tr>
<tr><td class="lbl l">기납부세액 (주현 근무지)</td><td class="num">2,596,800</td><td class="num">259,680</td><td class="num">0</td></tr>
<tr><td class="lbl l">기납부세액 (종전 근무지)</td><td class="num">0</td><td class="num">0</td><td class="num">0</td></tr>
<tr><td class="lbl l b">차감징수세액 (환급△)</td><td class="num b red">△412,200</td>
    <td class="num b red">△41,220</td><td class="num">0</td></tr>
</table>
<div class="sec">⑤ 주요 공제 내역 (요약)</div>
<table class="grid">
<tr><td class="lbl" style="width:26mm">근로소득공제</td><td class="num" style="width:26mm">12,750,000</td>
    <td class="lbl" style="width:26mm">인적공제</td><td class="num" style="width:26mm">6,000,000</td>
    <td class="lbl" style="width:26mm">연금보험료공제</td><td class="num">2,700,000</td></tr>
<tr><td class="lbl">보험료 세액공제</td><td class="num">120,000</td>
    <td class="lbl">의료비 세액공제</td><td class="num">184,500</td>
    <td class="lbl">근로소득 세액공제</td><td class="num">660,000</td></tr>
</table>
<div class="note">위의 원천징수액(근로소득)을 정히 영수(지급)합니다. &nbsp;&nbsp; 2026년 02월 28일</div>
<div class="footer-org" style="font-size:11pt">
  징수의무자 {SUPPLIER['name']} (서명 또는 인) {stamp('한빛테크',40)}</div>
<div class="c small" style="margin-top:2mm">○ ○ 세 무 서 장 &nbsp;귀하</div>
"""
    docs.append(dict(no=24, slug="24_근로소득원천징수영수증", size="A4",
                     title="근로소득 원천징수영수증",
                     html=html_doc("근로소득원천징수영수증", body, extra_css=CSS)))

    # 25. 사업소득 원천징수영수증 (3.3%)
    amt = 3_000_000
    it, lt = int(amt * 0.03), int(amt * 0.003)
    body = f"""
<div style="display:flex;justify-content:space-between">
  <span class="form-no">[별지 제23호서식(2)] 준용</span><span class="form-no">(앞쪽)</span></div>
<h1 class="title sm" style="margin-top:1mm">거주자의 사업소득 원천징수영수증</h1>
<div class="subtitle">( [&nbsp;✔&nbsp;] 소득자 보관용 &nbsp; [&nbsp;&nbsp;] 발행자 보관용 ) &nbsp;|&nbsp;
  일련번호 2026-BS-0087</div>
<div class="sec">① 징수의무자</div>
<table class="grid">
<tr><td class="lbl" style="width:28mm">사업자등록번호</td><td class="mono" style="width:44mm">{SUPPLIER['bno']}</td>
    <td class="lbl" style="width:24mm">법인명(상호)</td><td>{SUPPLIER['name']}</td></tr>
<tr><td class="lbl">대표자(성명)</td><td>{SUPPLIER['ceo']}</td>
    <td class="lbl">소재지</td><td class="small">{SUPPLIER['addr']}</td></tr>
</table>
<div class="sec">② 소득자</div>
<table class="grid">
<tr><td class="lbl" style="width:28mm">성명</td><td style="width:44mm">최프리 (프리랜서)</td>
    <td class="lbl" style="width:24mm">주민등록번호</td><td class="mono mask">910722-2******</td></tr>
<tr><td class="lbl">주소</td><td colspan="3">서울특별시 마포구 월드컵북로 100, 5층</td></tr>
<tr><td class="lbl">사업자등록번호</td><td>(해당 없음 - 인적용역)</td>
    <td class="lbl">내·외국인</td><td>내국인</td></tr>
</table>
<div class="sec">③ 지급 및 원천징수 명세</div>
<table class="grid">
<tr><th style="width:16mm">귀속<br>연월</th><th style="width:18mm">지급<br>연월일</th>
    <th style="width:20mm">업종<br>코드</th><th>지급 내용</th>
    <th style="width:26mm">지급총액</th><th style="width:22mm">소득세</th>
    <th style="width:22mm">지방소득세</th><th style="width:22mm">차인지급액</th></tr>
<tr><td class="c mono">2026-03</td><td class="c mono">2026-03-25</td><td class="c mono">940909</td>
    <td>UI/UX 디자인 외주 용역</td><td class="num">{won(amt)}</td>
    <td class="num">{won(it)}</td><td class="num">{won(lt)}</td>
    <td class="num b">{won(amt - it - lt)}</td></tr>
<tr><td class="lbl" colspan="4">합&nbsp;&nbsp;계</td><td class="num b">{won(amt)}</td>
    <td class="num b">{won(it)}</td><td class="num b">{won(lt)}</td>
    <td class="num b">{won(amt - it - lt)}</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:28mm">원천징수 세율</td>
    <td>소득세 3% + 지방소득세 0.3% = <b>3.3%</b> (소득세법 제129조 제1항 제3호)</td></tr>
<tr><td class="lbl">납부(예정)일</td><td class="mono">2026-04-10 (원천징수이행상황신고서와 함께 신고·납부)</td></tr>
</table>
<div class="note">위의 원천징수세액(사업소득)을 정히 영수(지급)합니다. &nbsp;&nbsp; 2026년 03월 25일</div>
<div class="footer-org" style="font-size:11pt">
  징수의무자 {SUPPLIER['name']} (서명 또는 인) {stamp('한빛테크',40)}</div>
<div class="c small" style="margin-top:2mm">○ ○ 세 무 서 장 &nbsp;귀하</div>
"""
    docs.append(dict(no=25, slug="25_사업소득원천징수영수증_3.3", size="A4",
                     title="사업소득 원천징수영수증 (3.3%)",
                     html=html_doc("사업소득원천징수영수증", body, extra_css=CSS)))

    # 26. 일용근로소득 지급명세서
    day = [("김일용", "880101-1******", 8, 160_000, 1_280_000),
           ("박일용", "920512-1******", 6, 160_000, 960_000),
           ("최일용", "790830-1******", 10, 170_000, 1_700_000)]
    rows = ""
    ti = tl = tg = 0
    for i, (nm, rrn, dcnt, dw, gross) in enumerate(day, 1):
        # 일용근로소득세 = (일급 - 15만원) × 6% × (1 - 55%)
        tax = int(max(0, (dw - 150_000)) * 0.06 * 0.45) * dcnt
        loc = int(tax * 0.1)
        ti += tax; tl += loc; tg += gross
        rows += (f'<tr><td class="c">{i}</td><td class="c">{nm}</td>'
                 f'<td class="c mono mask">{rrn}</td><td class="c">{dcnt}</td>'
                 f'<td class="num">{won(dw)}</td><td class="num">{won(gross)}</td>'
                 f'<td class="num">{won(tax)}</td><td class="num">{won(loc)}</td>'
                 f'<td class="num">{won(gross - tax - loc)}</td></tr>')
    body = f"""
<div style="display:flex;justify-content:space-between">
  <span class="form-no">[별지 제24호서식(4)] 준용</span><span class="form-no">(앞쪽)</span></div>
<h1 class="title sm" style="margin-top:1mm">일용근로소득 지급명세서</h1>
<div class="subtitle">(지급자 보관용) &nbsp;|&nbsp; 귀속연월 2026년 03월 &nbsp;|&nbsp;
  제출기한 2026-04-30</div>
<div class="sec">① 원천징수의무자(지급자)</div>
<table class="grid">
<tr><td class="lbl" style="width:28mm">사업자등록번호</td><td class="mono" style="width:44mm">{SUPPLIER['bno']}</td>
    <td class="lbl" style="width:24mm">법인명(상호)</td><td>{SUPPLIER['name']}</td></tr>
<tr><td class="lbl">사업장 소재지</td><td colspan="3" class="small">{SUPPLIER['addr']}</td></tr>
</table>
<div class="sec">② 일용근로자별 지급 명세</div>
<table class="grid">
<tr><th style="width:9mm">No</th><th style="width:22mm">성명</th>
    <th style="width:30mm">주민등록번호</th><th style="width:16mm">근로<br>일수</th>
    <th style="width:24mm">일급여액</th><th style="width:26mm">총지급액</th>
    <th style="width:22mm">소득세</th><th style="width:22mm">지방<br>소득세</th>
    <th style="width:26mm">차인지급액</th></tr>
{rows}
<tr><td class="lbl" colspan="5">합&nbsp;&nbsp;계</td><td class="num b">{won(tg)}</td>
    <td class="num b">{won(ti)}</td><td class="num b">{won(tl)}</td>
    <td class="num b">{won(tg - ti - tl)}</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:28mm">세액 계산식</td><td class="small">
   (일급여액 － 근로소득공제 150,000원) × 6% × (1 － 근로소득세액공제 55%)<br>
   ※ 산출세액이 1,000원 미만인 경우 소액부징수(소득세법 제86조)로 징수하지 않음</td></tr>
<tr><td class="lbl">근로내용</td><td>물류창고 상하차 및 재고실사 보조 (2026-03-02 ~ 2026-03-20)</td></tr>
</table>
<div class="note">위와 같이 일용근로소득을 지급하였음을 확인합니다. &nbsp;&nbsp; 2026년 03월 31일</div>
<div class="footer-org" style="font-size:11pt">
  {SUPPLIER['name']} (서명 또는 인) {stamp('한빛테크',40)}</div>
"""
    docs.append(dict(no=26, slug="26_일용근로소득지급명세서", size="A4",
                     title="일용근로소득 지급명세서",
                     html=html_doc("일용근로소득지급명세서", body, extra_css=CSS)))

    # 27. 4대보험 보험료 고지서(납부확인서)
    ins = [("국민연금", 4_425_000, "9.0%", 1_991_250, 1_991_250, 3_982_500),
           ("건강보험", 4_425_000, "7.09%", 1_568_662, 1_568_663, 3_137_325),
           ("장기요양보험", 3_137_325, "12.95%", 203_140, 203_140, 406_280),
           ("고용보험", 4_425_000, "1.8%", 398_250, 553_125, 951_375),
           ("산재보험", 4_425_000, "0.73%", 0, 323_025, 323_025)]
    rows = ""
    te = tr_ = tt = 0
    for nm, base, rate, emp, cor, tot in ins:
        te += emp; tr_ += cor; tt += tot
        rows += (f'<tr><td class="c b">{nm}</td><td class="num">{won(base)}</td>'
                 f'<td class="c">{rate}</td><td class="num">{won(emp)}</td>'
                 f'<td class="num">{won(cor)}</td><td class="num b">{won(tot)}</td></tr>')
    body = f"""
<h1 class="title sm">4대 사회보험료 고지서 (납부확인서)</h1>
<div class="subtitle">2026년 3월분 &nbsp;|&nbsp; 납부기한 2026-04-10 &nbsp;|&nbsp;
  고지번호 26-03-0000-1142</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">사업장명</td><td style="width:52mm">{SUPPLIER['name']}</td>
    <td class="lbl" style="width:26mm">사업자등록번호</td><td class="mono">{SUPPLIER['bno']}</td></tr>
<tr><td class="lbl">사업장관리번호</td><td class="mono">214-81-01117-0</td>
    <td class="lbl">가입자 수</td><td>12명 (국민연금 12 / 건강 12 / 고용 12 / 산재 12)</td></tr>
<tr><td class="lbl">소재지</td><td colspan="3" class="small">{SUPPLIER['addr']}</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:28mm">보험 종류</th><th style="width:30mm">보수월액 총액</th>
    <th style="width:20mm">요율</th><th style="width:30mm">근로자 부담</th>
    <th style="width:30mm">사업주 부담</th><th>합계(고지액)</th></tr>
{rows}
<tr><td class="lbl">합&nbsp;계</td><td>&nbsp;</td><td>&nbsp;</td>
    <td class="num b">{won(te)}</td><td class="num b">{won(tr_)}</td>
    <td class="num b" style="font-size:10pt">{won(tt)}</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm;height:14mm">납 부 할 금 액</td>
    <td class="c b" style="font-size:15pt">￦ {won(tt)}
      <div class="small">({kor_won(tt)})</div></td>
    <td class="lbl" style="width:26mm">납부기한</td><td class="c b" style="width:34mm">2026. 04. 10.</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">전용계좌</td>
    <td>국민연금 000000-00-000000 / 건강보험 000000-00-000000 (가상계좌)</td></tr>
<tr><td class="lbl">납부확인</td>
    <td class="b">2026-04-08 전액 납부 완료 (수납기관 : 대한은행 강남지점)</td></tr>
</table>
<div style="text-align:center;margin-top:4mm">{barcode('26030000114213750', 78)}</div>
<div class="note">· 납부기한 경과 시 연체금(1일 0.02%, 최대 9%)이 부과됩니다.<br>
· 본 고지서는 사업주 부담분에 대한 손금(비용) 증빙으로 사용할 수 있습니다.<br>
· 산재보험료는 전액 사업주 부담이며 업종별 요율이 적용됩니다.</div>
<div class="footer-org" style="font-size:12pt">국 민 건 강 보 험 공 단 &nbsp;(통합징수)</div>
"""
    docs.append(dict(no=27, slug="27_4대보험료고지서", size="A4",
                     title="4대 사회보험료 고지서",
                     html=html_doc("4대보험료고지서", body, extra_css=CSS)))
    return docs
