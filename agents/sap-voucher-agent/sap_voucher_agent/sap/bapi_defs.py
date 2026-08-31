# -*- coding: utf-8 -*-
"""SAP 표준 BAPI 카탈로그.

이 에이전트가 호출하는 BAPI 의 메타데이터를 한곳에 모은다.
`doc_number_field` 는 성공 응답에서 생성 문서번호를 꺼낼 EXPORT 파라미터명이다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class BapiDef:
    name: str
    module: str                       # FI / MM / SD / TV / MD / BC
    tcode: str                        # 대응하는 대화형 트랜잭션
    description: str
    doc_number_field: Optional[str] = None   # EXPORT 파라미터명
    fiscal_year_field: Optional[str] = None
    return_param: str = "RETURN"      # BAPIRET2 테이블/구조 이름
    return_is_table: bool = True
    needs_commit: bool = True
    check_bapi: Optional[str] = None  # 사전 검증 BAPI
    testrun_param: Optional[str] = None  # 테스트 실행 플래그 파라미터명
    s4_note: str = ""                 # S/4HANA 관련 유의사항


#: 호출 대상 BAPI 정의
BAPIS: dict[str, BapiDef] = {
    # ---------------------------------------------------------------- FI 회계전표
    "BAPI_ACC_DOCUMENT_POST": BapiDef(
        name="BAPI_ACC_DOCUMENT_POST", module="FI", tcode="FB01 / FB60 / FB70",
        description="회계전표 전기(G/L·AP·AR·세금·원천징수 통합)",
        doc_number_field="OBJ_KEY", check_bapi="BAPI_ACC_DOCUMENT_CHECK",
        s4_note="OBJ_KEY 는 BELNR(10)+BUKRS(4)+GJAHR(4) 20자리로 반환된다."),
    "BAPI_ACC_DOCUMENT_CHECK": BapiDef(
        name="BAPI_ACC_DOCUMENT_CHECK", module="FI", tcode="-",
        description="회계전표 사전 검증(전기 없이 오류만 반환)",
        needs_commit=False),
    "BAPI_ACC_DOCUMENT_REV_POST": BapiDef(
        name="BAPI_ACC_DOCUMENT_REV_POST", module="FI", tcode="FB08",
        description="회계전표 역분개(취소)", doc_number_field="OBJ_KEY",
        check_bapi="BAPI_ACC_DOCUMENT_REV_CHECK"),
    "BAPI_ACC_DOCUMENT_REV_CHECK": BapiDef(
        name="BAPI_ACC_DOCUMENT_REV_CHECK", module="FI", tcode="-",
        description="역분개 사전 검증", needs_commit=False),

    # ---------------------------------------------------------------- MM 송장검증
    "BAPI_INCOMINGINVOICE_CREATE": BapiDef(
        name="BAPI_INCOMINGINVOICE_CREATE", module="MM", tcode="MIRO",
        description="구매송장 검증 전기(PO 참조 3-way matching)",
        doc_number_field="INVOICEDOCNUMBER", fiscal_year_field="FISCALYEAR",
        check_bapi="BAPI_INCOMINGINVOICE_PARK"),
    "BAPI_INCOMINGINVOICE_PARK": BapiDef(
        name="BAPI_INCOMINGINVOICE_PARK", module="MM", tcode="MIR7",
        description="구매송장 저장(파킹) - 승인 대기 상태로 보류",
        doc_number_field="INVOICEDOCNUMBER", fiscal_year_field="FISCALYEAR"),
    "BAPI_INCOMINGINVOICE_CANCEL": BapiDef(
        name="BAPI_INCOMINGINVOICE_CANCEL", module="MM", tcode="MR8M",
        description="구매송장 취소", doc_number_field="INVOICEDOCNUMBER_REVERSAL"),

    # ---------------------------------------------------------------- MM 구매
    "BAPI_PO_CREATE1": BapiDef(
        name="BAPI_PO_CREATE1", module="MM", tcode="ME21N",
        description="구매오더(PO) 생성", doc_number_field="EXPPURCHASEORDER",
        testrun_param="TESTRUN"),
    "BAPI_PR_CREATE": BapiDef(
        name="BAPI_PR_CREATE", module="MM", tcode="ME51N",
        description="구매요청(PR) 생성 - S/4HANA 권장 BAPI",
        doc_number_field="NUMBER",
        s4_note="구형 BAPI_REQUISITION_CREATE 는 S/4 에서 BAPI_PR_CREATE 로 대체됨.",
        testrun_param="TESTRUN"),
    "BAPI_CONTRACT_CREATE": BapiDef(
        name="BAPI_CONTRACT_CREATE", module="MM", tcode="ME31K",
        description="구매계약(Outline Agreement) 생성",
        doc_number_field="PURCHASINGDOCUMENT"),
    "BAPI_GOODSMVT_CREATE": BapiDef(
        name="BAPI_GOODSMVT_CREATE", module="MM", tcode="MIGO",
        description="자재문서 생성(입고 101 / 출고 201 등)",
        doc_number_field="MATERIALDOCUMENT", fiscal_year_field="MATDOCUMENTYEAR",
        testrun_param="TESTRUN"),
    "BAPI_ENTRYSHEET_CREATE": BapiDef(
        name="BAPI_ENTRYSHEET_CREATE", module="MM", tcode="ML81N",
        description="서비스 확인서(Service Entry Sheet) 생성 - 용역 검수",
        doc_number_field="ENTRYSHEET",
        testrun_param="TESTRUN"),
    "BAPI_INB_DELIVERY_CREATE": BapiDef(
        name="BAPI_INB_DELIVERY_CREATE", module="MM", tcode="VL31N",
        description="입고예정 납품(Inbound Delivery) 생성",
        doc_number_field="DELIVERY"),

    # ---------------------------------------------------------------- SD 영업
    "BAPI_QUOTATION_CREATEFROMDATA2": BapiDef(
        name="BAPI_QUOTATION_CREATEFROMDATA2", module="SD", tcode="VA21",
        description="견적(Quotation) 생성", doc_number_field="SALESDOCUMENT"),
    "BAPI_SALESORDER_CREATEFROMDAT2": BapiDef(
        name="BAPI_SALESORDER_CREATEFROMDAT2", module="SD", tcode="VA01",
        description="수주(Sales Order) 생성", doc_number_field="SALESDOCUMENT",
        testrun_param="TESTRUN"),
    "BAPI_OUTB_DELIVERY_CREATE_SLS": BapiDef(
        name="BAPI_OUTB_DELIVERY_CREATE_SLS", module="SD", tcode="VL01N",
        description="출고 납품(Outbound Delivery) 생성", doc_number_field="DELIVERY"),
    "BAPI_BILLINGDOC_CREATEMULTIPLE": BapiDef(
        name="BAPI_BILLINGDOC_CREATEMULTIPLE", module="SD", tcode="VF01",
        description="청구문서(Billing Document) 생성 - 매출 세금계산서 대응",
        doc_number_field="SUCCESS", return_param="RETURN",
        testrun_param="TESTRUN"),

    # ---------------------------------------------------------------- FI-TV 출장경비
    "BAPI_TRIP_CREATE_FROM_DATA": BapiDef(
        name="BAPI_TRIP_CREATE_FROM_DATA", module="TV", tcode="TRIP / PR05",
        description="출장(Trip) 및 경비 정산 생성", doc_number_field="TRIPNO",
        s4_note="전표 전기는 후속 정산 프로그램(RPRFIN00 / PRRW)에서 수행된다."),
    "BAPI_TRIP_CHANGE": BapiDef(
        name="BAPI_TRIP_CHANGE", module="TV", tcode="PR05",
        description="출장 경비 변경", doc_number_field="TRIPNO"),

    # ---------------------------------------------------------------- 마스터데이터
    "BAPI_BUPA_CREATE_FROM_DATA": BapiDef(
        name="BAPI_BUPA_CREATE_FROM_DATA", module="MD", tcode="BP",
        description="비즈니스파트너(BP) 생성 - S/4HANA 거래처 등록",
        doc_number_field="BUSINESSPARTNER"),
    "BAPI_BUPA_ROLE_ADD_2": BapiDef(
        name="BAPI_BUPA_ROLE_ADD_2", module="MD", tcode="BP",
        description="BP 역할 추가(FLVN00 공급업체 / FLCU00 고객)"),
    "BAPI_BUPA_BANKDETAIL_ADD": BapiDef(
        name="BAPI_BUPA_BANKDETAIL_ADD", module="MD", tcode="BP",
        description="BP 은행계좌 등록"),
    "BAPI_VENDOR_CREATE": BapiDef(
        name="BAPI_VENDOR_CREATE", module="MD", tcode="XK01",
        description="공급업체 마스터 생성(ECC 레거시)", doc_number_field="VENDORNO",
        s4_note="S/4HANA 에서는 BP 기반 BAPI_BUPA_* 사용을 권장한다."),

    # ---------------------------------------------------------------- 첨부/문서관리
    "ARCHIVOBJECT_CREATE_TABLE": BapiDef(
        name="ARCHIVOBJECT_CREATE_TABLE", module="BC", tcode="OAC0",
        description="원본 증빙 파일을 콘텐츠 저장소에 아카이빙",
        doc_number_field="ARC_DOC_ID", needs_commit=False),
    "BINARY_RELATION_CREATE_COMMIT": BapiDef(
        name="BINARY_RELATION_CREATE_COMMIT", module="BC", tcode="-",
        description="아카이브 객체를 SAP 문서(GOS 첨부)에 연결"),

    # ---------------------------------------------------------------- 트랜잭션 제어
    "BAPI_TRANSACTION_COMMIT": BapiDef(
        name="BAPI_TRANSACTION_COMMIT", module="BC", tcode="-",
        description="LUW 커밋(WAIT='X' 로 동기 커밋)", needs_commit=False),
    "BAPI_TRANSACTION_ROLLBACK": BapiDef(
        name="BAPI_TRANSACTION_ROLLBACK", module="BC", tcode="-",
        description="LUW 롤백", needs_commit=False),
}


#: 표준 BAPI 가 존재하지 않아 대안 경로를 쓰는 시나리오
NO_STANDARD_BAPI: dict[str, str] = {
    "bank_statement": (
        "전자 은행명세서 업로드용 표준 BAPI 는 없다. 정식 경로는 FINSTA/MT940 IDoc 또는 "
        "프로그램 RFEBKA00(FF_5) 이며, 본 에이전트는 명세 라인별 "
        "BAPI_ACC_DOCUMENT_POST 로 대체 전기한다."),
    "cash_journal": (
        "현금출납장(FBCJ)에는 공개 표준 BAPI 가 없다. FI 전표 "
        "BAPI_ACC_DOCUMENT_POST 로 현금계정 상대전기한다."),
    "payroll_posting": (
        "급여 전기는 PC00_M99_CIPE(급여결과 전기)가 정식 경로다. 본 에이전트는 "
        "명세서 집계액을 BAPI_ACC_DOCUMENT_POST 로 전기하며, 실제 운영에서는 "
        "PY 전기 문서와 대사(reconciliation)해야 한다."),
}


def get(name: str) -> BapiDef:
    if name not in BAPIS:
        raise KeyError(f"알 수 없는 BAPI: {name}")
    return BAPIS[name]
