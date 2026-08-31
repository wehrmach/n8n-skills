# SAP Voucher Agent — 한국 증빙 → K-IFRS 판단 → SAP ERP 표준 BAPI 전기 AI 에이전트

한국에서 발생하는 지류(종이) 증빙 **50종**을 판독하고, **K-IFRS(한국채택국제회계기준)**
에 따라 회계처리를 판단한 뒤 **SAP ERP 표준 BAPI** 로 전표를 일으키는 AI 에이전트입니다.
`samples/korean-vouchers/` 의 샘플 PDF 50종과 1:1로 대응하며, 실제 SAP 없이도 Mock
시뮬레이터로 전 과정을 실행·검증할 수 있습니다.

```
증빙 PDF → 판독·분류 → 거래처 마스터 해석 → K-IFRS 회계판단 → 세무·전기 검증
        → BAPI 전기계획 → DRY-RUN → (사람 승인) → BAPI 전기 → COMMIT → 보고
```

이 에이전트의 설계 전제는 **세금계산서는 세법상 서류일 뿐 분개가 아니라는 것**입니다.
증빙 종류에서 곧바로 분개를 끌어내지 않고, 거래의 경제적 실질을 먼저 판단합니다.

## 빠른 시작

```bash
pip install -r requirements.txt

# 1) 증빙 유형별 BAPI 매핑 조회 (SAP·API 키 불필요)
python -m sap_voucher_agent routes
python -m sap_voucher_agent routes tax_invoice_in

# 2) 50종 전체를 Mock SAP 에 전기 (SAP·API 키 불필요)
python -m sap_voucher_agent demo --live

# 2-1) K-IFRS 회계판단 조회
python -m sap_voucher_agent kifrs                      # 적용 기준서 목록
python -m sap_voucher_agent --period-end 2026-03-31 kifrs all   # 50종 인식 결론
python -m sap_voucher_agent kifrs tax_invoice_out      # 개별 증빙 판단 근거
python examples/kifrs_walkthrough.py                   # 세법 형식 vs 회계 실질 시연

# 3) 실제 증빙 PDF 판독 + 전기계획 (ANTHROPIC_API_KEY 필요)
python -m sap_voucher_agent plan ../../samples/korean-vouchers/pdf/01_세금계산서_공급받는자보관용.pdf

# 4) 에이전트 자율 실행
python -m sap_voucher_agent agent "samples/korean-vouchers/pdf 의 세금계산서를 모두 전기해줘"
```

`--sap mock|rfc|auto` 로 연결 방식을 고릅니다. 기본 `auto` 는 SAP 접속 환경변수가
없으면 Mock 으로 떨어지므로, 실수로 운영 시스템에 전기될 일이 없습니다.

## 무엇이 들어 있나

| 파일 | 역할 |
|---|---|
| `doc_types.py` | 증빙 50종 유형 정의 (샘플 PDF 번호와 매핑) |
| `kifrs.py` | **핵심** — K-IFRS 회계판단 엔진 (인식 시점·자본화·기간귀속·측정) |
| `mapping.py` | **핵심** — 유형별 BAPI 전기 경로 레지스트리 (분기·대안 경로 포함) |
| `builders.py` | 38개 BAPI 파라미터 빌더 (실제 RFC 구조 생성) |
| `sap/bapi_defs.py` | 표준 BAPI 27종 카탈로그 (모듈·T-code·CHECK/TESTRUN·S/4 유의사항) |
| `accounts.py` | 계정과목·세금코드 결정 엔진 (JSON 오버라이드 가능) |
| `validation.py` | 한국 세무 규칙 + SAP 전기 요건 검증 |
| `planner.py` / `poster.py` | 전기계획 수립 / 실행 (CHECK → POST → COMMIT·ROLLBACK) |
| `extraction.py` | Claude 구조화 출력으로 PDF 판독 |
| `agent.py` | Claude 툴러너 기반 에이전트 (툴 10종) |
| `master_data.py` | 사업자번호 → SAP 거래처 코드 해석 (RFC_READ_TABLE / 로컬) |
| `sap/mock.py` | SAP 시뮬레이터 (차대검증·중복차단·오류주입) |
| `fixtures.py` | 50종 대표 샘플 데이터 (LLM 없이 회귀 테스트) |

