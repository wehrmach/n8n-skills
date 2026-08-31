# -*- coding: utf-8 -*-
"""그룹 7. 여비교통·소액 실물 영수증 - 간이영수증/택시/통행료/주차/식당/숙박/항공/철도"""
from common import (SUPPLIER, BUYER, won, kor_won, stamp, html_doc, barcode, biz_no)

CSS = """
h1.title { border:1.4pt solid #111; padding:2mm 0; }
table.grid td, table.grid th { font-size:8pt; }
.ticket { border:1.4pt solid #16457a; border-radius:2mm; padding:3mm; }
.ticket .hd { display:flex; justify-content:space-between; align-items:center;
              border-bottom:1pt solid #16457a; padding-bottom:1.5mm; margin-bottom:2mm; }
.ticket .brand { font-weight:700; color:#16457a; font-size:12pt; letter-spacing:2px; }
.leg { display:flex; align-items:center; justify-content:space-between; margin:2mm 0; }
.leg .ap { text-align:center; }
.leg .ap b { font-size:17pt; display:block; letter-spacing:1px; }
.leg .arrow { flex:1; text-align:center; color:#16457a; font-size:9pt;
              border-top:1pt dashed #16457a; margin:0 4mm; }
"""


def slip(inner):
    return f'<div class="slip">{inner}</div>'


