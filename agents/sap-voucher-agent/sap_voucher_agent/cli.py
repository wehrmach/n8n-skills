# -*- coding: utf-8 -*-
"""명령줄 인터페이스.

  python -m sap_voucher_agent routes [문서유형]     # BAPI 매핑 조회
  python -m sap_voucher_agent demo                  # 50종 픽스처 Mock 전기
  python -m sap_voucher_agent plan  <파일>          # 추출 + 전기계획 (Claude 필요)
  python -m sap_voucher_agent post  <파일> [--live] # 추출 + 검증 + 전기
  python -m sap_voucher_agent agent "<지시문>"      # 에이전트 자율 실행
"""
from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

from .accounts import AccountRules
from .doc_types import KR_NAME, DocType
from .mapping import ROUTES, coverage, route_for
from .master_data import MasterLookup, enrich
from .models import PostingContext
from .planner import explain, plan as build_plan
from .poster import post as run_post
from .sap.bapi_defs import BAPIS, NO_STANDARD_BAPI


def _ctx(args: argparse.Namespace) -> PostingContext:
    return PostingContext(
        company_code=args.company_code, fiscal_year=args.fiscal_year,
        username=args.user, purchasing_org=args.purch_org,
        purchasing_group=args.purch_group, plant=args.plant,
        storage_location=args.storage_loc, sales_org=args.sales_org,
        distribution_channel=args.dist_channel, division=args.division,
        default_cost_center=args.cost_center,
        approval_threshold=Decimal(str(args.approval_threshold)),
        capitalization_threshold=Decimal(str(args.capitalization_threshold)),
        deferral_min_amount=Decimal(str(args.deferral_min_amount)),
        lease_short_term_months=args.lease_short_term_months,
        period_end=_parse_date(args.period_end),
        intangible_capitalization=args.capitalize_development,
        dry_run=not getattr(args, "live", False))


def _parse_date(value: str | None):
    if not value:
        return None
    from .extraction import _date
    return _date(value)


def _client(args: argparse.Namespace):
    from .sap.rfc import make_client
    return make_client(args.sap)


# --------------------------------------------------------------------------- 명령

def cmd_routes(args: argparse.Namespace) -> int:
    if args.doc_type and args.doc_type != "all":
        try:
            r = route_for(DocType(args.doc_type))
        except (ValueError, KeyError):
            print(f"알 수 없는 문서 유형: {args.doc_type}")
            return 1
        print(f"{r.kr_name} [{r.doc_type.value}] - {r.posting_kind}")
        for key, steps in r.variants.items():
            print(f"  [{key}]")
            for s in steps:
                bd = BAPIS.get(s.bapi)
                print(f"    {s.bapi:34} {bd.tcode if bd else '-':<18} {s.purpose}")
        print(f"\n원칙: {r.notes}")
        if r.caveat:
            print(f"유의: {NO_STANDARD_BAPI[r.caveat]}")
        return 0

    print(f"{'증빙 유형':<30} {'전기성격':<12} 주 BAPI")
    print("-" * 100)
    for dt, r in ROUTES.items():
        print(f"{KR_NAME[dt]:<30} {r.posting_kind:<12} "
              f"{', '.join(r.all_bapis()[:2])}")
    c = coverage()
    print("-" * 100)
    print(f"문서유형 {c['doc_types']}종 / 사용 BAPI {len(c['distinct_bapis'])}종 / "
          f"항상 승인필요 {len(c['always_approve'])}종")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    from .fixtures import all_samples
    ctx = _ctx(args)
    sap = _client(args)
    rules = AccountRules()
    lookup = MasterLookup(client=sap)
    ok = fail = 0
    for dt, doc in all_samples().items():
        doc.source_file = f"{dt.value}.pdf"
        enrich(doc, lookup)
        if doc.supplier and not doc.supplier.sap_vendor:
            doc.supplier.sap_vendor = "0000199999"
        if doc.buyer and not doc.buyer.sap_customer:
            doc.buyer.sap_customer = "0000299999"
        p = build_plan(doc, ctx, rules)
        dry = run_post(p, sap, dry_run=True)
        out = (run_post(p, sap, dry_run=False, allow_unapproved=True)
               if dry.success and args.live else dry)
        mark = "OK " if out.success else "실패"
        ok += out.success
        fail += not out.success
        print(f"[{mark}] {KR_NAME[dt]:<30} {out.summary()[:150]}")
    print(f"\n합계 {ok + fail}종 / 성공 {ok} / 실패 {fail}"
          f"{'  (--live 없이 DRY-RUN 만 수행)' if not args.live else ''}")
    return 0 if fail == 0 else 1


def cmd_plan(args: argparse.Namespace) -> int:
    from .extraction import extract
    ctx = _ctx(args)
    sap = _client(args)
    doc = extract(args.file)
    enrich(doc, MasterLookup(client=sap))
    p = build_plan(doc, ctx, AccountRules())
    print(explain(p))
    return 0 if p.postable else 1


def cmd_post(args: argparse.Namespace) -> int:
    from .extraction import extract
    ctx = _ctx(args)
    sap = _client(args)
    doc = extract(args.file)
    unresolved = enrich(doc, MasterLookup(client=sap))
    if unresolved:
        print("거래처 미매핑:", "; ".join(unresolved))
    p = build_plan(doc, ctx, AccountRules())
    print(explain(p))
    print()
    dry = run_post(p, sap, dry_run=True)
    print("DRY-RUN:", dry.summary())
    if not dry.success:
        return 1
    if not args.live:
        print("\n실제 전기는 --live 옵션이 필요합니다.")
        return 0
    out = run_post(p, sap, dry_run=False, allow_unapproved=args.approve)
    print("전기:", out.summary())
    return 0 if out.success else 1


