"""
@file response.py
@description Lambda 関数の HTTP レスポンスヘルパー。
             CORS の allow_origin は ENV 環境変数で dev / prod を切り替える。
"""
from __future__ import annotations

import json
import os

_ENV = os.environ.get("ENV", "dev")
_ALLOW_ORIGINS: dict[str, str] = {
    "prod": "https://example.com",
    "dev": "http://localhost:3000",
}
_ORIGIN = _ALLOW_ORIGINS.get(_ENV, "http://localhost:3000")

_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": _ORIGIN,
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def ok(body: dict[str, object]) -> dict[str, object]:
    """
    HTTP 200 レスポンスを生成する。

    Args:
        body: レスポンスボディの dict

    Returns:
        Lambda プロキシ統合形式のレスポンス dict
    """
    return {
        "statusCode": 200,
        "headers": _HEADERS,
        "body": json.dumps(body, ensure_ascii=False),
    }


def error(status: int, message: str) -> dict[str, object]:
    """
    エラーレスポンスを生成する。

    Args:
        status: HTTP ステータスコード
        message: エラーメッセージ

    Returns:
        Lambda プロキシ統合形式のエラーレスポンス dict
    """
    return {
        "statusCode": status,
        "headers": _HEADERS,
        "body": json.dumps({"error": message}, ensure_ascii=False),
    }


def options() -> dict[str, object]:
    """
    CORS プリフライトリクエスト（OPTIONS）へのレスポンスを生成する。

    Returns:
        Lambda プロキシ統合形式の OPTIONS レスポンス dict
    """
    return {
        "statusCode": 200,
        "headers": _HEADERS,
        "body": "",
    }
