# -*- coding: utf-8 -*-
"""그룹 3. 내부 회계 증빙 - 지출결의서/품의서/여비정산서/법인카드내역/경조사비/전도금"""
from common import SUPPLIER, won, kor_won, stamp, html_doc

CSS = """
h1.title { border:1.6pt solid #111; padding:2.4mm 0; }
.approval { float:right; margin:0 0 2mm 3mm; }
.approval table { border-collapse:collapse; }
.approval td { border:.7pt solid #222; text-align:center; font-size:7.5pt; }
.approval td.h { background:#f0f0f0; font-weight:700; height:6mm; width:20mm; }
.approval td.s { height:17mm; vertical-align:middle; }
.approval td.side { writing-mode:vertical-rl; text-orientation:upright; width:6mm;
                    background:#f0f0f0; font-weight:700; letter-spacing:2px; }
.clear { clear:both; }
"""


def approval(cols=("담당", "대리", "과장", "부장", "대표이사"), sealed=3, label="결　재"):
    h = "".join(f'<td class="h">{c}</td>' for c in cols)
    s = "".join(f'<td class="s">{stamp(c, 34) if i < sealed else "&nbsp;"}</td>'
                for i, c in enumerate(["김담당", "이대리", "박과장", "최부장", "김한빛"][:len(cols)]))
    return f"""<div class="approval"><table>
<tr><td class="side" rowspan="2">{label}</td>{h}</tr><tr>{s}</tr></table></div>"""


