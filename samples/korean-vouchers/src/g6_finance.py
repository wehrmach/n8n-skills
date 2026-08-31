# -*- coding: utf-8 -*-
"""그룹 6. 금융 증빙 - 예금거래내역서/무통장입금증/약속어음/해외송금영수증"""
from common import SUPPLIER, BUYER, won, kor_won, stamp, html_doc, barcode

CSS = """
h1.title { border-bottom:2.4pt double #111; padding-bottom:2mm; }
.bank-hd { display:flex; justify-content:space-between; align-items:center;
           border-bottom:1.6pt solid #16457a; padding-bottom:1.5mm; }
.bank-hd .nm { font-size:13pt; font-weight:700; color:#16457a; letter-spacing:3px; }
.note-box { border:1.6pt solid #7a1616; padding:2mm; background:#fffaf7; }
.note-box h2 { text-align:center; font-size:14pt; letter-spacing:10px; margin:.5mm 0 2mm;
               color:#7a1616; }
table.grid td, table.grid th { font-size:8pt; }
.stub { border-left:1.2pt dashed #666; padding-left:3mm; }
"""


def build():
    docs = []

    # 32. 예금 거래내역서 (통장 거래내역)
    tx = [("2026-03-02", "이체", "㈜대한오피스", 0, 1_650_000, 48_350_000, "임차료 3월"),
          ("2026-03-05", "카드결제", "대한카드", 0, 1_270_000, 47_080_000, "법인카드 2월분"),
          ("2026-03-10", "입금", "㈜대한상사", 22_000_000, 0, 69_080_000, "매출대금"),
          ("2026-03-10", "이체", "국세청", 0, 4_318_000, 64_762_000, "부가세 예정"),
          ("2026-03-25", "급여이체", "급여 12건", 0, 51_240_000, 13_522_000, "3월 급여"),
          ("2026-03-25", "이체", "최프리", 0, 2_901_000, 10_621_000, "외주비(3.3% 공제)"),
          ("2026-03-27", "입금", "㈜세종물산", 18_700_000, 0, 29_321_000, "매출대금"),
          ("2026-03-31", "이자", "예금이자", 42_310, 0, 29_363_310, "세전"),
          ("2026-03-31", "출금", "이자소득세", 0, 6_510, 29_356_800, "15.4%")]
    rows = "".join(
        f'<tr><td class="c mono">{d}</td><td class="c">{k}</td><td>{w}</td>'
        f'<td class="num">{won(i) if i else "-"}</td>'
        f'<td class="num">{won(o) if o else "-"}</td>'
        f'<td class="num b">{won(b)}</td><td class="small">{m}</td></tr>'
        for d, k, w, i, o, b, m in tx)
    tin = sum(t[3] for t in tx)
    tout = sum(t[4] for t in tx)
    body = f"""
<div class="bank-hd"><span class="nm">대 한 은 행</span>
  <span class="small">DAEHAN BANK &nbsp;|&nbsp; 발급일 2026-04-01 &nbsp;|&nbsp;
  발급점 강남지점 (02-000-0000)</span></div>
<h1 class="title sm" style="margin-top:2mm">예 금 거 래 내 역 서</h1>
<div class="subtitle">조회기간 : 2026-03-01 ~ 2026-03-31</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:24mm">계좌번호</td><td class="mono b" style="width:44mm">123-456789-01-001</td>
    <td class="lbl" style="width:22mm">예금주</td><td>{SUPPLIER['name']}</td></tr>
<tr><td class="lbl">계좌종류</td><td>기업자유예금</td>
    <td class="lbl">사업자등록번호</td><td class="mono">{SUPPLIER['bno']}</td></tr>
<tr><td class="lbl">기초잔액</td><td class="num">50,000,000</td>
    <td class="lbl">기말잔액</td><td class="num b">29,356,800</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:22mm">거래일자</th><th style="width:18mm">구분</th>
    <th style="width:38mm">거래처(적요)</th><th style="width:26mm">입금(원)</th>
    <th style="width:26mm">출금(원)</th><th style="width:28mm">거래후 잔액</th><th>메모</th></tr>
{rows}
<tr><td class="lbl" colspan="3">합&nbsp;&nbsp;계</td><td class="num b">{won(tin)}</td>
    <td class="num b">{won(tout)}</td><td class="num b">29,356,800</td><td>&nbsp;</td></tr>
</table>
<div class="note">· 위 거래내역은 당행 전산자료와 상위 없음을 확인합니다.<br>
· 본 내역서는 회계감사·세무조사 시 금융거래 증빙자료로 사용할 수 있습니다.<br>
· 발급수수료 : 2,000원 (수납완료)</div>
<div class="footer-org" style="font-size:12pt">대 한 은 행 강 남 지 점 장 {stamp('지점장',44)}</div>
"""
    docs.append(dict(no=32, slug="32_예금거래내역서", size="A4", title="예금 거래내역서",
                     html=html_doc("예금거래내역서", body, extra_css=CSS)))

    # 33. 무통장입금증 (송금확인증)
    amt = 13_750_000
    body = f"""
<div class="bank-hd"><span class="nm">대 한 은 행</span>
  <span class="small">인터넷뱅킹 이체확인증</span></div>
<h1 class="title sm" style="margin-top:2mm">무 통 장 입 금 증 (이 체 확 인 증)</h1>
<div class="subtitle">거래번호 : 2026042509331100781</div>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:28mm">거래일시</td><td class="mono b" colspan="3">2026-04-25 09:33:11</td></tr>
<tr><td class="lbl">보내는 분</td><td style="width:54mm">{BUYER['name']}</td>
    <td class="lbl" style="width:24mm">출금계좌</td><td class="mono">999-0000-1234-56</td></tr>
<tr><td class="lbl">받는 분</td><td class="b">{SUPPLIER['name']}</td>
    <td class="lbl">입금계좌</td><td class="mono b">대한은행 123-456789-01-001</td></tr>
<tr><td class="lbl">받는분 표시</td><td>미래유통 3월분</td>
    <td class="lbl">내 통장 표시</td><td>한빛테크 용역비</td></tr>
</table>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:28mm;height:18mm">이 체 금 액</td>
    <td class="c" style="font-size:17pt;font-weight:700">￦ {won(amt)}
      <div class="small" style="font-weight:400">({kor_won(amt)})</div></td></tr>
<tr><td class="lbl">수 수 료</td><td class="num">면제 (기업 인터넷뱅킹)</td></tr>
<tr><td class="lbl">처리결과</td><td class="b" style="color:#1a6b3f">정상 처리 (입금 완료)</td></tr>
</table>
<div style="text-align:center;margin-top:4mm">{barcode('2026042509331100781', 84)}</div>
<div class="note">· 본 확인증은 자금 이체 사실을 증명하는 서류이며, 거래 증빙(입금 증빙)으로 사용됩니다.<br>
· 이체 결과에 대한 문의는 대한은행 고객센터(1500-0000)로 연락하시기 바랍니다.</div>
<div class="sign-area">위와 같이 이체되었음을 확인합니다. &nbsp;&nbsp; 2026년 04월 25일</div>
<div class="footer-org" style="font-size:12pt">대 한 은 행 {stamp('대한은행',44)}</div>
"""
    docs.append(dict(no=33, slug="33_무통장입금증_이체확인증", size="A5",
                     title="무통장입금증(이체확인증)",
                     html=html_doc("무통장입금증", body, size="A5", extra_css=CSS)))

    # 34. 약속어음
    face = 30_000_000
    body = f"""
<div class="note-box">
  <div style="display:flex;justify-content:space-between" class="small">
    <span>어음번호 : 자가 12345678</span><span>인지세 납부 (전자수입인지 첨부)</span></div>
  <h2>약 속 어 음</h2>
  <table class="grid" style="background:#fff">
  <tr><td class="lbl" style="width:26mm">수 취 인</td>
      <td class="b" colspan="3">{SUPPLIER['name']} 귀하</td></tr>
  <tr><td class="lbl" style="height:15mm">금&nbsp;&nbsp;&nbsp;&nbsp;액</td>
      <td class="c" colspan="3" style="font-size:16pt;font-weight:700">
        ￦ {won(face)}<div class="small" style="font-weight:400">(금 삼천만원정)</div></td></tr>
  <tr><td class="lbl">지 급 기 일</td><td class="c b" style="width:40mm">2026년 09월 30일</td>
      <td class="lbl" style="width:26mm">발 행 일</td><td class="c" style="width:40mm">2026년 03월 31일</td></tr>
  <tr><td class="lbl">지 급 지</td><td>서울특별시 성남시 분당구</td>
      <td class="lbl">발 행 지</td><td>경기도 성남시 분당구</td></tr>
  <tr><td class="lbl">지급장소</td><td colspan="3">대한은행 판교지점</td></tr>
  </table>
  <p class="small" style="margin-top:2mm">
  위의 금액을 귀하 또는 귀하의 지시인에게 이 약속어음과 상환하여 지급하겠습니다.</p>
  <table class="grid" style="background:#fff;margin-top:2mm">
  <tr><td class="lbl" style="width:26mm">발 행 인</td>
      <td class="small">상호 : {BUYER['name']}<br>
      주소 : {BUYER['addr']}<br>
      사업자등록번호 : {BUYER['bno']}<br>
      대표이사 : {BUYER['ceo']} (인) {stamp('미래유통',40)}</td></tr>
  </table>
</div>
<table class="grid" style="margin-top:2mm">
<tr><th colspan="4">배 서 란 (뒷면)</th></tr>
<tr><td class="lbl" style="width:22mm">배서일자</td><td style="width:30mm">&nbsp;</td>
    <td class="lbl" style="width:22mm">피배서인</td><td>&nbsp;</td></tr>
<tr><td class="lbl" style="height:11mm">배 서 인</td><td colspan="3" class="small">
    주소 : &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 상호 :
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 대표자 : &nbsp; (인)</td></tr>
</table>
<div class="note xsmall">· 「어음법」상 유가증권으로 지급기일에 지급장소에 제시하여야 합니다.
 회계처리는 수취 시 받을어음(자산), 발행 시 지급어음(부채)으로 계상합니다.
 종이 약속어음은 단계적으로 폐지되어 전자어음으로 전환되고 있습니다.</div>
"""
    docs.append(dict(no=34, slug="34_약속어음", size="A5L", title="약속어음",
                     html=html_doc("약속어음", body, size="A5L",
                                   extra_css=CSS + "\nbody { zoom:.93; }\n")))

    # 35. 해외송금 영수증 (외화)
    usd, rate = 12_500.00, 1_342.50
    krw = int(usd * rate)
    fee = 25_000
    body = f"""
<div class="bank-hd"><span class="nm">대 한 은 행</span>
  <span class="small">FOREIGN REMITTANCE ADVICE / 외화송금 영수증</span></div>
<h1 class="title sm" style="margin-top:2mm">해 외 송 금 영 수 증</h1>
<div class="subtitle">Reference No. : DHB-2026-FT-0031882 &nbsp;|&nbsp; 거래일 2026-03-18</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:28mm">송금인 (Remitter)</td>
    <td style="width:56mm">{SUPPLIER['name']}<div class="xsmall">{SUPPLIER['addr']}</div></td>
    <td class="lbl" style="width:24mm">사업자번호</td><td class="mono">{SUPPLIER['bno']}</td></tr>
<tr><td class="lbl">수취인 (Beneficiary)</td>
    <td>GLOBAL SOFT SOLUTIONS PTE. LTD.<div class="xsmall">10 ANSON ROAD, SINGAPORE 079903</div></td>
    <td class="lbl">수취인 계좌</td><td class="mono">SG00-XXXX-0000-1234</td></tr>
<tr><td class="lbl">수취은행</td><td>OVERSEA BANK LTD., SINGAPORE</td>
    <td class="lbl">SWIFT CODE</td><td class="mono">OVBKSGSGXXX</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:34%">구분</th><th>내용</th></tr>
<tr><td class="lbl l">송금 통화 / 금액</td><td class="b">USD 12,500.00</td></tr>
<tr><td class="lbl l">적용 환율 (전신환 매도율)</td><td class="mono">1 USD = KRW {rate:,.2f}</td></tr>
<tr><td class="lbl l">원화 환산액</td><td class="num b">￦ {won(krw)}</td></tr>
<tr><td class="lbl l">송금수수료</td><td class="num">￦ {won(fee)}</td></tr>
<tr><td class="lbl l">전신료(Cable Charge)</td><td class="num">￦ 8,000</td></tr>
<tr><td class="lbl l">해외 중계·수취 수수료 부담</td><td>OUR (송금인 부담) / USD 25.00</td></tr>
<tr><td class="lbl l b">총 출금액</td><td class="num b" style="font-size:11pt">￦ {won(krw + fee + 8000)}</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:28mm">송금 사유</td><td>해외 소프트웨어 라이선스 사용료 (Invoice No. GS-2026-0442)</td></tr>
<tr><td class="lbl">외국환거래 신고</td><td>「외국환거래규정」 제4-3조 경상거래 - 신고 예외 (증빙서류 제출)</td></tr>
<tr><td class="lbl">제출 증빙</td><td class="small">Commercial Invoice 1부, 계약서 사본 1부</td></tr>
<tr><td class="lbl">출금계좌</td><td class="mono">대한은행 123-456789-01-001 ({SUPPLIER['name']})</td></tr>
</table>
<div class="note">· 본 영수증은 외국환거래 및 비용 지출 증빙으로 사용됩니다.<br>
· 해외 지급 사용료는 원천징수(제한세율) 대상 여부를 조세조약에 따라 검토하여야 합니다.<br>
· This advice is issued for the customer's reference and is not a negotiable instrument.</div>
<div class="footer-org" style="font-size:12pt">대 한 은 행 외 환 센 터 {stamp('외환센터',44)}</div>
"""
    docs.append(dict(no=35, slug="35_해외송금영수증", size="A4", title="해외송금 영수증",
                     html=html_doc("해외송금영수증", body, extra_css=CSS)))
    return docs