## 증빙 → BAPI 매핑 (요약)

| 증빙 그룹 | 주요 BAPI | 대응 T-code |
|---|---|---|
| 세금계산서(매입, PO 있음) | `BAPI_INCOMINGINVOICE_CREATE` | MIRO |
| 세금계산서(매입, PO 없음) | `BAPI_ACC_DOCUMENT_POST` | FB60 |
| 세금계산서(매출) | `BAPI_ACC_DOCUMENT_POST` / `BAPI_BILLINGDOC_CREATEMULTIPLE` | FB70 / VF01 |
| 수정세금계산서 | `BAPI_ACC_DOCUMENT_REV_POST` | FB08 |
| 카드전표·현금영수증·소액영수증 | `BAPI_ACC_DOCUMENT_POST` | FB50 |
| 발주서 / 구매품의서 / 용역계약서 | `BAPI_PO_CREATE1` / `BAPI_PR_CREATE` / `BAPI_CONTRACT_CREATE` | ME21N / ME51N / ME31K |
| 거래명세서·인수증 (자재) | `BAPI_GOODSMVT_CREATE` | MIGO |
| 검수확인서 (용역) | `BAPI_ENTRYSHEET_CREATE` | ML81N |
| 견적서 | `BAPI_QUOTATION_CREATEFROMDATA2` | VA21 |
| 출장여비·여비영수증 | `BAPI_TRIP_CREATE_FROM_DATA` | PR05 |
| 사업소득 원천징수 3.3% | `BAPI_ACC_DOCUMENT_POST` + `ACCOUNTWT` | FB60 |
| 수입신고필증·Commercial Invoice | `BAPI_INCOMINGINVOICE_CREATE` | MIRO |
| 사업자등록증·통장 사본 | `BAPI_BUPA_CREATE_FROM_DATA` 외 | BP |
| 원본 증빙 첨부 | `ARCHIVOBJECT_CREATE_TABLE` | OAC0 |

전체 50종 매핑은 `python -m sap_voucher_agent routes` 로 확인합니다.

### 표준 BAPI 가 없는 경우

거짓 매핑 대신 대안 경로를 명시하고 경고를 남깁니다.

- **전자 은행명세서** — 정식 경로는 MT940/FINSTA IDoc 또는 `RFEBKA00`(FF_5).
  본 에이전트는 라인별 FI 전표로 대체하고 미매칭분은 은행미결계정에 남깁니다.
- **현금출납장(FBCJ)** — 공개 BAPI 없음. FI 전표로 현금계정 상대전기합니다.
- **급여 전기** — 정식 경로는 `PC00_M99_CIPE`. 집계액을 FI 전표로 전기하되
  PY 전기문서와 대사가 필요함을 경고합니다.

## K-IFRS 회계판단

세법상 증빙 형식과 회계상 거래 실질이 갈리는 지점을 판단합니다. 같은 증빙이라도
결론이 달라집니다.

| 증빙 | 세법상 시각 | K-IFRS 인식 |
|---|---|---|
| 입금표·이체확인증 | 현금 수수 증명 | **채권·채무 소거** (손익 미발생) |
| 용역계약서·발주서 | 거래 성립 증거 | **회계 인식 대상 아님** (미이행계약) |
| 연간 보험료 세금계산서 | 작성일에 전액 매입 | **선급비용 이연** + 월별 상각 스케줄 |
| ERP 개발용역 세금계산서 | 전액 손금 | **1038 개발단계 요건 판단 필요** (기본: 비용) |
| 선청구 청구서 | 공급시기 도래 | **계약부채(선수금)** — 수행의무 미이행 |
| 수입세금계산서 | 매입세액 공제 | **환급 가능 자산** — 취득원가에서 제외 |
| 부가세 납부영수증 | 세금 납부 | **예수금 정산** — 비용이 아님 |
| 수정세금계산서 | 당초분 취소 | **기인식분 정정** — 오류면 소급재작성 검토 |
| 검수확인서 | 검수 사실 확인 | **통제 이전 시점** — 인식일을 결정 |

적용 기준서: 개념체계(발생주의·실질우선·중요성), 1001 상계금지, 1002 재고자산,
1008 오류수정, 1012 법인세, 1016 유형자산, 1019 종업원급여, 1021 환율변동효과,
1037 충당부채, 1038 무형자산, 1109 금융상품, 1115 수익, 1116 리스.