def build():
    docs = []

    # 17. 지출결의서
    lines = [("2026-03-05", "사무용품 구입 (A4용지 외)", "소모품비", "신용카드", 380_000, "카드전표 첨부"),
             ("2026-03-11", "거래처 접대 (중식)", "접대비", "법인카드", 154_000, "카드전표·참석자명단"),
             ("2026-03-17", "택배 발송비", "운반비", "현금", 32_000, "간이영수증"),
             ("2026-03-22", "직원 교육 수강료", "교육훈련비", "계좌이체", 660_000, "계산서(면세)"),
             ("2026-03-28", "사무실 정수기 임차료", "지급임차료", "자동이체", 44_000, "세금계산서")]
    total = sum(l[4] for l in lines)
    rows = "".join(
        f'<tr><td class="c">{i}</td><td class="c mono">{d}</td><td>{nm}</td>'
        f'<td class="c">{acc}</td><td class="c">{pay}</td>'
        f'<td class="num">{won(amt)}</td><td class="small">{rem}</td></tr>'
        for i, (d, nm, acc, pay, amt, rem) in enumerate(lines, 1))
    rows += "".join('<tr>' + '<td style="height:6.5mm">&nbsp;</td>' * 7 + '</tr>' for _ in range(3))
    body = f"""
{approval()}
<h1 class="title sm">지 출 결 의 서</h1>
<div class="clear"></div>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:24mm">기안일자</td><td class="mono" style="width:34mm">2026-03-31</td>
    <td class="lbl" style="width:24mm">기안부서</td><td style="width:34mm">경영지원팀</td>
    <td class="lbl" style="width:24mm">기안자</td><td>김담당 사원</td></tr>
<tr><td class="lbl">문서번호</td><td class="mono">경지-2026-0331-14</td>
    <td class="lbl">지출예정일</td><td class="mono">2026-04-05</td>
    <td class="lbl">지출방법</td><td>법인계좌 이체 / 법인카드</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:9mm">No</th><th style="width:24mm">지출일자</th><th>적요(지출내용)</th>
    <th style="width:24mm">계정과목</th><th style="width:20mm">결제수단</th>
    <th style="width:26mm">금액(원)</th><th style="width:34mm">증빙</th></tr>
{rows}
<tr><td class="lbl" colspan="5">합&nbsp;&nbsp;계</td><td class="num b">{won(total)}</td>
    <td class="small">증빙 5매 첨부</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:24mm">금액(한글)</td><td class="b">{kor_won(total)}</td></tr>
<tr><td class="lbl">지출사유</td><td class="small">
   2026년 3월 중 발생한 부서 운영경비 지출분에 대하여 위와 같이 결의하오니 재가하여 주시기 바랍니다.</td></tr>
<tr><td class="lbl">첨부서류</td><td class="small">
   1. 신용카드 매출전표 2매 &nbsp; 2. 간이영수증 1매 &nbsp; 3. 계산서 1매 &nbsp; 4. 전자세금계산서 1매</td></tr>
</table>
<div class="footer-org">{SUPPLIER['name']}</div>
"""
    docs.append(dict(no=17, slug="17_지출결의서", size="A4", title="지출결의서",
                     html=html_doc("지출결의서", body, extra_css=CSS)))

    # 18. 구매품의서
    body = f"""
{approval()}
<h1 class="title sm">구 매 품 의 서</h1>
<div class="clear"></div>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:24mm">문서번호</td><td class="mono" style="width:36mm">구매-2026-0221-03</td>
    <td class="lbl" style="width:24mm">기안일자</td><td class="mono" style="width:30mm">2026-02-21</td>
    <td class="lbl" style="width:20mm">보존연한</td><td>5년</td></tr>
<tr><td class="lbl">기안부서</td><td>전산팀</td>
    <td class="lbl">기안자</td><td>정검수 대리</td>
    <td class="lbl">시행일</td><td class="mono">2026-03-02</td></tr>
<tr><td class="lbl">제&nbsp;&nbsp;목</td><td colspan="5" class="b">ERP 연동 모듈 개발 용역 구매 품의의 건</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:24mm;height:24mm">품의 배경<br>및 목적</td><td class="small">
  · 현행 레거시 재고관리 시스템과 신규 ERP 간 데이터 연동이 수작업으로 이루어져 월 40시간의
    비효율이 발생하고 있음<br>
  · 연동 모듈 도입 시 마감 소요기간이 5일 → 2일로 단축될 것으로 예상됨<br>
  · 이에 전문 업체를 통한 개발 용역을 구매하고자 함</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:9mm">No</th><th>구매 품목</th><th style="width:18mm">수량</th>
    <th style="width:28mm">공급가액</th><th style="width:24mm">부가세</th><th style="width:28mm">합계</th></tr>
<tr><td class="c">1</td><td>ERP 연동 모듈 개발(설계·구현)</td><td class="c">1식</td>
    <td class="num">8,000,000</td><td class="num">800,000</td><td class="num">8,800,000</td></tr>
<tr><td class="c">2</td><td>데이터 마이그레이션 용역</td><td class="c">1식</td>
    <td class="num">3,000,000</td><td class="num">300,000</td><td class="num">3,300,000</td></tr>
<tr><td class="c">3</td><td>사용자 교육 및 매뉴얼 제작</td><td class="c">3회</td>
    <td class="num">1,500,000</td><td class="num">150,000</td><td class="num">1,650,000</td></tr>
<tr><td class="lbl" colspan="3">합&nbsp;&nbsp;계</td><td class="num b">12,500,000</td>
    <td class="num b">1,250,000</td><td class="num b">13,750,000</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:24mm">업체선정</td><td class="small">
   3개사 견적 비교 후 최저가 및 유사 구축실적 보유 업체인 (주)한빛테크놀로지 선정
   (A사 15,400,000원 / B사 14,300,000원 / 한빛테크 13,750,000원)</td></tr>
<tr><td class="lbl">예산과목</td><td>정보화사업비 - 소프트웨어개발비 (2026년 예산 잔액 21,000,000원)</td></tr>
<tr><td class="lbl">기대효과</td><td class="small">연간 약 480시간 업무시간 절감(환산 약 12,000,000원), 마감 정확도 향상</td></tr>
</table>
<div class="sign-area">위와 같이 품의하오니 재가하여 주시기 바랍니다.</div>
<div class="footer-org">{SUPPLIER['name']}</div>
"""
    docs.append(dict(no=18, slug="18_구매품의서", size="A4", title="구매품의서",
                     html=html_doc("구매품의서", body, extra_css=CSS)))

    # 19. 출장여비 정산서
    trips = [("2026-03-09", "KTX 서울→부산 (왕복)", "교통비", 119_600, "승차권 영수증"),
             ("2026-03-09", "부산 시내 택시 3회", "교통비", 34_800, "택시영수증 3매"),
             ("2026-03-09", "숙박 (부산 1박)", "숙박비", 88_000, "숙박영수증"),
             ("2026-03-10", "식대 (3식)", "식비", 42_000, "카드전표"),
             ("2026-03-10", "일비 (2일 × 20,000원)", "일비", 40_000, "사규 제32조"),
             ("2026-03-10", "거래처 미팅 다과", "접대비", 23_000, "간이영수증")]
    tt = sum(t[3] for t in trips)
    adv = 300_000
    rows = "".join(f'<tr><td class="c">{i}</td><td class="c mono">{d}</td><td>{nm}</td>'
                   f'<td class="c">{acc}</td><td class="num">{won(a)}</td>'
                   f'<td class="small">{rem}</td></tr>'
                   for i, (d, nm, acc, a, rem) in enumerate(trips, 1))
    body = f"""
{approval(("담당","팀장","부서장","대표이사"), sealed=3)}
<h1 class="title sm">국 내 출 장 여 비 정 산 서</h1>
<div class="clear"></div>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:22mm">소속/직급</td><td style="width:36mm">영업팀 / 과장</td>
    <td class="lbl" style="width:22mm">성명</td><td style="width:30mm">이출장 {stamp('이출장',30)}</td>
    <td class="lbl" style="width:22mm">사번</td><td>2019-0142</td></tr>
<tr><td class="lbl">출장기간</td><td>2026-03-09 ~ 2026-03-10 (1박 2일)</td>
    <td class="lbl">출장지</td><td>부산광역시</td>
    <td class="lbl">동행자</td><td>없음</td></tr>
<tr><td class="lbl">출장목적</td><td colspan="5">부산 지역 신규 거래처(대한상사) 방문 및 계약 협의</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:9mm">No</th><th style="width:24mm">일자</th><th>내역</th>
    <th style="width:22mm">비목</th><th style="width:26mm">금액(원)</th><th style="width:34mm">증빙</th></tr>
{rows}
<tr><td class="lbl" colspan="4">지 출 합 계</td><td class="num b">{won(tt)}</td><td>&nbsp;</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">가지급금(선지급)</td><td class="num" style="width:34mm">{won(adv)}</td>
    <td class="lbl" style="width:26mm">정산 지출액</td><td class="num" style="width:34mm">{won(tt)}</td>
    <td class="lbl" style="width:26mm">반납액</td><td class="num b">{won(adv - tt)}</td></tr>
</table>
<div class="note">· 반납액 {won(adv - tt)}원은 2026-03-12 법인계좌로 입금 완료<br>
· 증빙 원본 {len(trips)}매를 본 정산서 뒷면에 첨부함</div>
<div class="sign-area">위와 같이 출장 여비를 정산합니다. &nbsp;&nbsp; 2026년 03월 11일<br>
정산자 : 영업팀 이출장 (인) {stamp('이출장',36)}</div>
<div class="footer-org">{SUPPLIER['name']}</div>
"""
    docs.append(dict(no=19, slug="19_출장여비정산서", size="A4", title="출장여비 정산서",
                     html=html_doc("출장여비정산서", body, extra_css=CSS)))

    # 20. 법인카드 사용내역서
    use = [("03-03", "㈜한빛문구 역삼점", "사무용품", "소모품비", 45_000, "김담당"),
           ("03-05", "한빛문구 역삼점", "A4용지 외", "소모품비", 380_000, "김담당"),
           ("03-11", "고향식당", "거래처 중식 접대(4인)", "접대비", 154_000, "이출장"),
           ("03-13", "대한주유소 판교점", "차량 주유(법인차량 12가3456)", "차량유지비", 92_000, "박과장"),
           ("03-18", "코리아항공", "국내선 항공권(김포-제주)", "여비교통비", 138_600, "이출장"),
           ("03-21", "대한호텔 제주", "숙박 1박", "여비교통비", 132_000, "이출장"),
           ("03-25", "클라우드서비스(해외)", "서버 사용료", "지급수수료", 217_400, "정검수"),
           ("03-27", "우리동네카페", "사내 회의 다과", "복리후생비", 28_500, "김담당")]
    ut = sum(u[4] for u in use)
    rows = "".join(f'<tr><td class="c mono">{d}</td><td>{m}</td><td class="small">{c}</td>'
                   f'<td class="c">{acc}</td><td class="num">{won(a)}</td>'
                   f'<td class="c">{who}</td><td class="c">O</td></tr>'
                   for d, m, c, acc, a, who in use)
    body = f"""
{approval(("담당","팀장","부서장"), sealed=3)}
<h1 class="title sm">법 인 카 드 사 용 내 역 서</h1>
<div class="clear"></div>
<div class="subtitle">2026년 3월분 (사용기간 2026-03-01 ~ 2026-03-31)</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:24mm">카드사</td><td style="width:34mm">대한카드(법인)</td>
    <td class="lbl" style="width:24mm">카드번호</td><td class="mono" style="width:38mm">5327-88**-****-1234</td>
    <td class="lbl" style="width:22mm">결제계좌</td><td>{SUPPLIER['bank']} {SUPPLIER['acct']}</td></tr>
<tr><td class="lbl">사용부서</td><td>경영지원팀 외</td>
    <td class="lbl">결제일</td><td class="mono">2026-04-15</td>
    <td class="lbl">한도</td><td>월 5,000,000원</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:16mm">사용일</th><th style="width:44mm">가맹점명</th><th>사용내용</th>
    <th style="width:24mm">계정과목</th><th style="width:24mm">금액(원)</th>
    <th style="width:18mm">사용자</th><th style="width:16mm">전표<br>첨부</th></tr>
{rows}
<tr><td class="lbl" colspan="4">합&nbsp;&nbsp;계</td><td class="num b">{won(ut)}</td>
    <td colspan="2" class="c small">전표 {len(use)}매</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">매입세액 공제분</td><td class="num" style="width:32mm">{won(ut - 217400 - 154000)}</td>
    <td class="lbl" style="width:26mm">불공제분</td><td class="num" style="width:32mm">{won(217400 + 154000)}</td>
    <td class="lbl" style="width:26mm">불공제 사유</td><td class="small">접대비, 해외 사용분</td></tr>
</table>
<div class="note">· 개인적 용도 사용분은 없으며, 전 건에 대한 매출전표를 첨부함<br>
· 접대비는 건당 3만원 초과분으로 지출 상대방·목적을 별도 기록함</div>
<div class="footer-org">{SUPPLIER['name']}</div>
"""
    docs.append(dict(no=20, slug="20_법인카드사용내역서", size="A4",
                     title="법인카드 사용내역서",
                     html=html_doc("법인카드사용내역서", body, extra_css=CSS)))

    # 21. 경조사비 지급 품의서 (청첩장 사본 첨부)
    body = f"""
{approval(("담당","팀장","부서장","대표이사"), sealed=4)}
<h1 class="title sm">경 조 사 비 지 급 품 의 서</h1>
<div class="clear"></div>
<table class="grid" style="margin-top:3mm">
<tr><td class="lbl" style="width:24mm">문서번호</td><td class="mono" style="width:36mm">경지-2026-0314-08</td>
    <td class="lbl" style="width:24mm">기안일자</td><td class="mono">2026-03-14</td></tr>
<tr><td class="lbl">경조 구분</td><td class="b">결혼 (거래처 경조사)</td>
    <td class="lbl">행사일자</td><td class="mono">2026-03-21 (토) 12:00</td></tr>
<tr><td class="lbl">대상자</td><td>대한상사 구매팀 김대한 부장 (자녀 결혼)</td>
    <td class="lbl">관계</td><td>주요 거래처 담당자</td></tr>
<tr><td class="lbl">장소</td><td colspan="3">서울 강남구 ○○웨딩홀 3층 그랜드홀</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:24mm">지급금액</td>
    <td class="b" style="font-size:12pt">￦ 200,000 <span class="small">({kor_won(200000)})</span></td>
    <td class="lbl" style="width:22mm">계정과목</td><td style="width:30mm">접대비 (경조사비)</td></tr>
<tr><td class="lbl">지급방법</td><td>현금 (경조사비 봉투 전달)</td>
    <td class="lbl">지급일</td><td class="mono">2026-03-20</td></tr>
<tr><td class="lbl">참석자</td><td colspan="3">영업팀 이출장 과장 (화환 별도 발송 : 100,000원)</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:24mm;height:34mm">첨부 증빙<br>(청첩장 사본)</td>
    <td class="c" style="color:#888">
      <div style="border:1pt dashed #999;padding:6mm;margin:2mm 20mm;background:#fafafa">
        <div class="b" style="font-size:11pt;letter-spacing:3px">청 첩 장 사 본 부 착 란</div>
        <div class="small" style="margin-top:2mm">
          (청첩장·부고장 사본 또는 화환 주문내역을 이 칸에 부착)</div>
      </div></td></tr>
</table>
<div class="note">
· 경조사비는 건당 20만원 이내로 법정 증빙(세금계산서 등) 수취 의무가 면제되나,
  청첩장·부고장 사본 등 사실관계를 확인할 수 있는 서류를 반드시 첨부하여야 함
  (법인세법 시행령 제41조, 접대비 손금산입 한도 내).<br>
· 20만원 초과 시 전액 손금불산입 대상이므로 지급 전 사전 승인 필수.</div>
<div class="footer-org">{SUPPLIER['name']}</div>
"""
    docs.append(dict(no=21, slug="21_경조사비지급품의서", size="A4",
                     title="경조사비 지급 품의서",
                     html=html_doc("경조사비지급품의서", body, extra_css=CSS)))

    # 22. 소액현금(전도금) 정산서
    pc = [("03-02", "우편·등기 발송", "통신비", 12_800, 0),
          ("03-06", "사무실 생수 구입", "복리후생비", 24_000, 0),
          ("03-09", "퀵서비스(계약서 송부)", "운반비", 18_000, 0),
          ("03-15", "명함 제작 (3인분)", "도서인쇄비", 45_000, 0),
          ("03-19", "회의용 다과", "복리후생비", 31_500, 0),
          ("03-24", "청소용품 구입", "소모품비", 16_700, 0),
          ("03-30", "등기부등본 발급 수수료", "지급수수료", 3_000, 0)]
    pt = sum(p[3] for p in pc)
    fund, bal_prev = 500_000, 112_400
    rows = "".join(f'<tr><td class="c mono">{d}</td><td>{nm}</td><td class="c">{acc}</td>'
                   f'<td class="num">{won(a)}</td>'
                   f'<td class="num">{won(fund + bal_prev - sum(x[3] for x in pc[:i+1]))}</td>'
                   f'<td class="c small">영수증</td></tr>'
                   for i, (d, nm, acc, a, _) in enumerate(pc))
    body = f"""
{approval(("담당","팀장","부서장"), sealed=3)}
<h1 class="title sm">소 액 현 금 (전 도 금) 정 산 서</h1>
<div class="clear"></div>
<div class="subtitle">2026년 3월분 &nbsp;|&nbsp; 관리부서 : 경영지원팀 &nbsp;|&nbsp; 관리자 : 김담당</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:28mm">전월이월 잔액</td><td class="num" style="width:30mm">{won(bal_prev)}</td>
    <td class="lbl" style="width:28mm">당월 보충액</td><td class="num" style="width:30mm">{won(fund)}</td>
    <td class="lbl" style="width:24mm">당월 사용액</td><td class="num">{won(pt)}</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:18mm">사용일</th><th>적요</th><th style="width:26mm">계정과목</th>
    <th style="width:24mm">지출액</th><th style="width:26mm">잔액</th><th style="width:22mm">증빙</th></tr>
{rows}
<tr><td class="lbl" colspan="3">합&nbsp;&nbsp;계</td><td class="num b">{won(pt)}</td>
    <td class="num b">{won(fund + bal_prev - pt)}</td><td class="c small">{len(pc)}매</td></tr>
</table>
<table class="grid" style="margin-top:3mm">
<tr><th colspan="4">현 금 실 사 확 인 (2026-03-31 18:00 기준)</th></tr>
<tr><td class="lbl" style="width:26mm">장부상 잔액</td><td class="num" style="width:34mm">{won(fund + bal_prev - pt)}</td>
    <td class="lbl" style="width:26mm">실제 보유 현금</td><td class="num">{won(fund + bal_prev - pt)}</td></tr>
<tr><td class="lbl">과부족</td><td class="num">0</td>
    <td class="lbl">실사자</td><td>경영지원팀 박과장 {stamp('박과장',30)}</td></tr>
</table>
<div class="note">· 건당 3만원 이하 지출은 간이영수증으로 증빙 가능 (법인세법 시행령 제158조)<br>
· 3만원 초과 지출은 반드시 세금계산서·계산서·카드전표·현금영수증 중 하나를 수취</div>
<div class="footer-org">{SUPPLIER['name']}</div>
"""
    docs.append(dict(no=22, slug="22_소액현금_전도금정산서", size="A4",
                     title="소액현금(전도금) 정산서",
                     html=html_doc("소액현금정산서", body, extra_css=CSS)))
    return docs
