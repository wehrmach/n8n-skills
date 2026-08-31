# -*- coding: utf-8 -*-
"""전기 실행기.

안전 규약
 1. 전기 BAPI 는 가능하면 CHECK BAPI 로 먼저 검증한다.
 2. dry_run 이면 CHECK 만 수행하고 절대 POST 하지 않는다.
 3. 한 스텝이라도 실패하면 즉시 BAPI_TRANSACTION_ROLLBACK 을 호출한다.
 4. 모든 스텝이 성공해야 BAPI_TRANSACTION_COMMIT(WAIT='X') 를 호출한다.
 5. 후속 스텝은 선행 스텝이 만든 문서번호를 참조로 이어받는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import BapiCall, BapiMessage, PostingPlan, PostingResult
from .sap.bapi_defs import BAPIS
from .sap.client import SapClient, TimedCall, interpret


@dataclass
class PostingOutcome:
    """전기 계획 실행 결과 전체."""

    plan: PostingPlan
    results: list[PostingResult] = field(default_factory=list)
    committed: bool = False
    rolled_back: bool = False
    dry_run: bool = False
    aborted_reason: str | None = None

    @property
    def success(self) -> bool:
        return (bool(self.results) and all(r.success for r in self.results)
                and not self.rolled_back and self.aborted_reason is None)

    @property
    def document_numbers(self) -> dict[str, str]:
        return {r.bapi: r.document_number for r in self.results if r.document_number}

    @property
    def failed_result(self) -> PostingResult | None:
        for r in self.results:
            if not r.success:
                return r
        return None

    def summary(self) -> str:
        head = f"[{self.plan.kr_name}] "
        if self.aborted_reason:
            # SAP 이 돌려준 실제 오류 메시지를 반드시 함께 보여준다.
            failed = self.failed_result
            detail = ""
            if failed is not None and failed.errors:
                detail = " :: " + "; ".join(
                    f"[{m.id}{m.number}] {m.message}" for m in failed.errors)
            tail = " (ROLLBACK 수행)" if self.rolled_back else ""
            return head + f"중단 - {self.aborted_reason}{detail}{tail}"
        if not self.results:
            return head + "실행된 호출 없음"
        body = " | ".join(r.summary() for r in self.results)
        tail = ""
        if self.dry_run:
            tail = " (DRY-RUN: 실제 전기하지 않음)"
        elif self.committed:
            tail = " (COMMIT 완료)"
        elif self.rolled_back:
            tail = " (ROLLBACK 수행)"
        return head + body + tail


def _link_previous(call: BapiCall, outcome: PostingOutcome) -> None:
    """선행 스텝의 문서번호를 후속 스텝 파라미터에 연결한다."""
    docs = outcome.document_numbers
    if call.bapi == "ARCHIVOBJECT_CREATE_TABLE":
        for bapi, no in docs.items():
            if bapi != "ARCHIVOBJECT_CREATE_TABLE":
                call.params["OBJECT_ID"] = no
                call.params["SAP_OBJECT"] = {
                    "BAPI_INCOMINGINVOICE_CREATE": "BUS2081",
                    "BAPI_PO_CREATE1": "BUS2012",
                    "BAPI_GOODSMVT_CREATE": "BUS2017",
                }.get(bapi, "BKPF")
                break
    elif call.bapi == "BAPI_BUPA_ROLE_ADD_2" or call.bapi == "BAPI_BUPA_BANKDETAIL_ADD":
        bp = docs.get("BAPI_BUPA_CREATE_FROM_DATA")
        if bp:
            call.params["BUSINESSPARTNER"] = bp
    elif call.bapi == "BAPI_ACC_DOCUMENT_POST" and "BAPI_INCOMINGINVOICE_CREATE" in docs:
        header = call.params.get("DOCUMENTHEADER")
        if isinstance(header, dict):
            header.setdefault("REF_DOC_NO", docs["BAPI_INCOMINGINVOICE_CREATE"][:16])


def _run_check(client: SapClient, call: BapiCall) -> PostingResult:
    """사전 검증을 수행한다. 3단계 폴백:

      1) 전용 CHECK BAPI (예: BAPI_ACC_DOCUMENT_CHECK)
      2) BAPI 자체의 TESTRUN 플래그 (예: BAPI_PO_CREATE1 TESTRUN='X')
      3) 둘 다 없으면 로컬 파라미터 검증만 수행했음을 명시한다
    """
    bd = BAPIS.get(call.bapi)

    if call.check_bapi and call.check_bapi != "BAPI_INCOMINGINVOICE_PARK":
        with TimedCall() as t:
            raw = client.call(call.check_bapi, **call.params)
        return interpret(call.check_bapi, raw, dry_run=True, elapsed_ms=t.elapsed_ms)

    if bd and bd.testrun_param:
        try:
            with TimedCall() as t:
                raw = client.call(call.bapi, **{**call.params, bd.testrun_param: "X"})
            res = interpret(call.bapi, raw, dry_run=True, elapsed_ms=t.elapsed_ms)
            res.document_number = None      # TESTRUN 은 문서를 만들지 않는다
            return res
        except Exception as exc:            # TESTRUN 미지원 릴리스 대비
            return PostingResult(
                bapi=call.bapi, success=True, dry_run=True,
                messages=[BapiMessage(
                    type="W", id="ZAGENT", number="003",
                    message=f"{call.bapi} TESTRUN 검증을 수행할 수 없습니다({exc}). "
                            "로컬 파라미터 검증만 완료했습니다.")])

    return PostingResult(
        bapi=call.bapi, success=True, dry_run=True,
        messages=[BapiMessage(
            type="I", id="ZAGENT", number="002",
            message=f"{call.bapi} 은(는) 표준 CHECK/TESTRUN 을 제공하지 않습니다. "
                    "로컬 파라미터 검증만 수행했습니다. 실제 전기 시 오류가 "
                    "발생할 수 있습니다.")])


def post(plan: PostingPlan, client: SapClient, *, dry_run: bool = True,
         auto_commit: bool = True, allow_unapproved: bool = False) -> PostingOutcome:
    """전기 계획을 실행한다."""
    out = PostingOutcome(plan=plan, dry_run=dry_run)

    if not plan.postable:
        out.aborted_reason = (
            "검증 오류로 전기할 수 없습니다: " + "; ".join(plan.validation_errors))
        return out
    if plan.requires_approval and not allow_unapproved and not dry_run:
        out.aborted_reason = (
            "사람 승인이 필요합니다: " + "; ".join(plan.approval_reasons)
            + " — 승인 후 allow_unapproved=True 로 재실행하십시오.")
        return out

    for call in plan.calls:
        _link_previous(call, out)

        check = _run_check(client, call)
        out.results.append(check)
        if not check.success:
            out.aborted_reason = f"{check.bapi} 사전 검증 실패"
            _rollback(client, out, dry_run)
            return out

        if dry_run:
            continue

        with TimedCall() as t:
            raw = client.call(call.bapi, **call.params)
        result = interpret(call.bapi, raw, elapsed_ms=t.elapsed_ms)
        out.results.append(result)
        if not result.success:
            out.aborted_reason = f"{call.bapi} 전기 실패"
            _rollback(client, out, dry_run)
            return out

    if dry_run:
        return out

    if auto_commit and any(c.commit for c in plan.calls):
        with TimedCall():
            client.call("BAPI_TRANSACTION_COMMIT", WAIT="X")
        out.committed = True
        for r in out.results:
            r.committed = True
    return out


def _rollback(client: SapClient, out: PostingOutcome, dry_run: bool) -> None:
    if dry_run:
        return
    try:
        client.call("BAPI_TRANSACTION_ROLLBACK")
        out.rolled_back = True
    except Exception as exc:                      # pragma: no cover
        out.aborted_reason = (out.aborted_reason or "") + f" (롤백 실패: {exc})"