### 판단은 사람에게 넘긴다

회사 정책과 사실관계에 달린 쟁점은 에이전트가 결정하지 않고 **차단 판단**으로
올립니다. 금액은 어떤 경우에도 자동으로 바꾸지 않습니다.

- 개발비 자본화 6요건 충족 여부 (1038 문단 57)
- 리스 인식 여부 — 단기·소액 면제 대상이 아닌 경우 (1116)
- 수행의무 이행일 — 세금계산서 작성일로 대체 금지 (1115)
- 외화 적용환율 누락 (1021)
- 장기어음 현재가치 할인 (1109)
- 취득세·등록세의 취득원가 가산 대상 자산 (1016)
- 수정세금계산서의 정정 사유 — 당기 반영 vs 소급재작성 (1008)

`set_accounting_policy` 툴 또는 CLI 옵션(`--capitalize-development`,
`--capitalization-threshold`, `--period-end`)으로 회사 정책을 지정하면 판단이
해소되고 계정이 재분류됩니다.

### 기간귀속(cut-off)

용역 제공기간이 보고기간을 넘으면 발생주의에 따라 선급비용으로 이연합니다.
명세 라인을 '당기 경과분'과 '선급비용 이연분' 두 줄로 나누므로 총액과 전표
차대는 그대로 유지되고, 부가세는 세금계산서 작성일 과세기간에 전액 남습니다
(회계상 이연과 세법상 공제시기는 별개).

```
차변 821100 보험료          1,000,000   (당기 경과분 1개월)
차변 133100 선급비용       11,000,000   (2026-03-01~2027-02-28)
차변 135100 부가세대급금    1,200,000
대변 공급업체              13,200,000
→ 기간배분 스케줄 11건 생성 (SAP 발생/이연 엔진 ACACTREE01 또는 반복전표 FBD1)
```

## 안전장치

전기는 되돌리기 어려운 작업이므로 다음을 강제합니다.

1. **DRY-RUN 선행** — 전용 CHECK BAPI(`BAPI_ACC_DOCUMENT_CHECK`) → BAPI 자체
   `TESTRUN` 플래그 → 로컬 검증 순으로 폴백하며, 검증 수단이 없으면 그 사실을
   명시합니다. 에이전트는 DRY-RUN 없이 `execute_posting` 을 호출할 수 없습니다.
2. **멱등성** — 증빙 고유번호(승인번호 등)를 참조번호(XBLNR, 16자)로 정규화해
   중복 전기를 차단합니다. 16자 초과 시 앞부분 + MD5 해시로 유일성을 보존하고,
   한 증빙이 문서를 둘 이상 만드는 계획(예: 수입신고필증 = 관세 송장 + 부가세
   전표)에서는 스텝별로 참조번호를 분기해 자기 자신과 충돌하지 않게 합니다.
3. **2단계 실행과 LUW 위생** — 모든 스텝을 먼저 검증한 뒤 실제 전기에 들어갑니다.
   `TESTRUN` 은 실제 처리 로직을 태워 잠금·버퍼를 남기므로, 검증 단계가 끝나면
   전기 전에 반드시 롤백으로 LUW 를 정리합니다(정리용 롤백은 실패가 아닙니다).
4. **원자성** — 한 스텝이라도 실패하면 즉시 `BAPI_TRANSACTION_ROLLBACK`,
   전 스텝 성공 시에만 `BAPI_TRANSACTION_COMMIT(WAIT='X')`. **커밋 응답도
   검증**하므로 채번만 되고 저장되지 않은 문서를 성공으로 보고하지 않습니다.
5. **승인 게이트** — 수정세금계산서·약속어음·급여·용역계약·거래처 마스터 변경은
   금액과 무관하게 사람 승인을 요구하고, 금액 한도 초과분도 승인 대상입니다.
6. **차단 검증** — 차대 불일치, 마스터 미매핑, 미래 전기일자, 합계 불일치는
   BAPI 호출 자체를 하지 않습니다.
7. **오류 가시성** — 실패 시 SAP 이 반환한 메시지 ID·번호·본문을 그대로 노출합니다.

## 한국 세무 규칙 검증

