# -*- coding: utf-8 -*-
"""그룹 8. 무역 증빙 - Commercial Invoice / Packing List / 수입신고필증 / 선하증권"""
from common import SUPPLIER, won, stamp, html_doc, barcode, biz_no

CSS = """
h1.title { border-top:2pt solid #111; border-bottom:2pt solid #111; padding:2mm 0;
           letter-spacing:6px; }
table.grid td, table.grid th { font-size:7.8pt; }
.en { font-family:'NG'; }
.box-hd { background:#eee; font-weight:700; font-size:7pt; padding:.6mm 1.2mm;
          border-bottom:.5pt solid #999; }
.decl { border:1.2pt solid #222; }
.decl .r { display:flex; }
.decl .c { border-right:.6pt solid #999; border-bottom:.6pt solid #999; padding:1mm 1.4mm;
           flex:1; min-height:8mm; }
.decl .c:last-child { border-right:0; }
.decl .k { font-size:6.6pt; color:#555; display:block; }
.decl .v { font-size:8pt; font-weight:700; }
"""

SELLER = "GLOBAL SOFT SOLUTIONS PTE. LTD.<br>10 ANSON ROAD, #12-05, SINGAPORE 079903<br>TEL +65-0000-0000"


def build():
    docs = []
    items = [("Notebook Computer, 14\" i7/16GB", "NB-X14-I7", "EA", 50, 300.00, 15_000.00),
             ("Docking Station, USB-C", "DS-C90", "EA", 50, 45.00, 2_250.00),
             ("Spare Battery Pack", "BT-55W", "EA", 20, 32.50, 650.00)]
    total_usd = sum(i[5] for i in items)

    # 44. Commercial Invoice
    rows = "".join(
        f'<tr><td class="c">{n}</td><td>{d}</td><td class="c mono">{code}</td>'
        f'<td class="c">{u}</td><td class="c">{q}</td>'
        f'<td class="num">{p:,.2f}</td><td class="num">{a:,.2f}</td></tr>'
        for n, (d, code, u, q, p, a) in enumerate(items, 1))
    body = f"""
<h1 class="title sm">COMMERCIAL INVOICE</h1>
<div class="subtitle">상 업 송 장</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">① Shipper/Seller</td><td colspan="3" class="en">{SELLER}</td></tr>
<tr><td class="lbl">② Consignee</td><td colspan="3" class="en">
    {SUPPLIER['name']} (HANBIT TECHNOLOGY CO., LTD.)<br>
    8F, 123 TEHERAN-RO, GANGNAM-GU, SEOUL, KOREA<br>
    BUSINESS REG. NO. {SUPPLIER['bno']} &nbsp;|&nbsp; TEL +82-2-555-1234</td></tr>
<tr><td class="lbl">③ Notify Party</td><td colspan="3" class="en">SAME AS CONSIGNEE</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">④ Invoice No. &amp; Date</td>
    <td class="mono" style="width:44mm">GS-2026-0442 / 2026-03-05</td>
    <td class="lbl" style="width:26mm">⑤ L/C No. &amp; Date</td>
    <td class="mono">M0000-2603-00123 / 2026-02-20</td></tr>
<tr><td class="lbl">⑥ Buyer (if other)</td><td>SAME AS CONSIGNEE</td>
    <td class="lbl">⑦ Payment Terms</td><td>T/T 30 DAYS AFTER B/L DATE</td></tr>
<tr><td class="lbl">⑧ Port of Loading</td><td>SINGAPORE, SINGAPORE</td>
    <td class="lbl">⑨ Final Destination</td><td>INCHEON, KOREA</td></tr>
<tr><td class="lbl">⑩ Carrier / Vessel</td><td>OCEAN STAR V.0142E</td>
    <td class="lbl">⑪ Sailing on or about</td><td class="mono">2026-03-08</td></tr>
<tr><td class="lbl">⑫ Price Term</td><td class="b">CIF INCHEON</td>
    <td class="lbl">⑬ Currency</td><td class="b">USD</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:9mm">No</th><th>⑭ Description of Goods</th>
    <th style="width:26mm">Model</th><th style="width:14mm">Unit</th>
    <th style="width:16mm">Q'ty</th><th style="width:26mm">Unit Price</th>
    <th style="width:30mm">Amount (USD)</th></tr>
{rows}
<tr><td colspan="6" class="lbl">TOTAL (FOB VALUE)</td><td class="num b">{total_usd:,.2f}</td></tr>
<tr><td colspan="6" class="lbl">FREIGHT</td><td class="num">850.00</td></tr>
<tr><td colspan="6" class="lbl">INSURANCE</td><td class="num">120.00</td></tr>
<tr><td colspan="6" class="lbl b">TOTAL CIF AMOUNT</td>
    <td class="num b" style="font-size:10pt">{total_usd + 970:,.2f}</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:30mm">⑮ Total Amount in Words</td>
    <td class="b en">SAY US DOLLARS EIGHTEEN THOUSAND EIGHT HUNDRED SEVENTY ONLY</td></tr>
<tr><td class="lbl">⑯ Country of Origin</td><td>SINGAPORE / MALAYSIA (as marked)</td></tr>
<tr><td class="lbl">⑰ HS Code</td><td class="mono">8471.30-0000, 8473.30-9000, 8507.60-0000</td></tr>
<tr><td class="lbl">⑱ Packing</td><td>12 CARTONS, TOTAL G.W. 318.5 KGS / N.W. 286.0 KGS</td></tr>
<tr><td class="lbl">⑲ Shipping Marks</td><td class="en">HANBIT / INCHEON / C/NO. 1-12 / MADE IN SINGAPORE</td></tr>
</table>
<div class="note en">We hereby certify that the contents of this invoice are true and correct.</div>
<div class="sign-area">SINGAPORE, 05 MARCH 2026</div>
<div class="footer-org en" style="font-size:11pt;letter-spacing:1px">
  GLOBAL SOFT SOLUTIONS PTE. LTD. {stamp('SEAL',40)}</div>
"""
    docs.append(dict(no=44, slug="44_Commercial_Invoice", size="A4",
                     title="Commercial Invoice (상업송장)",
                     html=html_doc("Commercial Invoice", body, extra_css=CSS)))

    # 45. Packing List
    ctn = [(("1-6"), "Notebook Computer", 50, "8 EA/CTN", 24.5, 147.0, 26.0, 156.0,
            "60 x 40 x 35"),
           (("7-10"), "Docking Station", 50, "13 EA/CTN", 18.0, 72.0, 20.5, 82.0,
            "50 x 35 x 30"),
           (("11-12"), "Spare Battery Pack", 20, "10 EA/CTN", 33.5, 67.0, 40.25, 80.5,
            "45 x 35 x 28")]
    rows = "".join(
        f'<tr><td class="c">{c}</td><td>{d}</td><td class="c">{q}</td><td class="c">{pk}</td>'
        f'<td class="num">{nw:,.1f}</td><td class="num">{tnw:,.1f}</td>'
        f'<td class="num">{gw:,.1f}</td><td class="num">{tgw:,.1f}</td>'
        f'<td class="c mono">{dim}</td></tr>'
        for c, d, q, pk, nw, tnw, gw, tgw, dim in ctn)
    body = f"""
<h1 class="title sm">PACKING LIST</h1>
<div class="subtitle">포 장 명 세 서</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">Shipper</td><td colspan="3" class="en">{SELLER}</td></tr>
<tr><td class="lbl">Consignee</td><td colspan="3" class="en">
    {SUPPLIER['name']} (HANBIT TECHNOLOGY CO., LTD.), SEOUL, KOREA</td></tr>
<tr><td class="lbl">Invoice No. / Date</td><td class="mono" style="width:40mm">GS-2026-0442 / 2026-03-05</td>
    <td class="lbl" style="width:26mm">B/L No.</td><td class="mono">OSLSGINC26030088</td></tr>
<tr><td class="lbl">Vessel / Voyage</td><td>OCEAN STAR V.0142E</td>
    <td class="lbl">Container No.</td><td class="mono">OSLU 123456-7 / 20'DV</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:16mm">C/NO.</th><th>Description</th><th style="width:14mm">Q'ty</th>
    <th style="width:22mm">Packing</th><th style="width:20mm">N.W.<br>(kg/ctn)</th>
    <th style="width:20mm">Total N.W.<br>(kg)</th><th style="width:20mm">G.W.<br>(kg/ctn)</th>
    <th style="width:20mm">Total G.W.<br>(kg)</th><th style="width:28mm">Measurement<br>(cm)</th></tr>
{rows}
<tr><td class="lbl">TOTAL</td><td class="c">12 CARTONS</td><td class="c b">120</td>
    <td>&nbsp;</td><td>&nbsp;</td><td class="num b">286.0</td><td>&nbsp;</td>
    <td class="num b">318.5</td><td class="c">1.85 CBM</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:30mm">Shipping Marks</td>
    <td class="en">HANBIT<br>INCHEON<br>C/NO. 1-12<br>MADE IN SINGAPORE</td>
    <td class="lbl" style="width:26mm">Port of Loading</td><td>SINGAPORE</td></tr>
<tr><td class="lbl">Port of Discharge</td><td>INCHEON, KOREA</td>
    <td class="lbl">Sailing Date</td><td class="mono">2026-03-08</td></tr>
</table>
<div class="note en">We hereby certify that the contents of this packing list are true and correct.</div>
<div class="sign-area">SINGAPORE, 05 MARCH 2026</div>
<div class="footer-org en" style="font-size:11pt">GLOBAL SOFT SOLUTIONS PTE. LTD. {stamp('SEAL',40)}</div>
"""
    docs.append(dict(no=45, slug="45_Packing_List", size="A4",
                     title="Packing List (포장명세서)",
                     html=html_doc("Packing List", body, extra_css=CSS)))

    # 46. 수입신고필증
    def cell(k, v, flex=1):
        return f'<div class="c" style="flex:{flex}"><span class="k">{k}</span><span class="v">{v}</span></div>'
    duty, edu_t, vat_i = 0, 0, 2_100_000
    body = f"""
<div style="display:flex;justify-content:space-between" class="small">
  <span>관세청 UNI-PASS</span><span>[별지 제1-2호서식] 준용 &nbsp;|&nbsp; (갑지)</span></div>
<h1 class="title sm" style="margin-top:1mm">수 입 신 고 필 증</h1>
<div class="subtitle">(수입자 보관용) &nbsp;|&nbsp; ※ 처리기간 : 즉시</div>
<div class="decl" style="margin-top:2mm">
  <div class="r">{cell('① 신고번호','41099-26-0123456M',2)}{cell('② 신고일','2026-03-17')}
      {cell('③ 세관·과','인천세관 / 통관지원과')}{cell('⑥ 입항일','2026-03-15')}</div>
  <div class="r">{cell('④ B/L(AWB)번호','OSLSGINC26030088',2)}{cell('⑤ 화물관리번호','26OSL0142-0001')}
      {cell('⑦ 반입일','2026-03-16')}{cell('⑧ 징수형태','11 (신고납부)')}</div>
  <div class="r">{cell('⑨ 신고자','대한관세사무소 / 관세사 김통관',2)}
      {cell('⑩ 수입자',f"{SUPPLIER['name']} ({SUPPLIER['bno']})",2)}</div>
  <div class="r">{cell('⑪ 납세의무자',f"{SUPPLIER['name']} / 통관고유부호 HANBIT-1-01-1-01-9",3)}
      {cell('⑫ 무역거래처','GLOBAL SOFT SOLUTIONS PTE. LTD.')}</div>
  <div class="r">{cell('⑬ 공급자','GLOBAL SOFT SOLUTIONS PTE. LTD.',2)}
      {cell('⑭ 원산지증명서 유무','Y (FORM AK)')}{cell('⑮ 운송형태','10-FC (해상 컨테이너)')}</div>
  <div class="r">{cell('⑯ 적출국','SG (싱가포르)')}{cell('⑰ 선기명','OCEAN STAR')}
      {cell('⑱ 검사(반입)장소','인천항 CFS')}{cell('⑲ 총중량','318.5 KG')}</div>
</div>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:12mm">란<br>번호</th><th style="width:26mm">HS부호</th>
    <th>품명 · 규격</th><th style="width:18mm">수량</th>
    <th style="width:26mm">단가(USD)</th><th style="width:30mm">금액(USD)</th></tr>
<tr><td class="c">1</td><td class="c mono">8471.30-0000</td>
    <td>NOTEBOOK COMPUTER 14" i7/16GB (NB-X14-I7)</td><td class="c">50 EA</td>
    <td class="num">300.00</td><td class="num">15,000.00</td></tr>
<tr><td class="c">2</td><td class="c mono">8473.30-9000</td>
    <td>DOCKING STATION USB-C (DS-C90)</td><td class="c">50 EA</td>
    <td class="num">45.00</td><td class="num">2,250.00</td></tr>
<tr><td class="c">3</td><td class="c mono">8507.60-0000</td>
    <td>LITHIUM-ION BATTERY PACK (BT-55W)</td><td class="c">20 EA</td>
    <td class="num">32.50</td><td class="num">650.00</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">㉑ 결제금액</td><td class="b" style="width:44mm">CIF - USD - 18,870.00</td>
    <td class="lbl" style="width:24mm">㉒ 환율</td><td class="mono">1,342.50 (2026-03-17 과세환율)</td></tr>
<tr><td class="lbl">㉓ 총과세가격</td><td class="num b">￦ 25,332,975</td>
    <td class="lbl">㉔ 운임·보험료</td><td class="num">포함 (CIF)</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:30mm">세종</th><th style="width:30mm">세율(구분)</th>
    <th style="width:36mm">과세표준</th><th>세액(원)</th></tr>
<tr><td class="c">관&nbsp;세</td><td class="c">0% (FTA 협정관세 · AKFTA)</td>
    <td class="num">25,332,975</td><td class="num">{won(duty)}</td></tr>
<tr><td class="c">개별소비세</td><td class="c">-</td><td class="num">-</td><td class="num">0</td></tr>
<tr><td class="c">부가가치세</td><td class="c">10%</td><td class="num">25,332,975</td>
    <td class="num b">{won(2_533_297)}</td></tr>
<tr><td class="lbl" colspan="3">⑳ 총 세액 합계</td>
    <td class="num b" style="font-size:10pt">{won(2_533_297)}</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:26mm">납부기한</td><td class="mono" style="width:34mm">2026-03-31</td>
    <td class="lbl" style="width:26mm">신고수리일자</td><td class="mono b">2026-03-18</td></tr>
<tr><td class="lbl">담당자</td><td>인천세관 통관지원과 이심사</td>
    <td class="lbl">처리결과</td><td class="b" style="color:#1a6b3f">수리 (P/L 신고 · 서류제출 없음)</td></tr>
</table>
<div class="note">· 본 수입신고필증은 「관세법」에 따라 적법하게 신고·수리되었음을 증명합니다.<br>
· 수입 부가가치세는 세관장이 발행한 <b>수입세금계산서</b>로 매입세액 공제를 받습니다.<br>
· 원산지증명서 사후 검증 대비 관련 서류를 5년간 보관하여야 합니다.</div>
<div style="text-align:center;margin-top:2mm">{barcode('41099260123456M', 78)}</div>
<div class="footer-org" style="font-size:12pt">인 천 세 관 장 {stamp('세관장',44)}</div>
"""
    docs.append(dict(no=46, slug="46_수입신고필증", size="A4", title="수입신고필증",
                     html=html_doc("수입신고필증", body, extra_css=CSS)))

    # 47. 선하증권 (B/L)
    body = f"""
<div style="display:flex;justify-content:space-between" class="small">
  <span class="b">OCEAN STAR LINE CO., LTD.</span>
  <span>B/L No. <b class="mono">OSLSGINC26030088</b></span></div>
<h1 class="title sm" style="margin-top:1mm">BILL OF LADING</h1>
<div class="subtitle">선 하 증 권 &nbsp;|&nbsp; ORIGINAL (3/3)</div>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:28mm">Shipper</td><td colspan="3" class="en">{SELLER}</td></tr>
<tr><td class="lbl">Consignee</td><td colspan="3" class="en b">
    TO THE ORDER OF DAEHAN BANK, SEOUL</td></tr>
<tr><td class="lbl">Notify Party</td><td colspan="3" class="en">
    {SUPPLIER['name']} (HANBIT TECHNOLOGY CO., LTD.)<br>
    8F, 123 TEHERAN-RO, GANGNAM-GU, SEOUL, KOREA / TEL +82-2-555-1234</td></tr>
<tr><td class="lbl">Pre-carriage by</td><td style="width:44mm">-</td>
    <td class="lbl" style="width:30mm">Place of Receipt</td><td>SINGAPORE CY</td></tr>
<tr><td class="lbl">Ocean Vessel / Voy.</td><td>OCEAN STAR V.0142E</td>
    <td class="lbl">Port of Loading</td><td>SINGAPORE</td></tr>
<tr><td class="lbl">Port of Discharge</td><td>INCHEON, KOREA</td>
    <td class="lbl">Place of Delivery</td><td>INCHEON CY</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><th style="width:30mm">Marks &amp; Numbers</th><th style="width:22mm">No. of Pkgs</th>
    <th>Description of Goods</th><th style="width:24mm">Gross Weight</th>
    <th style="width:22mm">Measurement</th></tr>
<tr><td class="c en" style="height:24mm">HANBIT<br>INCHEON<br>C/NO. 1-12<br>MADE IN SINGAPORE</td>
    <td class="c">12 CARTONS<br>(1 x 20'DV)</td>
    <td class="en">NOTEBOOK COMPUTERS AND ACCESSORIES<br>
      CONTAINER NO. : OSLU 123456-7 / SEAL NO. SG0088412<br>
      "SHIPPER'S LOAD, COUNT AND SEAL"<br>
      FREIGHT PREPAID</td>
    <td class="c">318.5 KGS</td><td class="c">1.850 CBM</td></tr>
<tr><td class="lbl">TOTAL</td><td class="c b">TWELVE (12) CARTONS ONLY</td>
    <td colspan="3">&nbsp;</td></tr>
</table>
<table class="grid" style="margin-top:2mm">
<tr><td class="lbl" style="width:28mm">Freight &amp; Charges</td><td style="width:40mm">OCEAN FREIGHT : PREPAID</td>
    <td class="lbl" style="width:26mm">No. of Original B/L</td><td class="c b">THREE (3)</td></tr>
<tr><td class="lbl">Place &amp; Date of Issue</td><td>SINGAPORE, 08 MARCH 2026</td>
    <td class="lbl">On Board Date</td><td class="mono">08 MARCH 2026</td></tr>
</table>
<div class="note en small">
RECEIVED by the Carrier the Goods specified above in apparent good order and condition unless
otherwise stated, to be transported to such place as agreed, authorised or permitted herein.
In witness whereof the number of original Bills of Lading stated above have been signed,
one of which being accomplished, the others to stand void.</div>
<div class="sign-area">As Carrier</div>
<div class="footer-org en" style="font-size:11pt">OCEAN STAR LINE CO., LTD. {stamp('CARRIER',40)}</div>
<div class="note">· 선하증권은 유가증권으로서 화물의 인도청구권을 표창하며, 수입통관 및 대금결제 증빙으로 사용됩니다.</div>
"""
    docs.append(dict(no=47, slug="47_선하증권_BL", size="A4", title="선하증권(B/L)",
                     html=html_doc("Bill of Lading", body, extra_css=CSS)))
    return docs
