# -*- coding: utf-8 -*-
"""pyrfc 기반 실제 SAP 연결 클라이언트.

사전 준비:
  1. SAP NetWeaver RFC SDK 설치 (SAP Support Portal, 계약 필요)
  2. pip install pyrfc

접속 정보는 환경변수 또는 sapnwrfc.ini 로 주입한다.
  SAP_ASHOST, SAP_SYSNR, SAP_CLIENT, SAP_USER, SAP_PASSWD, SAP_LANG
  (또는 메시지 서버 접속: SAP_MSHOST, SAP_GROUP, SAP_SYSID)
"""
from __future__ import annotations

import os
from typing import Any, Optional


class RfcConfigError(RuntimeError):
    pass


def connection_params(**overrides: Any) -> dict[str, Any]:
    """환경변수에서 RFC 접속 파라미터를 구성한다."""
    env = os.environ
    params: dict[str, Any] = {
        "client": env.get("SAP_CLIENT", ""),
        "user": env.get("SAP_USER", ""),
        "passwd": env.get("SAP_PASSWD", ""),
        "lang": env.get("SAP_LANG", "KO"),
    }
    if env.get("SAP_MSHOST"):                       # 로드밸런싱 접속
        params.update(mshost=env["SAP_MSHOST"],
                      group=env.get("SAP_GROUP", "PUBLIC"),
                      sysid=env.get("SAP_SYSID", ""))
    else:                                           # 애플리케이션 서버 직접 접속
        params.update(ashost=env.get("SAP_ASHOST", ""),
                      sysnr=env.get("SAP_SYSNR", "00"))
    if env.get("SAP_SNC_QOP"):                      # SNC(암호화) 사용 시
        params.update(snc_qop=env["SAP_SNC_QOP"],
                      snc_myname=env.get("SAP_SNC_MYNAME", ""),
                      snc_partnername=env.get("SAP_SNC_PARTNERNAME", ""),
                      snc_lib=env.get("SAP_SNC_LIB", ""))
    params.update(overrides)
    missing = [k for k in ("client", "user", "passwd") if not params.get(k)]
    if missing:
        raise RfcConfigError(
            f"SAP 접속 정보가 부족합니다: {', '.join(missing)}. "
            "SAP_CLIENT / SAP_USER / SAP_PASSWD 환경변수를 설정하십시오.")
    return {k: v for k, v in params.items() if v not in (None, "")}


class RfcClient:
    """pyrfc.Connection 래퍼. 컨텍스트 매니저로 사용할 수 있다."""

    def __init__(self, *, connection: Any = None, **overrides: Any) -> None:
        if connection is not None:
            self._conn = connection
            self._owned = False
            return
        try:
            from pyrfc import Connection            # type: ignore[import-not-found]
        except ImportError as exc:                  # pragma: no cover
            raise RfcConfigError(
                "pyrfc 가 설치되어 있지 않습니다. SAP NetWeaver RFC SDK 설치 후 "
                "`pip install pyrfc` 를 실행하거나, 개발 중이라면 MockClient 를 "
                "사용하십시오.") from exc
        self._conn = Connection(**connection_params(**overrides))
        self._owned = True

    def call(self, function_name: str, **params: Any) -> dict[str, Any]:
        return self._conn.call(function_name, **params)

    def ping(self) -> bool:
        try:
            self._conn.call("RFC_PING")
            return True
        except Exception:                            # pragma: no cover
            return False

    def close(self) -> None:
        if self._owned and hasattr(self._conn, "close"):
            self._conn.close()

    def __enter__(self) -> "RfcClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def make_client(mode: str = "auto", **kwargs: Any) -> Any:
    """모드에 따라 RFC/Mock 클라이언트를 생성한다.

    mode: 'rfc' | 'mock' | 'auto'(접속정보 있으면 rfc, 없으면 mock)
    """
    from .mock import MockClient
    if mode == "mock":
        return MockClient(**kwargs)
    if mode == "rfc":
        return RfcClient(**kwargs)
    try:
        connection_params()
    except RfcConfigError:
        return MockClient()
    try:
        return RfcClient()
    except RfcConfigError:
        return MockClient()