| 코드 | 내용 |
|---|---|
| EVD001 | 3만원 초과 간이영수증 → 증빙불비가산세 2% 경고 |
| EVD002 | 경조사비 20만원 초과 → 전액 손금불산입 경고 |
| EVD003 | 3만원 초과 접대성 지출 → 매입세액 불공제·상대방 기록 필요 |
| VAT001 | 면세 증빙에 세액 기재 → 차단 |
| VAT002 | 부가세액이 공급가액의 10%와 불일치 → 경고 |
| PTY001 | 사업자등록번호 체크디지트 불일치 → OCR 오독 의심 |
| AMT002 | 합계 ≠ 공급가액 + 세액 → 차단 |
| MST001 | 매입 전기인데 SAP 공급업체 미매핑 → 차단 |
| IFRS001 | K-IFRS 인식 대상이 아닌데 회계전표가 계획됨 → 경고 |
| IFRS002 | 선급비용 이연 발생 → 매월 상각 전기 필요 경고 |

계정·세금코드는 접대비(불공제 `V2`), 여객운송(면세 `V0`), 일반 매입(`V1`) 등
증빙 성격에 따라 자동 결정하며 `AccountRules.from_json()` 으로 회사 계정체계에
맞춰 교체할 수 있습니다.

## 실제 SAP 연결

```bash
export SAP_ASHOST=sapapp01 SAP_SYSNR=00 SAP_CLIENT=100 \
       SAP_USER=RFC_AGENT SAP_PASSWD='***' SAP_LANG=KO
python -m sap_voucher_agent post 증빙.pdf --sap rfc --live --approve
```

SAP NetWeaver RFC SDK 설치 후 `pip install pyrfc` 가 필요합니다.
운영 반영 전 반드시 확인할 것:

- 세금코드(`V0/V1/V2/A0/A1`)와 G/L 계정번호는 **예시값**입니다. 회사 코드체계로
  교체하십시오(`accounts.py` 또는 JSON 오버라이드).
- 자본화 기준금액·이연 최소금액·리스 면제 기준은 회사의 K-IFRS 회계정책에 맞춰
  `PostingContext` 에서 설정해야 합니다. 기본값은 예시입니다.
- 이 도구는 회계처리를 **제안하고 근거를 남기는** 것이지 회계사의 판단을 대체하지
  않습니다. 자본화·리스·수익인식 결론은 반드시 사람이 확정해야 합니다.
- RFC 사용자에게는 필요한 BAPI 권한만 부여하고, 전기 권한은 회사코드·전표유형
  단위로 제한하십시오.
- S/4HANA 에서는 거래처가 BP 로 통합되어 `BAPI_VENDOR_CREATE` 대신
  `BAPI_BUPA_*` 를 사용해야 합니다(카탈로그에 표시되어 있습니다).

## 테스트

```bash
python -m pytest tests -q          # 256 tests
python examples/run_all_types.py   # 50종 Mock 전기 커버리지 표
```

`test_coverage.py` 는 50종 각각에 대해 경로·픽스처·빌더 존재, 계획 수립,
DRY-RUN, 실제 전기, 멱등키 길이, **FI 전표 차대 균형**을 검사합니다.
`test_kifrs.py` 는 발생주의·미이행계약·기간귀속·자본화·수익인식·리스·외화·
상계금지 규칙과, 50종 전부가 근거 있는 K-IFRS 인식 결론을 갖는지 검사합니다.

## 아키텍처 노트

- 모델은 **Claude Opus 5**(`claude-opus-5`), 적응형 사고(`thinking: adaptive`)를
  사용합니다. 판독은 구조화 출력(`messages.parse`), 에이전트 루프는
  툴러너(`client.beta.messages.tool_runner`)를 씁니다.
- 시스템 프롬프트는 `cache_control` 로 캐시해 반복 판독 비용을 줄입니다.
- 에이전트 툴은 증빙 원문 대신 **식별자와 짧은 요약**만 주고받습니다.
  대용량 JSON 이 컨텍스트를 잠식하지 않도록 세션 상태에 보관합니다.
- BAPI 파라미터는 전기 전 `inspect_bapi_params` 로 사람이 직접 확인할 수 있습니다.

---

Conceived by Romuald Członkowski - [www.aiadvisors.pl/en](https://www.aiadvisors.pl/en)
