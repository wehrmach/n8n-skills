# -*- coding: utf-8 -*-
"""SAP 연결 추상화.

`SapClient` 프로토콜을 만족하는 구현체는 두 가지다.
 * `rfc.RfcClient`  - pyrfc 를 통한 실제 SAP 시스템 연결
 * `mock.MockClient` - 로컬 시뮬레이션(개발/테스트/데모)
"""
from __future__ import annotations

import time
from typing import Any, Protocol, runtime_checkable

from ..models import BapiMessage, PostingResult
from .bapi_defs import BAPIS, BapiDef


@runtime_checkable
class SapClient(Protocol):
    """SAP RFC 호출 인터페이스."""

    def call(self, function_name: str, **params: Any) -> dict[str, Any]:
        """RFC 함수를 호출하고 EXPORT/TABLES 를 dict 로 반환한다."""
        ...

    def close(self) -> None:
        ...


# --------------------------------------------------------------------------- 결과 해석

def parse_messages(raw: dict[str, Any], return_param: str = "RETURN") -> list[BapiMessage]:
    """BAPIRET2 테이블/구조를 BapiMessage 리스트로 변환한다."""
    ret = raw.get(return_param)
    if ret is None:
        return []
    rows = ret if isinstance(ret, list) else [ret]
    out: list[BapiMessage] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        t = (r.get("TYPE") or "").strip().upper()
        if t not in ("S", "I", "W", "E", "A", ""):
            t = ""
        out.append(BapiMessage(
            type=t, id=(r.get("ID") or "").strip(),
            number=str(r.get("NUMBER") or "").strip(),
            message=(r.get("MESSAGE") or r.get("MESSAGE_V1") or "").strip(),
            field=(r.get("FIELD") or "").strip(),
        ))
    return [m for m in out if m.message or m.type]


def _extract_doc_number(raw: dict[str, Any], bapi: BapiDef) -> str | None:
    if not bapi.doc_number_field:
        return None
    val = raw.get(bapi.doc_number_field)
    if isinstance(val, list):                     # BILLINGDOC 등 테이블형 반환
        if not val:
            return None
        first = val[0]
        if isinstance(first, dict):
            for key in ("BILL_DOC", "DOCUMENT", "SALESDOCUMENT", "BILLINGDOCUMENT"):
                if first.get(key):
                    return str(first[key]).strip()
            return None
        val = first
    if val in (None, "", "$"):
        return None
    return str(val).strip()


def interpret(bapi_name: str, raw: dict[str, Any], *, dry_run: bool = False,
              elapsed_ms: int | None = None) -> PostingResult:
    """RFC 원시 응답 → PostingResult."""
    bapi = BAPIS.get(bapi_name) or BapiDef(
        name=bapi_name, module="?", tcode="-", description="")
    messages = parse_messages(raw, bapi.return_param)
    has_error = any(m.is_error for m in messages)
    doc_no = _extract_doc_number(raw, bapi)
    # 전기 BAPI 인데 문서번호가 없고 오류도 없으면 이상 상황으로 간주한다.
    if not has_error and bapi.doc_number_field and doc_no is None and not dry_run:
        has_error = True
        messages.append(BapiMessage(
            type="E", id="ZAGENT", number="001",
            message=f"{bapi_name} 이 문서번호를 반환하지 않았습니다. 전기 실패로 처리합니다."))
    return PostingResult(
        bapi=bapi_name, success=not has_error, document_number=doc_no,
        fiscal_year=(str(raw.get(bapi.fiscal_year_field)).strip()
                     if bapi.fiscal_year_field and raw.get(bapi.fiscal_year_field) else None),
        messages=messages, dry_run=dry_run, elapsed_ms=elapsed_ms,
        raw={k: v for k, v in raw.items() if k != bapi.return_param},
    )


class TimedCall:
    """RFC 호출 시간 측정 컨텍스트."""

    def __enter__(self) -> "TimedCall":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc: object) -> None:
        self.elapsed_ms = int((time.perf_counter() - self._t0) * 1000)
