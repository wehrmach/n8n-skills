# -*- coding: utf-8 -*-
"""SAP 거래처 마스터 조회.

증빙의 사업자등록번호를 SAP 공급업체(LIFNR)/고객(KUNNR) 코드로 해석한다.
 * 실제 SAP: RFC_READ_TABLE 로 LFA1-STCD2 / KNA1-STCD2 를 조회
 * 시뮬레이션: JSON 파일 기반 로컬 디렉터리
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .sap.client import SapClient


def normalize_biz_no(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


@dataclass
class MasterRecord:
    sap_code: str
    name: str
    biz_reg_no: str
    kind: str = "vendor"          # vendor | customer
    payment_terms: Optional[str] = None
    recon_account: Optional[str] = None
    blocked: bool = False


@dataclass
class MasterDirectory:
    """로컬 거래처 디렉터리(시뮬레이션 및 캐시용)."""

    records: dict[str, MasterRecord] = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: str | Path) -> "MasterDirectory":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        recs = {}
        for r in data:
            key = normalize_biz_no(r["biz_reg_no"])
            recs[key] = MasterRecord(
                sap_code=r["sap_code"], name=r["name"], biz_reg_no=key,
                kind=r.get("kind", "vendor"),
                payment_terms=r.get("payment_terms"),
                recon_account=r.get("recon_account"),
                blocked=r.get("blocked", False))
        return cls(records=recs)

    def add(self, rec: MasterRecord) -> None:
        self.records[normalize_biz_no(rec.biz_reg_no)] = rec

    def find(self, biz_reg_no: str | None, kind: str = "vendor") -> Optional[MasterRecord]:
        rec = self.records.get(normalize_biz_no(biz_reg_no))
        return rec if rec and rec.kind == kind else None

    def find_by_name(self, name: str, kind: str = "vendor") -> Optional[MasterRecord]:
        n = (name or "").replace(" ", "")
        for rec in self.records.values():
            if rec.kind == kind and rec.name.replace(" ", "") == n:
                return rec
        return None


#: 데모용 기본 디렉터리 - samples/korean-vouchers 의 가상 거래처와 대응
DEMO_DIRECTORY = MasterDirectory(records={
    "2148101117": MasterRecord("0000100234", "(주)한빛테크놀로지", "2148101117",
                               "vendor", payment_terms="N030", recon_account="251100"),
    "1378123454": MasterRecord("0000200567", "(주)미래유통", "1378123454",
                               "customer", recon_account="108100"),
    "2201509875": MasterRecord("0000100311", "한빛문구 역삼점", "2201509875", "vendor"),
    "1068102227": MasterRecord("0000100312", "대한사무기기(주)", "1068102227", "vendor"),
    "1182204560": MasterRecord("0000100313", "번개퀵서비스", "1182204560", "vendor"),
    "1201508881": MasterRecord("0000100314", "고향식당", "1201508881", "vendor"),
    "6058102229": MasterRecord("0000100315", "대한호텔 부산", "6058102229", "vendor"),
    "1108104447": MasterRecord("0000100316", "코리아항공(주)", "1108104447", "vendor"),
    "3148205555": MasterRecord("0000100317", "대한철도공사", "3148205555", "vendor"),
    "2208107775": MasterRecord("0000100318", "대한교통(주)", "2208107775", "vendor"),
    "1028203333": MasterRecord("0000100319", "사단법인 한빛나눔재단", "1028203333",
                               "vendor"),
    "2018200026": MasterRecord("0000100320", "한국도로공사", "2018200026", "vendor"),
    "1208100190": MasterRecord("0000100321", "한빛에너지(주)", "1208100190", "vendor"),
    "2028148929": MasterRecord("0000100322", "대한카드(주)", "2028148929", "vendor"),
    "1218300111": MasterRecord("0000100323", "인천세관장", "1218300111", "vendor"),
    "2148129997": MasterRecord("0000100324", "한빛빌딩 주차장", "2148129997", "vendor"),
})


class MasterLookup:
    """SAP 우선 조회 → 실패 시 로컬 디렉터리 폴백."""

    def __init__(self, client: SapClient | None = None,
                 directory: MasterDirectory | None = None,
                 use_rfc: bool = False) -> None:
        self.client = client
        self.directory = directory or DEMO_DIRECTORY
        self.use_rfc = use_rfc

    # ------------------------------------------------------------ RFC 조회

    def _read_table(self, table: str, fields: list[str],
                    where: str) -> list[dict[str, str]]:
        """RFC_READ_TABLE 로 마스터 테이블을 조회한다."""
        if self.client is None:
            return []
        raw = self.client.call(
            "RFC_READ_TABLE",
            QUERY_TABLE=table, DELIMITER="|",
            FIELDS=[{"FIELDNAME": f} for f in fields],
            OPTIONS=[{"TEXT": where}], ROWCOUNT=5)
        out = []
        for row in raw.get("DATA", []) or []:
            parts = [p.strip() for p in str(row.get("WA", "")).split("|")]
            out.append(dict(zip(fields, parts)))
        return out

    # ------------------------------------------------------------ 공개 API

    def vendor(self, biz_reg_no: str | None, name: str | None = None
               ) -> Optional[MasterRecord]:
        return self._lookup(biz_reg_no, name, "vendor")

    def customer(self, biz_reg_no: str | None, name: str | None = None
                 ) -> Optional[MasterRecord]:
        return self._lookup(biz_reg_no, name, "customer")

    def _lookup(self, biz_reg_no: str | None, name: str | None,
                kind: str) -> Optional[MasterRecord]:
        digits = normalize_biz_no(biz_reg_no)
        if self.use_rfc and self.client is not None and digits:
            table, code_field = (("LFA1", "LIFNR") if kind == "vendor"
                                 else ("KNA1", "KUNNR"))
            try:
                rows = self._read_table(table, [code_field, "NAME1", "STCD2"],
                                        f"STCD2 = '{digits}'")
                if rows:
                    rec = MasterRecord(
                        sap_code=rows[0][code_field], name=rows[0].get("NAME1", ""),
                        biz_reg_no=digits, kind=kind)
                    self.directory.add(rec)
                    return rec
            except Exception:                    # RFC 실패 시 로컬 폴백
                pass
        rec = self.directory.find(digits, kind)
        if rec is None and name:
            rec = self.directory.find_by_name(name, kind)
        return rec


def enrich(doc: Any, lookup: MasterLookup) -> list[str]:
    """VoucherDocument 의 거래처에 SAP 코드를 채운다. 미해결 항목을 반환한다."""
    unresolved: list[str] = []
    if doc.supplier is not None and not doc.supplier.sap_vendor:
        rec = lookup.vendor(doc.supplier.biz_reg_no, doc.supplier.name)
        if rec:
            doc.supplier.sap_vendor = rec.sap_code
        else:
            unresolved.append(
                f"공급업체 미등록: {doc.supplier.name} "
                f"({doc.supplier.biz_reg_no or '사업자번호 없음'})")
    if doc.buyer is not None and not doc.buyer.sap_customer:
        rec = lookup.customer(doc.buyer.biz_reg_no, doc.buyer.name)
        if rec:
            doc.buyer.sap_customer = rec.sap_code
    return unresolved
