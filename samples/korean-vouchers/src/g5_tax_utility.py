# -*- coding: utf-8 -*-
"""그룹 5. 세금·공과금 증빙 - 국세/지방세 납부영수증, 공과금 청구서, 기부금영수증"""
from common import SUPPLIER, won, kor_won, stamp, html_doc, barcode, biz_no

CSS = """
h1.title { border-top:2pt solid #111; border-bottom:2pt solid #111; padding:2mm 0; }
.form-no { font-size:7pt; color:#444; border:.7pt solid #666; padding:.6mm 1.6mm;
           display:inline-block; }
.amt-box { border:1.4pt solid #111; padding:3mm; text-align:center; margin-top:2mm; }
.amt-box .v { font-size:18pt; font-weight:700; letter-spacing:1px; }
.giro { border:1.2pt solid #1a6b3f; padding:2mm; margin-top:3mm; background:#f4faf6; }
.giro .t { font-weight:700; color:#1a6b3f; letter-spacing:3px; text-align:center; }
.stub { border-top:1.2pt dashed #666; margin-top:3mm; padding-top:2mm; }
table.grid td, table.grid th { font-size:8pt; }
"""


def build():
    docs = []

    # 28. 국세 납부영수증 (부가가치세 확정신고 납부분)
    tax = 4_318_000
    body = f"""
<div style="display:flex;justify-content:space-between">
  <span class="form-no">국세징수법 시행규칙 [별지 제20호서식] 준용</span>
  <span class="form-no">납세자 보관용</span></div>
<h1 class="title sm" style="margin-top:1mm">국 세 납 부 영 수 증 서</h1>
<div class="subtitle">(전자납부 확인서) &nbsp;|&nbsp; 국세청 홈택스 발급</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">전자납부번호</td>
    <td class="mono b" style="width:56mm">0126-1-14-26-0-4318000</td>
    <td class="lbl" style="width:24mm">발급일자</td><td class="mono">2026-04-27</td></tr>
<tr><td class="lbl">납세자 상호</td><td>{SUPPLIER['name']}</td>
    <td class="lbl">사업자등록번호</td><td class="mono">{SUPPLIER['bno']}</td></tr>
<tr><td class="lbl">대표자</td><td>{SUPPLIER['ceo']}</td>
    <td class="lbl">관할 세무서</td><td>○○세무서</td></tr>
<tr><td class="lbl">주소</td><td colspan="3" class="small">{SUPPLIER['addr']}</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:30mm">세목</th><th style="width:26mm">귀속연도</th>
    <th style="width:30mm">신고구분</th><th style="width:26mm">납부기한</th><th>납부세액(원)</th></tr>
<tr><td class="c b">부가가치세</td><td class="c">2026년 제1기 예정</td>
    <td class="c">확정신고 자진납부</td><td class="c mono">2026-04-27</td>
    <td class="num b">{won(tax)}</td></tr>
<tr><td class="c">가산세</td><td class="c">-</td><td class="c">-</td><td class="c">-</td>
    <td class="num">0</td></tr>
<tr><td class="lbl" colspan="4">합&nbsp;&nbsp;계</td><td class="num b" style="font-size:10pt">{won(tax)}</td></tr>
</table>
<div class="amt-box">
  <div class="small">납 부 금 액</div>
  <div class="v">￦ {won(tax)}</div>
  <div class="small">({kor_won(tax)})</div>
</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">납부일시</td><td class="mono" style="width:44mm">2026-04-27 15:32:11</td>
    <td class="lbl" style="width:22mm">납부방법</td><td>계좌이체(인터넷뱅킹)</td></tr>
<tr><td class="lbl">수납기관</td><td>대한은행 강남지점</td>
    <td class="lbl">거래고유번호</td><td class="mono">2026042715321100412</td></tr>
<tr><td class="lbl">계산내역</td><td colspan="3" class="small">
    매출세액 8,912,000 － 매입세액 4,594,000 ＝ 납부세액 {won(tax)}</td></tr>
</table>
<div style="text-align:center;margin-top:3mm">{barcode('012611426043180000', 88)}</div>
<div class="note">· 위 금액이 정히 수납되었음을 확인합니다.<br>
· 본 영수증은 국세 납부사실을 증명하는 서류로, 회계상 세금과공과 계상 증빙으로 사용됩니다.<br>
· 납부내역은 국세청 홈택스(hometax.go.kr) &gt; 납부·고지·환급 에서 조회할 수 있습니다.</div>
<div class="footer-org" style="font-size:12pt">○ ○ 세 무 서 장 {stamp('세무서장',44)}</div>
"""
    docs.append(dict(no=28, slug="28_국세납부영수증_부가가치세", size="A4",
                     title="국세 납부영수증(부가가치세)",
                     html=html_doc("국세납부영수증", body, extra_css=CSS)))

    # 29. 지방세 납부영수증 (재산세)
    ltax, edu, reg = 1_240_000, 248_000, 156_000
    lt = ltax + edu + reg
    body = f"""
<div style="display:flex;justify-content:space-between">
  <span class="form-no">지방세법 시행규칙 [별지 제○호서식] 준용</span>
  <span class="form-no">납세자 보관용</span></div>
<h1 class="title sm" style="margin-top:1mm">지 방 세 납 부 확 인 서</h1>
<div class="subtitle">(재산세 - 건축물) &nbsp;|&nbsp; 위택스(wetax.go.kr) 발급</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">전자납부번호</td>
    <td class="mono b" style="width:58mm">11680-1-26-09-0000142</td>
    <td class="lbl" style="width:22mm">과세연도</td><td class="mono">2026년도</td></tr>
<tr><td class="lbl">납세자</td><td>{SUPPLIER['name']} ({SUPPLIER['bno']})</td>
    <td class="lbl">과세기준일</td><td class="mono">2026-06-01</td></tr>
<tr><td class="lbl">과세물건</td><td colspan="3" class="small">
    서울특별시 강남구 테헤란로 123 한빛빌딩 8층 (사무실 · 연면적 412.5㎡)</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th>세목</th><th style="width:34mm">과세표준(원)</th><th style="width:20mm">세율</th>
    <th style="width:32mm">세액(원)</th></tr>
<tr><td class="c">재산세 (건축물)</td><td class="num">496,000,000</td><td class="c">0.25%</td>
    <td class="num">{won(ltax)}</td></tr>
<tr><td class="c">지방교육세</td><td class="num">{won(ltax)}</td><td class="c">20%</td>
    <td class="num">{won(edu)}</td></tr>
<tr><td class="c">지역자원시설세</td><td class="num">496,000,000</td><td class="c">0.0315%</td>
    <td class="num">{won(reg)}</td></tr>
<tr><td class="lbl" colspan="3">합&nbsp;&nbsp;계</td><td class="num b">{won(lt)}</td></tr>
</table>
<div class="amt-box">
  <div class="small">납 부 금 액</div>
  <div class="v">￦ {won(lt)}</div>
  <div class="small">({kor_won(lt)})</div>
</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">납부기한</td><td class="mono" style="width:34mm">2026-07-31</td>
    <td class="lbl" style="width:24mm">납부일자</td><td class="mono">2026-07-28</td></tr>
<tr><td class="lbl">수납기관</td><td>대한은행 (CD/ATM 및 인터넷지로)</td>
    <td class="lbl">과세관청</td><td>서울특별시 강남구청장</td></tr>
</table>
<div class="giro">
  <div class="t">전 자 납 부 (지 로) 확 인</div>
  <table class="grid tight" style="margin-top:1.5mm;background:#fff">
  <tr><td class="lbl" style="width:26mm">지로번호</td><td class="mono">1234567</td>
      <td class="lbl" style="width:26mm">가상계좌</td><td class="mono">700-0000-000000</td></tr>
  </table>
  <div style="text-align:center;margin-top:2mm">{barcode('11680126090000142', 80)}</div>
</div>
<div class="note">· 위 지방세가 정상 수납되었음을 확인합니다.<br>
· 납부기한 경과 시 가산금 3%(및 매월 0.66% 중가산금)가 부과됩니다.</div>
<div class="footer-org" style="font-size:12pt">강 남 구 청 장 {stamp('구청장',44)}</div>
"""
    docs.append(dict(no=29, slug="29_지방세납부확인서_재산세", size="A4",
                     title="지방세 납부확인서(재산세)",
                     html=html_doc("지방세납부확인서", body, extra_css=CSS)))

    # 30. 공과금(전기요금) 청구서 겸 영수증
    base, use_, vat, fund = 6_580, 428_420, 43_500, 15_600
    tot = base + use_ + vat + fund
    body = f"""
<h1 class="title sm">전 기 요 금 청 구 서 (영 수 증)</h1>
<div class="subtitle">2026년 3월분 &nbsp;|&nbsp; 발행일 2026-04-05 &nbsp;|&nbsp;
  세금계산서 겸용 (부가가치세법 제32조)</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:24mm">고객번호</td><td class="mono b" style="width:34mm">0142-8891-33</td>
    <td class="lbl" style="width:24mm">고객명</td><td>{SUPPLIER['name']}</td>
    <td class="lbl" style="width:24mm">사업자번호</td><td class="mono">{SUPPLIER['bno']}</td></tr>
<tr><td class="lbl">사용장소</td><td colspan="3" class="small">서울 강남구 테헤란로 123 한빛빌딩 8층</td>
    <td class="lbl">계약종별</td><td>일반용(갑) 저압</td></tr>
<tr><td class="lbl">계약전력</td><td>45 kW</td>
    <td class="lbl">검침일</td><td class="mono">2026-03-31</td>
    <td class="lbl">납기일</td><td class="mono b">2026-04-25</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:26mm">당월 지침</th><th style="width:26mm">전월 지침</th>
    <th style="width:26mm">사용량(kWh)</th><th style="width:26mm">전월 사용량</th>
    <th style="width:26mm">전년 동월</th><th>역률</th></tr>
<tr><td class="c mono">28,417</td><td class="c mono">24,905</td><td class="c b">3,512</td>
    <td class="c">3,308</td><td class="c">3,690</td><td class="c">96%</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th colspan="2">요 금 내 역</th></tr>
<tr><td class="lbl l" style="width:50%">기본요금 (45kW × 146.2원)</td><td class="num">{won(base)}</td></tr>
<tr><td class="lbl l">전력량요금 (3,512kWh)</td><td class="num">{won(use_)}</td></tr>
<tr><td class="lbl l">부가가치세 (10%)</td><td class="num">{won(vat)}</td></tr>
<tr><td class="lbl l">전력산업기반기금 (3.7%)</td><td class="num">{won(fund)}</td></tr>
<tr><td class="lbl l b">청 구 금 액 (원 단위 절사)</td><td class="num b" style="font-size:11pt">{won(tot)}</td></tr>
</table>
<div class="amt-box">
  <div class="small">이 달의 전기요금</div>
  <div class="v">￦ {won(tot)}</div>
  <div class="small">납기일 2026. 04. 25. &nbsp;|&nbsp; 자동이체 출금예정</div>
</div>
<div class="giro">
  <div class="t">지 로 (G I R O) 납 부 란</div>
  <table class="grid tight" style="margin-top:1.5mm;background:#fff">
  <tr><td class="lbl" style="width:24mm">지로번호</td><td class="mono">6100015</td>
      <td class="lbl" style="width:24mm">전자납부번호</td><td class="mono">1234-5678-9012-3456</td></tr>
  </table>
  <div style="text-align:center;margin-top:2mm">{barcode('61000150142889133', 82)}</div>
</div>
<div class="stub">
  <div class="small b">[ 영수증 (고객 보관용) ]</div>
  <table class="grid tight" style="margin-top:1mm">
  <tr><td class="lbl" style="width:24mm">수납일자</td><td class="mono" style="width:30mm">2026-04-25</td>
      <td class="lbl" style="width:24mm">수납금액</td><td class="num b" style="width:30mm">{won(tot)}</td>
      <td class="lbl" style="width:24mm">수납방법</td><td>자동이체(대한은행)</td></tr>
  </table>
</div>
<div class="note">· 본 청구서는 부가가치세법상 세금계산서를 갈음하는 서류로 매입세액 공제가 가능합니다.
  (공급가액 {won(base + use_)}원, 세액 {won(vat)}원)<br>
· 전력산업기반기금은 부가가치세 과세대상이 아닙니다.</div>
<div class="footer-org" style="font-size:12pt">한 빛 에 너 지 (주)</div>
"""
    docs.append(dict(no=30, slug="30_공과금_전기요금청구서", size="A4",
                     title="공과금 청구서(전기요금)",
                     html=html_doc("전기요금청구서", body, extra_css=CSS)))

    # 31. 기부금영수증
    body = f"""
<div style="display:flex;justify-content:space-between">
  <span class="form-no">소득세법 시행규칙 [별지 제45호의2서식] 준용</span>
  <span class="form-no">(앞쪽)</span></div>
<h1 class="title sm" style="margin-top:1mm">기 부 금 영 수 증</h1>
<div class="subtitle">일련번호 : 2026-0000-0451</div>
<div style="border:.7pt solid #222;padding:1mm 2mm;background:#e9edf5;font-weight:700;
     margin-top:2mm;font-size:8.5pt">① 기부자</div>
<table class="grid">
<tr><td class="lbl" style="width:26mm">성명(법인명)</td><td style="width:56mm">{SUPPLIER['name']}</td>
    <td class="lbl" style="width:30mm">주민(사업자)등록번호</td><td class="mono">{SUPPLIER['bno']}</td></tr>
<tr><td class="lbl">주소(소재지)</td><td colspan="3" class="small">{SUPPLIER['addr']}</td></tr>
</table>
<div style="border:.7pt solid #222;padding:1mm 2mm;background:#e9edf5;font-weight:700;
     margin-top:2mm;font-size:8.5pt">② 기부금 단체</div>
<table class="grid">
<tr><td class="lbl" style="width:26mm">단체명</td><td style="width:56mm">사단법인 한빛나눔재단</td>
    <td class="lbl" style="width:30mm">고유번호(사업자번호)</td><td class="mono">{biz_no('102820333')}</td></tr>
<tr><td class="lbl">소재지</td><td class="small">서울특별시 종로구 사직로 20</td>
    <td class="lbl">기부금 공제 구분</td><td class="b">법정기부금 (지정기부금 아님)</td></tr>
</table>
<div style="border:.7pt solid #222;padding:1mm 2mm;background:#e9edf5;font-weight:700;
     margin-top:2mm;font-size:8.5pt">③ 기부금 모집처(언론기관 등)</div>
<table class="grid">
<tr><td class="lbl" style="width:26mm">단체명</td><td>해당 없음</td>
    <td class="lbl" style="width:26mm">사업자등록번호</td><td>-</td></tr>
</table>
<div style="border:.7pt solid #222;padding:1mm 2mm;background:#e9edf5;font-weight:700;
     margin-top:2mm;font-size:8.5pt">④ 기부 내용</div>
<table class="grid">
<tr><th style="width:20mm">유형</th><th style="width:20mm">코드</th>
    <th style="width:24mm">연월일</th><th>내용</th>
    <th style="width:26mm">금액(원)</th></tr>
<tr><td class="c">금전</td><td class="c mono">10</td><td class="c mono">2026-03-18</td>
    <td>아동 교육환경 개선 사업 후원금</td><td class="num b">5,000,000</td></tr>
<tr><td class="c">현물</td><td class="c mono">20</td><td class="c mono">2026-03-25</td>
    <td>노트북 10대 기증 (장부가액)</td><td class="num">3,000,000</td></tr>
<tr><td class="lbl" colspan="4">합&nbsp;&nbsp;계</td><td class="num b" style="font-size:10pt">8,000,000</td></tr>
</table>
<div class="amt-box">
  <div class="small">기 부 금 액 합 계</div>
  <div class="v">￦ 8,000,000</div>
  <div class="small">({kor_won(8000000)})</div>
</div>
<div class="note">「소득세법」 제34조 및 「법인세법」 제24조에 따라 위와 같이 기부금을 기부하였음을 증명합니다.
<br>※ 본 영수증은 손금산입(법인) 또는 세액공제(개인) 증빙자료로 사용됩니다.
<br>※ 현물기부의 경우 장부가액(시가가 장부가액보다 낮은 경우 시가)으로 평가하였습니다.</div>
<div class="sign-area">2026년 03월 31일</div>
<div class="footer-org" style="font-size:12pt">
  사단법인 한빛나눔재단 &nbsp; 이사장 나 눔 {stamp('나눔재단',44)}</div>
"""
    docs.append(dict(no=31, slug="31_기부금영수증", size="A4", title="기부금영수증",
                     html=html_doc("기부금영수증", body, extra_css=CSS)))
    return docs