def build():
    docs = []

    # 36. 간이영수증 (일반 영수증)
    amt = 28_000
    body = f"""
<h1 class="title sm">영 &nbsp; 수 &nbsp; 증</h1>
<div class="subtitle">(공급받는자용) &nbsp;|&nbsp; No. 0142</div>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:26mm;height:14mm">공급받는자</td>
    <td class="b">{SUPPLIER['name']} 귀하</td></tr>
<tr><td class="lbl" style="height:20mm">금&nbsp;&nbsp;&nbsp;&nbsp;액</td>
    <td class="c" style="font-size:16pt;font-weight:700">
      ￦ {won(amt)}<div class="small" style="font-weight:400">({kor_won(amt)})</div></td></tr>
</table>
<div class="note" style="text-align:center;font-size:9pt">위 금액을 정히 영수함.</div>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:24mm">품목</th><th style="width:18mm">수량</th>
    <th style="width:26mm">단가</th><th>금액</th></tr>
<tr><td class="c">퀵서비스 운송료</td><td class="c">1</td><td class="num">18,000</td>
    <td class="num">18,000</td></tr>
<tr><td class="c">포장자재</td><td class="c">2</td><td class="num">5,000</td>
    <td class="num">10,000</td></tr>
<tr><td class="lbl" colspan="3">합&nbsp;계</td><td class="num b">{won(amt)}</td></tr>
</table>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:26mm">사업자등록번호</td><td class="mono">{biz_no('118220456')}</td></tr>
<tr><td class="lbl">상&nbsp;&nbsp;&nbsp;&nbsp;호</td>
    <td>번개퀵서비스 &nbsp;&nbsp; 대표 김번개 {stamp('김번개',32)}</td></tr>
<tr><td class="lbl">사업장 소재지</td><td class="small">서울특별시 강남구 논현로 88</td></tr>
<tr><td class="lbl">업태 / 종목</td><td>운수업 / 화물운송</td></tr>
<tr><td class="lbl">전화번호</td><td>02-511-0000</td></tr>
<tr><td class="lbl">작성일자</td><td class="mono">2026년 03월 17일</td></tr>
</table>
<div class="note">· 건당 3만원 이하 거래는 간이영수증으로 지출증빙이 가능합니다.
  (법인세법 시행령 제158조 제2항)<br>
· 3만원 초과 거래를 간이영수증으로 처리하면 증빙불비가산세 2%가 부과됩니다.</div>
"""
    docs.append(dict(no=36, slug="36_간이영수증", size="A5", title="간이영수증",
                     html=html_doc("간이영수증", body, size="A5", extra_css=CSS)))

    # 37. 택시 영수증
    body = slip(f"""
  <div class="ttl">택 시 영 수 증</div>
  <hr>
  <div class="row"><span>운수회사</span><span>대한교통(주)</span></div>
  <div class="row"><span>사업자번호</span><span>{biz_no('220810777')}</span></div>
  <div class="row"><span>차량번호</span><span>서울 12가 3456</span></div>
  <div class="row"><span>운전자</span><span>김기사</span></div>
  <div class="row"><span>연락처</span><span>02-888-0000</span></div>
  <hr>
  <div class="row"><span>승차일시</span><span>2026/03/09 08:12</span></div>
  <div class="row"><span>하차일시</span><span>2026/03/09 08:41</span></div>
  <div class="row"><span>승차지</span><span>강남역 11번 출구</span></div>
  <div class="row"><span>하차지</span><span>서울역 KTX 승강장</span></div>
  <div class="row"><span>주행거리</span><span>11.4 km</span></div>
  <hr>
  <div class="row"><span>기 본 요 금</span><span>4,800</span></div>
  <div class="row"><span>거리·시간 요금</span><span>7,300</span></div>
  <div class="row"><span>심야·시외 할증</span><span>0</span></div>
  <div class="row b" style="font-size:10pt"><span>합 계</span><span>12,100</span></div>
  <hr>
  <div class="row"><span>결제수단</span><span>법인카드</span></div>
  <div class="row"><span>카드번호</span><span>5327-88**-****-1234</span></div>
  <div class="row"><span>승인번호</span><span>21883047</span></div>
  <hr>
  <div class="xsmall">· 여객운송용역은 부가가치세 면세이며 매입세액 공제 대상이 아닙니다.</div>
  <div class="xsmall">· 여비교통비 지출 증빙으로 사용하십시오.</div>
  <div class="xsmall">· 분실물 문의 : 02-888-0000</div>
  <hr>
  <div style="text-align:center">{barcode('TAXI-21883047', 60)}</div>
""")
    docs.append(dict(no=37, slug="37_택시영수증", size="SLIP", title="택시 영수증",
                     html=html_doc("택시영수증", body, size="SLIP",
                                   watermark="샘플", note="")))

    # 38. 고속도로 통행료 영수증
    body = slip(f"""
  <div class="ttl">고속도로 통행료 영수증</div>
  <div style="text-align:center" class="xsmall">한국도로공사 (가상 샘플)</div>
  <hr>
  <div class="row"><span>영수증번호</span><span>2026-0309-118842</span></div>
  <div class="row"><span>차량번호</span><span>12가 3456</span></div>
  <div class="row"><span>차종</span><span>1종 (승용차)</span></div>
  <hr>
  <div class="row"><span>진입영업소</span><span>서울(경부)</span></div>
  <div class="row"><span>진입일시</span><span>2026/03/09 09:05</span></div>
  <div class="row"><span>진출영업소</span><span>부산</span></div>
  <div class="row"><span>진출일시</span><span>2026/03/09 13:22</span></div>
  <div class="row"><span>주행거리</span><span>398.5 km</span></div>
  <hr>
  <div class="row"><span>통 행 료</span><span>21,100</span></div>
  <div class="row"><span>할 인</span><span>0</span></div>
  <div class="row b" style="font-size:10pt"><span>납부금액</span><span>21,100</span></div>
  <hr>
  <div class="row"><span>결제구분</span><span>하이패스 (후불)</span></div>
  <div class="row"><span>카드번호</span><span>9410-**-****-0022</span></div>
  <div class="row"><span>공급가액</span><span>19,182</span></div>
  <div class="row"><span>부가세</span><span>1,918</span></div>
  <hr>
  <div class="xsmall">· 도로 통행료는 과세 대상이며 사업 관련 사용분은
    매입세액 공제가 가능합니다.</div>
  <div class="xsmall">· 통행료 문의 : 1588-0000</div>
  <hr>
  <div style="text-align:center">{barcode('TOLL-20260309118842', 60)}</div>
""")
    docs.append(dict(no=38, slug="38_고속도로통행료영수증", size="SLIP",
                     title="고속도로 통행료 영수증",
                     html=html_doc("통행료영수증", body, size="SLIP",
                                   watermark="샘플", note="")))

    # 39. 주차장 영수증
    body = slip(f"""
  <div class="ttl">주 차 요 금 영 수 증</div>
  <hr>
  <div class="row"><span>주차장명</span><span>한빛빌딩 지하주차장</span></div>
  <div class="row"><span>사업자번호</span><span>{biz_no('214812999')}</span></div>
  <div class="row"><span>대표자</span><span>주차관리</span></div>
  <div class="row"><span>주소</span><span>서울 강남구 테헤란로 123</span></div>
  <hr>
  <div class="row"><span>차량번호</span><span>12가 3456</span></div>
  <div class="row"><span>입차시각</span><span>2026/03/11 11:40</span></div>
  <div class="row"><span>출차시각</span><span>2026/03/11 14:25</span></div>
  <div class="row"><span>주차시간</span><span>2시간 45분</span></div>
  <hr>
  <div class="row"><span>기본 30분</span><span>2,000</span></div>
  <div class="row"><span>추가 135분(10분당 500원)</span><span>6,500</span></div>
  <div class="row"><span>할인(방문등록 1시간)</span><span>-3,000</span></div>
  <hr>
  <div class="row"><span>공 급 가 액</span><span>5,000</span></div>
  <div class="row"><span>부 가 세</span><span>500</span></div>
  <div class="row b" style="font-size:10pt"><span>결제금액</span><span>5,500</span></div>
  <hr>
  <div class="row"><span>결제수단</span><span>현금영수증(지출증빙)</span></div>
  <div class="row"><span>식별번호</span><span>{SUPPLIER['bno']}</span></div>
  <div class="row"><span>승인번호</span><span>771204558</span></div>
  <hr>
  <div class="xsmall">· 감사합니다. 안전운행 하십시오.</div>
""")
    docs.append(dict(no=39, slug="39_주차요금영수증", size="SLIP", title="주차요금 영수증",
                     html=html_doc("주차요금영수증", body, size="SLIP",
                                   watermark="샘플", note="")))

    # 40. 음식점 POS 영수증
    body = slip(f"""
  <div class="ttl">고 향 식 당</div>
  <div style="text-align:center" class="xsmall">맛있는 한 끼, 감사합니다</div>
  <hr>
  <div class="row"><span>사업자번호</span><span>{biz_no('120150888')}</span></div>
  <div class="row"><span>대표자</span><span>정고향</span></div>
  <div class="row"><span>주소</span><span>서울 강남구 역삼로 15</span></div>
  <div class="row"><span>전화</span><span>02-566-1122</span></div>
  <hr>
  <div class="row"><span>영수증번호</span><span>2026-0311-0087</span></div>
  <div class="row"><span>거래일시</span><span>2026/03/11 12:48:22</span></div>
  <div class="row"><span>POS / 테이블</span><span>POS-01 / T7</span></div>
  <div class="row"><span>인원</span><span>4명</span></div>
  <hr>
  <div class="row"><span>한정식 A코스 &nbsp;x4</span><span>140,000</span></div>
  <div class="row"><span>불고기전골 &nbsp;x1</span><span>32,000</span></div>
  <div class="row"><span>공기밥 &nbsp;x4</span><span>4,000</span></div>
  <div class="row"><span>음료(주류 제외) &nbsp;x4</span><span>8,000</span></div>
  <hr>
  <div class="row"><span>공 급 가 액</span><span>140,000</span></div>
  <div class="row"><span>부 가 세</span><span>14,000</span></div>
  <div class="row b" style="font-size:11pt"><span>합 계</span><span>154,000</span></div>
  <hr>
  <div class="row"><span>결제수단</span><span>신용카드(법인)</span></div>
  <div class="row"><span>카드번호</span><span>5327-88**-****-1234</span></div>
  <div class="row"><span>승인번호</span><span>44120987</span></div>
  <div class="row"><span>할부</span><span>일시불</span></div>
  <hr>
  <div class="xsmall">· 접대 목적 지출 시 참석자·상호를 별도 기록하여야 합니다.</div>
  <div class="xsmall">· 접대비는 매입세액 불공제 대상입니다.</div>
  <div class="xsmall">· 교환·환불은 영수증 지참 시 7일 이내 가능</div>
  <hr>
  <div style="text-align:center">{barcode('POS-2026031100087', 60)}</div>
""")
    docs.append(dict(no=40, slug="40_음식점POS영수증", size="SLIP",
                     title="음식점 POS 영수증",
                     html=html_doc("음식점영수증", body, size="SLIP",
                                   watermark="샘플", note="")))

    # 41. 숙박 영수증
    body = f"""
<h1 class="title sm">숙 박 영 수 증</h1>
<div class="subtitle">대한호텔 부산 &nbsp;|&nbsp; DAEHAN HOTEL BUSAN</div>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:26mm">영수증번호</td><td class="mono" style="width:38mm">BS-2026-0309-1142</td>
    <td class="lbl" style="width:22mm">발행일</td><td class="mono">2026-03-10</td></tr>
<tr><td class="lbl">투숙객</td><td>이출장</td>
    <td class="lbl">객실번호</td><td>1208호 (스탠다드 더블)</td></tr>
<tr><td class="lbl">체크인</td><td class="mono">2026-03-09 15:20</td>
    <td class="lbl">체크아웃</td><td class="mono">2026-03-10 10:40</td></tr>
<tr><td class="lbl">공급받는자</td><td colspan="3">{SUPPLIER['name']} ({SUPPLIER['bno']})</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:9mm">No</th><th>항목</th><th style="width:16mm">수량</th>
    <th style="width:26mm">단가</th><th style="width:26mm">금액</th></tr>
<tr><td class="c">1</td><td>객실료 (1박)</td><td class="c">1</td>
    <td class="num">80,000</td><td class="num">80,000</td></tr>
<tr><td class="c">2</td><td>조식 (1인)</td><td class="c">1</td>
    <td class="num">0</td><td class="num">0</td></tr>
<tr><td class="lbl" colspan="4">공급가액</td><td class="num">80,000</td></tr>
<tr><td class="lbl" colspan="4">부가가치세</td><td class="num">8,000</td></tr>
<tr><td class="lbl" colspan="4">합&nbsp;&nbsp;계</td><td class="num b" style="font-size:11pt">88,000</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">결제수단</td><td>법인카드 5327-88**-****-1234 (승인 33019822)</td></tr>
<tr><td class="lbl">사업자등록번호</td><td class="mono">{biz_no('605810222')}</td></tr>
<tr><td class="lbl">상호 / 대표자</td><td>대한호텔 부산 / 호텔장 {stamp('대한호텔',32)}</td></tr>
<tr><td class="lbl">주소</td><td class="small">부산광역시 해운대구 해운대해변로 100</td></tr>
</table>
<div class="note">· 숙박용역은 부가가치세 과세대상으로 사업 관련 지출 시 매입세액 공제가 가능합니다.<br>
· 출장여비 정산 시 본 영수증을 정산서에 첨부하십시오.</div>
"""
    docs.append(dict(no=41, slug="41_숙박영수증", size="A5", title="숙박 영수증",
                     html=html_doc("숙박영수증", body, size="A5", extra_css=CSS)))

    # 42. 항공권 e-티켓 확인증 및 영수증
    body = f"""
<div class="ticket">
  <div class="hd"><span class="brand">KOREA AIR &nbsp;코리아항공</span>
    <span class="small">e-Ticket Itinerary &amp; Receipt / 전자항공권 확인증</span></div>
  <table class="grid">
  <tr><td class="lbl" style="width:26mm">예약번호(PNR)</td><td class="mono b" style="width:30mm">7X9KQP</td>
      <td class="lbl" style="width:26mm">항공권번호</td><td class="mono">180-2411882910</td></tr>
  <tr><td class="lbl">탑승객</td><td>LEE/CHULJANG MR</td>
      <td class="lbl">발권일</td><td class="mono">2026-03-14</td></tr>
  <tr><td class="lbl">회원번호</td><td class="mono">KA-88123344</td>
      <td class="lbl">발권처</td><td>코리아항공 온라인</td></tr>
  </table>
  <div class="leg">
    <div class="ap"><b>GMP</b><span class="small">김포 08:30</span><br>
      <span class="xsmall">2026-03-18 (수)</span></div>
    <div class="arrow">KE-1201 &nbsp;·&nbsp; 1시간 10분 &nbsp;·&nbsp; B737-800 ▶</div>
    <div class="ap"><b>CJU</b><span class="small">제주 09:40</span><br>
      <span class="xsmall">2026-03-18 (수)</span></div>
  </div>
  <div class="leg">
    <div class="ap"><b>CJU</b><span class="small">제주 19:20</span><br>
      <span class="xsmall">2026-03-21 (토)</span></div>
    <div class="arrow">KE-1218 &nbsp;·&nbsp; 1시간 05분 &nbsp;·&nbsp; B737-800 ▶</div>
    <div class="ap"><b>GMP</b><span class="small">김포 20:25</span><br>
      <span class="xsmall">2026-03-21 (토)</span></div>
  </div>
  <table class="grid">
  <tr><th style="width:34%">운임 내역 (Fare Details)</th><th>금액 (KRW)</th></tr>
  <tr><td class="lbl l">항공운임 (Fare) - 왕복</td><td class="num">116,000</td></tr>
  <tr><td class="lbl l">부가가치세 (VAT 10%)</td><td class="num">11,600</td></tr>
  <tr><td class="lbl l">공항시설사용료 (BP)</td><td class="num">8,000</td></tr>
  <tr><td class="lbl l">유류할증료 (YQ)</td><td class="num">3,000</td></tr>
  <tr><td class="lbl l b">총 결제금액</td><td class="num b" style="font-size:11pt">138,600</td></tr>
  </table>
  <table class="grid" style="margin-top:2mm">
  <tr><td class="lbl" style="width:26mm">결제수단</td><td>법인카드 5327-88**-****-1234 / 승인 55102384</td></tr>
  <tr><td class="lbl">구매자(사업자)</td><td>{SUPPLIER['name']} ({SUPPLIER['bno']})</td></tr>
  <tr><td class="lbl">발행 항공사</td><td>코리아항공(주) ({biz_no('110810444')})</td></tr>
  </table>
  <div class="note">· 국내선 항공운임은 부가가치세 과세대상으로 매입세액 공제가 가능합니다.
    (국제선은 영세율)<br>
  · 공항시설사용료는 과세대상이 아니며, 유류할증료는 운임에 포함하여 과세됩니다.<br>
  · 탑승 수속은 출발 1시간 전까지 완료하여 주십시오.</div>
  <div style="text-align:center;margin-top:2mm">{barcode('1802411882910-7X9KQP', 76)}</div>
</div>
"""
    docs.append(dict(no=42, slug="42_항공권_e티켓_영수증", size="A4",
                     title="항공권 e-티켓 영수증",
                     html=html_doc("항공권e티켓", body, extra_css=CSS)))

    # 43. KTX 승차권 영수증
    body = slip(f"""
  <div class="ttl">승 차 권 (영 수 증)</div>
  <div style="text-align:center" class="xsmall">대한철도공사 (가상 샘플)</div>
  <hr>
  <div class="row"><span>발권번호</span><span>26030-9-0114-2288</span></div>
  <div class="row"><span>발권일시</span><span>2026/03/07 16:02</span></div>
  <hr>
  <div style="text-align:center" class="b" style="font-size:11pt">KTX 101</div>
  <div class="row"><span>출발</span><span>서울 03/09(월) 09:00</span></div>
  <div class="row"><span>도착</span><span>부산 03/09(월) 11:38</span></div>
  <div class="row"><span>좌석</span><span>7호차 12A (일반실 · 순방향)</span></div>
  <div class="row"><span>인원</span><span>어른 1명</span></div>
  <hr>
  <div style="text-align:center" class="b">[ 돌아오는 열차 ]</div>
  <div class="row"><span>출발</span><span>부산 03/10(화) 17:10</span></div>
  <div class="row"><span>도착</span><span>서울 03/10(화) 19:48</span></div>
  <div class="row"><span>좌석</span><span>4호차 05D (일반실)</span></div>
  <hr>
  <div class="row"><span>운임 (편도 59,800 x2)</span><span>119,600</span></div>
  <div class="row"><span>할인</span><span>0</span></div>
  <div class="row b" style="font-size:10pt"><span>결제금액</span><span>119,600</span></div>
  <hr>
  <div class="row"><span>공급가액</span><span>108,727</span></div>
  <div class="row"><span>부가세</span><span>10,873</span></div>
  <div class="row"><span>결제수단</span><span>법인카드(승인 61220034)</span></div>
  <div class="row"><span>사업자번호</span><span>{biz_no('314820555')}</span></div>
  <hr>
  <div class="xsmall">· 철도 여객운송은 과세대상으로 매입세액 공제가 가능합니다.</div>
  <div class="xsmall">· 반환 시 수수료가 부과될 수 있습니다.</div>
  <hr>
  <div style="text-align:center">{barcode('KTX-2603090114 2288', 60)}</div>
""")
    docs.append(dict(no=43, slug="43_KTX승차권영수증", size="SLIP",
                     title="KTX 승차권 영수증",
                     html=html_doc("KTX승차권", body, size="SLIP",
                                   watermark="샘플", note="")))
    return docs
