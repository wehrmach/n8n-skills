# -*- coding: utf-8 -*-
"""SAP 시뮬레이션 클라이언트.

실제 SAP 없이 전체 파이프라인을 실행·테스트하기 위한 구현체다.
 * 문서번호를 채번하고 호출 이력을 기록한다
 * 참조번호(REF_DOC_NO) 중복 시 SAP 의 중복송장 경고를 재현한다
 * 회계전표는 차대 균형을 검사해 불균형이면 오류 메시지를 반환한다
 * `fail_on` 으로 특정 BAPI 의 실패를 강제해 오류 처리 경로를 테스트할 수 있다
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from .bapi_defs import BAPIS


class MockClient:
    """인메모리 SAP 시뮬레이터."""

    def __init__(self, *, strict_balance: bool = True,
                 fail_on: set[str] | None = None) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.documents: dict[str, dict[str, Any]] = {}
        self.seen_refs: dict[str, str] = {}        # REF_DOC_NO -> 문서번호
        self.committed = 0
        self.rolled_back = 0
        self.strict_balance = strict_balance
        self.fail_on = fail_on or set()
        self._counters: dict[str, int] = {}

    # ------------------------------------------------------------ 내부 유틸

    def _next(self, prefix: str, width: int = 10) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}{self._counters[prefix]:0{width - len(prefix)}d}"

    @staticmethod
    def _ok(msg: str) -> dict[str, Any]:
        return {"TYPE": "S", "ID": "RW", "NUMBER": "605", "MESSAGE": msg, "FIELD": ""}

    @staticmethod
    def _err(msg: str, mid: str = "ZMOCK", num: str = "001",
             field: str = "") -> dict[str, Any]:
        return {"TYPE": "E", "ID": mid, "NUMBER": num, "MESSAGE": msg, "FIELD": field}

    @staticmethod
    def _warn(msg: str) -> dict[str, Any]:
        return {"TYPE": "W", "ID": "M8", "NUMBER": "108", "MESSAGE": msg, "FIELD": ""}

    def _check_ref(self, ref: str, doc_no: str) -> list[dict[str, Any]]:
        """참조번호 중복 검사 - SAP 의 중복 송장 검사(M8 108) 재현."""
        if not ref:
            return []
        if ref in self.seen_refs:
            return [self._err(
                f"참조번호 {ref} 로 이미 전기된 문서가 있습니다"
                f"(문서번호 {self.seen_refs[ref]}). 중복 전기를 차단했습니다.",
                mid="M8", num="108", field="REF_DOC_NO")]
        self.seen_refs[ref] = doc_no
        return []

    # ------------------------------------------------------------ RFC 호출

    def call(self, function_name: str, **params: Any) -> dict[str, Any]:
        self.calls.append((function_name, params))
        testrun = str(params.pop("TESTRUN", "")).upper() == "X"

        if function_name in self.fail_on:
            return {"RETURN": [self._err(
                f"{function_name} 강제 실패(테스트 시나리오)")]}

        handler = getattr(self, f"_h_{function_name.lower()}", None)
        raw = handler(params) if handler is not None else self._h_generic(
            function_name, params)
        if testrun:
            bapi = BAPIS.get(function_name)
            if bapi and bapi.doc_number_field:
                raw.pop(bapi.doc_number_field, None)
            rows = raw.get("RETURN") or []
            if isinstance(rows, list) and not any(
                    r.get("TYPE") in ("E", "A") for r in rows):
                raw["RETURN"] = [self._ok(f"{function_name} TESTRUN 검증 통과")]
        return raw

    def close(self) -> None:      # pragma: no cover - 인터페이스 호환용
        pass

    # ------------------------------------------------------------ 핸들러

    def _h_bapi_transaction_commit(self, params: dict[str, Any]) -> dict[str, Any]:
        self.committed += 1
        return {"RETURN": {"TYPE": "S", "ID": "", "NUMBER": "",
                           "MESSAGE": "커밋 완료", "FIELD": ""}}

    def _h_bapi_transaction_rollback(self, params: dict[str, Any]) -> dict[str, Any]:
        self.rolled_back += 1
        return {"RETURN": {"TYPE": "S", "ID": "", "NUMBER": "",
                           "MESSAGE": "롤백 완료", "FIELD": ""}}

    # --- FI 회계전표 -------------------------------------------------------

    def _validate_acc(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = []
        header = params.get("DOCUMENTHEADER") or {}
        for req in ("COMP_CODE", "DOC_DATE", "PSTNG_DATE", "DOC_TYPE"):
            if not header.get(req):
                msgs.append(self._err(f"전표 헤더 필수항목 {req} 누락", mid="RW",
                                      num="609", field=req))
        amounts = params.get("CURRENCYAMOUNT") or []
        if not amounts:
            msgs.append(self._err("CURRENCYAMOUNT 라인이 없습니다", mid="RW", num="610"))
        if self.strict_balance and amounts:
            total = sum(Decimal(str(a.get("AMT_DOCCUR", "0")))
                        for a in amounts if a.get("CURR_TYPE", "00") == "00")
            if abs(total) >= Decimal("0.01"):
                msgs.append(self._err(
                    f"차변과 대변이 일치하지 않습니다(차액 {total}). 전기할 수 없습니다.",
                    mid="F5", num="702"))
        for row in (params.get("ACCOUNTPAYABLE") or []):
            if str(row.get("VENDOR_NO", "")).strip("0") in ("", "UNMAPPED"):
                msgs.append(self._err(
                    "공급업체 코드가 매핑되지 않았습니다(VENDOR_NO). "
                    "거래처 마스터를 먼저 확인하십시오.", mid="F5", num="151",
                    field="VENDOR_NO"))
        for row in (params.get("ACCOUNTRECEIVABLE") or []):
            if str(row.get("CUSTOMER", "")).strip("0") in ("", "UNMAPPED"):
                msgs.append(self._err(
                    "고객 코드가 매핑되지 않았습니다(CUSTOMER).", mid="F5", num="152",
                    field="CUSTOMER"))
        return msgs

    def _h_bapi_acc_document_check(self, params: dict[str, Any]) -> dict[str, Any]:
        msgs = self._validate_acc(params)
        if not msgs:
            msgs = [self._ok("전표 검증 완료 - 오류 없음")]
        return {"RETURN": msgs}

    def _h_bapi_acc_document_post(self, params: dict[str, Any]) -> dict[str, Any]:
        msgs = self._validate_acc(params)
        if any(m["TYPE"] in ("E", "A") for m in msgs):
            return {"RETURN": msgs}
        header = params.get("DOCUMENTHEADER") or {}
        belnr = self._next("", 10)
        obj_key = f"{belnr}{header.get('COMP_CODE','')}{header.get('FISC_YEAR','')}"
        dup = self._check_ref(header.get("REF_DOC_NO", ""), belnr)
        if dup:
            return {"RETURN": dup}
        self.documents[obj_key] = params
        return {"OBJ_KEY": obj_key, "OBJ_TYPE": "BKPFF", "OBJ_SYS": "MOCKCLNT100",
                "RETURN": [self._ok(f"전표 {belnr} 이(가) 회사코드 "
                                    f"{header.get('COMP_CODE')} 에 전기되었습니다")]}

    def _h_bapi_acc_document_rev_post(self, params: dict[str, Any]) -> dict[str, Any]:
        rev = params.get("REVERSAL") or {}
        if not rev.get("OBJ_KEY"):
            return {"RETURN": [self._err(
                "역분개할 원 전표번호(OBJ_KEY)가 없습니다.", mid="F5", num="201",
                field="OBJ_KEY")]}
        belnr = self._next("", 10)
        obj = f"{belnr}{rev.get('COMP_CODE','')}{rev.get('PSTNG_DATE','')[:4]}"
        return {"OBJ_KEY": obj,
                "RETURN": [self._ok(f"전표 {rev['OBJ_KEY']} 이(가) "
                                    f"{belnr} 로 역분개되었습니다")]}

    def _h_bapi_acc_document_rev_check(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"RETURN": [self._ok("역분개 검증 완료")]}

    # --- MM ----------------------------------------------------------------

    def _h_bapi_incominginvoice_create(self, params: dict[str, Any]) -> dict[str, Any]:
        header = params.get("HEADERDATA") or {}
        msgs: list[dict[str, Any]] = []
        if not header.get("COMP_CODE"):
            msgs.append(self._err("회사코드 누락", mid="M8", num="003", field="COMP_CODE"))
        gross = Decimal(str(header.get("GROSS_AMOUNT", "0")))
        items = params.get("ITEMDATA") or []
        taxes = params.get("TAXDATA") or []
        item_sum = sum(Decimal(str(i.get("ITEM_AMOUNT", "0"))) for i in items)
        tax_sum = sum(Decimal(str(t.get("TAX_AMOUNT", "0"))) for t in taxes)
        if items and abs(item_sum + tax_sum - gross) >= Decimal("0.01"):
            msgs.append(self._err(
                f"총액({gross})이 명세 합계({item_sum}+{tax_sum})와 일치하지 않습니다.",
                mid="M8", num="083", field="GROSS_AMOUNT"))
        for it in items:
            if not it.get("PO_NUMBER"):
                msgs.append(self._err(
                    f"품목 {it.get('INVOICE_DOC_ITEM')}: 구매오더번호가 없습니다. "
                    "PO 없는 송장은 FI 직접전표로 전기하십시오.",
                    mid="M8", num="147", field="PO_NUMBER"))
        if any(m["TYPE"] in ("E", "A") for m in msgs):
            return {"RETURN": msgs}
        docno = self._next("51", 10)
        dup = self._check_ref(header.get("REF_DOC_NO", ""), docno)
        if dup:
            return {"RETURN": dup}
        return {"INVOICEDOCNUMBER": docno,
                "FISCALYEAR": header.get("PSTNG_DATE", "")[:4],
                "RETURN": [self._ok(f"송장문서 {docno} 이(가) 생성되었습니다")]}

    def _h_bapi_incominginvoice_park(self, params: dict[str, Any]) -> dict[str, Any]:
        docno = self._next("51", 10)
        return {"INVOICEDOCNUMBER": docno,
                "FISCALYEAR": (params.get("HEADERDATA") or {}).get("PSTNG_DATE", "")[:4],
                "RETURN": [self._ok(f"송장 {docno} 이(가) 파킹되었습니다(승인 대기)")]}

    def _h_bapi_po_create1(self, params: dict[str, Any]) -> dict[str, Any]:
        header = params.get("POHEADER") or {}
        msgs = []
        if str(header.get("VENDOR", "")).strip("0") in ("", "UNMAPPED"):
            msgs.append(self._err("공급업체가 매핑되지 않았습니다", mid="06", num="017",
                                  field="VENDOR"))
        if not header.get("PURCH_ORG"):
            msgs.append(self._err("구매조직 누락", mid="06", num="018", field="PURCH_ORG"))
        if msgs:
            return {"RETURN": msgs}
        po = self._next("45", 10)
        return {"EXPPURCHASEORDER": po,
                "RETURN": [self._ok(f"표준 구매오더 {po} 이(가) 생성되었습니다")]}

    def _h_bapi_pr_create(self, params: dict[str, Any]) -> dict[str, Any]:
        pr = self._next("10", 10)
        return {"NUMBER": pr,
                "RETURN": [self._ok(f"구매요청 {pr} 이(가) 생성되었습니다")]}

    def _h_bapi_contract_create(self, params: dict[str, Any]) -> dict[str, Any]:
        c = self._next("46", 10)
        return {"PURCHASINGDOCUMENT": c,
                "RETURN": [self._ok(f"구매계약 {c} 이(가) 생성되었습니다")]}

    def _h_bapi_goodsmvt_create(self, params: dict[str, Any]) -> dict[str, Any]:
        items = params.get("GOODSMVT_ITEM") or []
        if not items:
            return {"RETURN": [self._err("이동 품목이 없습니다", mid="M7", num="018")]}
        msgs = []
        for it in items:
            if not it.get("PO_NUMBER"):
                msgs.append(self._err("구매오더 참조 없이 101 입고는 불가합니다",
                                      mid="M7", num="093", field="PO_NUMBER"))
            if not it.get("PLANT"):
                msgs.append(self._err("플랜트 누락", mid="M7", num="021", field="PLANT"))
        if msgs:
            return {"RETURN": msgs}
        mblnr = self._next("50", 10)
        return {"MATERIALDOCUMENT": mblnr,
                "MATDOCUMENTYEAR": (params.get("GOODSMVT_HEADER") or {})
                .get("PSTNG_DATE", "")[:4],
                "RETURN": [self._ok(f"자재문서 {mblnr} 이(가) 전기되었습니다")]}

    def _h_bapi_entrysheet_create(self, params: dict[str, Any]) -> dict[str, Any]:
        h = params.get("ENTRYSHEETHEADER") or {}
        if not h.get("PO_NUMBER"):
            return {"RETURN": [self._err(
                "서비스 확인서는 구매오더 참조가 필요합니다", mid="SE", num="185",
                field="PO_NUMBER")]}
        es = self._next("10", 10)
        return {"ENTRYSHEET": es,
                "RETURN": [self._ok(f"서비스 확인서 {es} 이(가) 생성·승인되었습니다")]}

    def _h_bapi_inb_delivery_create(self, params: dict[str, Any]) -> dict[str, Any]:
        d = self._next("18", 10)
        return {"DELIVERY": d,
                "RETURN": [self._ok(f"입고예정 납품 {d} 이(가) 생성되었습니다")]}

    # --- SD ----------------------------------------------------------------

    def _h_bapi_quotation_createfromdata2(self, params: dict[str, Any]) -> dict[str, Any]:
        q = self._next("20", 10)
        return {"SALESDOCUMENT": q,
                "RETURN": [self._ok(f"견적 {q} 이(가) 생성되었습니다")]}

    def _h_bapi_billingdoc_createmultiple(self, params: dict[str, Any]) -> dict[str, Any]:
        rows = params.get("BILLINGDATAIN") or []
        if not rows or not rows[0].get("REF_DOC"):
            return {"RETURN": [self._err(
                "청구할 참조문서(납품/수주)가 없습니다", mid="VF", num="047",
                field="REF_DOC")]}
        b = self._next("90", 10)
        return {"SUCCESS": [{"BILL_DOC": b}],
                "RETURN": [self._ok(f"청구문서 {b} 이(가) 생성되었습니다")]}

    # --- FI-TV / 마스터 -----------------------------------------------------

    def _h_bapi_trip_create_from_data(self, params: dict[str, Any]) -> dict[str, Any]:
        if not params.get("EMPLOYEENUMBER"):
            return {"RETURN": [self._err(
                "사원번호(PERNR)가 없습니다. 인사마스터 매핑이 필요합니다.",
                mid="PTRA", num="001", field="EMPLOYEENUMBER")]}
        t = self._next("00", 10)
        return {"TRIPNO": t,
                "RETURN": [self._ok(f"출장 {t} 이(가) 등록되었습니다")]}

    def _h_bapi_bupa_create_from_data(self, params: dict[str, Any]) -> dict[str, Any]:
        bp = self._next("BP", 10)
        return {"BUSINESSPARTNER": bp,
                "RETURN": [self._ok(f"비즈니스파트너 {bp} 이(가) 생성되었습니다")]}

    def _h_archivobject_create_table(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"ARCHIV_ID": params.get("ARCHIV_ID", "Z1"),
                "ARC_DOC_ID": self._next("AR", 16),
                "RETURN": [self._ok("원본 증빙이 아카이빙되었습니다")]}

    # --- 폴백 ---------------------------------------------------------------

    def _h_generic(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        bapi = BAPIS.get(name)
        out: dict[str, Any] = {"RETURN": [self._ok(f"{name} 처리 완료(시뮬레이션)")]}
        if bapi and bapi.doc_number_field:
            out[bapi.doc_number_field] = self._next("99", 10)
        return out