def cmd_kifrs(args: argparse.Namespace) -> int:
    """K-IFRS 기준서 카탈로그 또는 특정 증빙 유형의 회계판단을 출력한다."""
    from .fixtures import FACTORIES
    from .kifrs import NO_ENTRY_DOCS, SETTLEMENT_DOCS, STANDARDS, assess

    if not args.doc_type or args.doc_type == "standards":
        print("적용 K-IFRS 기준서")
        print("-" * 78)
        for code, desc in STANDARDS.items():
            print(f"  {('K-IFRS ' + code) if code != 'CF' else '개념체계':<14} {desc}")
        print("-" * 78)
        print("회계 인식 대상이 아닌 증빙(미이행계약·물류문서):")
        print("  " + ", ".join(KR_NAME[d] for d in sorted(NO_ENTRY_DOCS,
                                                          key=lambda x: x.value)))
        print("손익 미발생(채권·채무 소거) 증빙:")
        print("  " + ", ".join(KR_NAME[d] for d in sorted(SETTLEMENT_DOCS,
                                                          key=lambda x: x.value)))
        return 0

    if args.doc_type == "all":
        ctx = _ctx(args)
        print(f"{'증빙 유형':<30} {'K-IFRS 인식':<22} 기준서")
        print("-" * 100)
        for dt, factory in FACTORIES.items():
            a = assess(factory(), ctx)
            print(f"{KR_NAME[dt]:<30} {a.recognition.kr:<22} "
                  f"{', '.join(a.standards)}")
        return 0

    try:
        dt = DocType(args.doc_type)
    except ValueError:
        print(f"알 수 없는 문서 유형: {args.doc_type}")
        return 1
    print(assess(FACTORIES[dt](), _ctx(args)).summary())
    return 0


def cmd_agent(args: argparse.Namespace) -> int:
    from .agent import VoucherAgent
    ctx = _ctx(args)
    sap = _client(args)
    agent = VoucherAgent(sap=sap, ctx=ctx, lookup=MasterLookup(client=sap))
    agent.run(args.instruction)
    return 0


# --------------------------------------------------------------------------- 파서

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="sap_voucher_agent",
        description="한국 지류 증빙을 SAP 표준 BAPI 로 전기하는 AI 에이전트")
    ap.add_argument("--sap", choices=["auto", "rfc", "mock"], default="auto",
                    help="SAP 연결 방식 (기본 auto: 접속정보 없으면 mock)")
    ap.add_argument("--company-code", default="1000")
    ap.add_argument("--fiscal-year", type=int, default=None)
    ap.add_argument("--user", default="AI_AGENT")
    ap.add_argument("--purch-org", default="1000")
    ap.add_argument("--purch-group", default="001")
    ap.add_argument("--plant", default="1000")
    ap.add_argument("--storage-loc", default="0001")
    ap.add_argument("--sales-org", default="1000")
    ap.add_argument("--dist-channel", default="10")
    ap.add_argument("--division", default="00")
    ap.add_argument("--cost-center", default="1000-ADM")
    ap.add_argument("--approval-threshold", default="10000000")
    # ── K-IFRS 회계정책 ──────────────────────────────────────────────────
    ap.add_argument("--period-end", default=None,
                    help="보고기간 종료일 YYYY-MM-DD (기간귀속 판단 기준)")
    ap.add_argument("--capitalization-threshold", default="1000000",
                    help="자산 인식 최소금액(중요성 기준)")
    ap.add_argument("--deferral-min-amount", default="100000",
                    help="선급비용 이연 최소금액")
    ap.add_argument("--lease-short-term-months", type=int, default=12,
                    help="K-IFRS 1116 단기리스 면제 기준(개월)")
    ap.add_argument("--capitalize-development", action="store_true",
                    help="개발비 자본화 요건(K-IFRS 1038) 충족을 회사가 판정했음")

    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("routes", help="증빙 유형별 BAPI 매핑 조회")
    p.add_argument("doc_type", nargs="?", default="all")
    p.set_defaults(func=cmd_routes)

    p = sub.add_parser("demo", help="50종 픽스처를 SAP(기본 Mock)에 전기")
    p.add_argument("--live", action="store_true", help="DRY-RUN 이 아닌 실제 전기")
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("plan", help="증빙 파일 추출 + 전기계획 출력")
    p.add_argument("file")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("post", help="증빙 파일 추출 + 검증 + 전기")
    p.add_argument("file")
    p.add_argument("--live", action="store_true")
    p.add_argument("--approve", action="store_true", help="승인 필요 전기를 승인 처리")
    p.set_defaults(func=cmd_post)

    p = sub.add_parser("kifrs", help="K-IFRS 기준서 및 증빙별 회계판단 조회")
    p.add_argument("doc_type", nargs="?", default="standards",
                   help="'standards'(기본) | 'all' | 문서유형 코드")
    p.set_defaults(func=cmd_kifrs)

    p = sub.add_parser("agent", help="에이전트 자율 실행")
    p.add_argument("instruction")
    p.set_defaults(func=cmd_agent)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n중단되었습니다.")
        return 130
    except Exception as exc:
        print(f"오류: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
