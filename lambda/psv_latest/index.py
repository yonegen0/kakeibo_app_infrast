"""
@file index.py
@description GET /api/psv/latest のエントリポイント。
             最新 PSV のメタデータを返す。

環境変数:
    ENV: 実行環境（dev / prod）
    TABLE_PSV: kakeibo-psv-{env}
    INDEX: userId-createdAt-index
"""
from __future__ import annotations

import logging
import os

from shared.utils import response
from psv_latest import logic

_ENV = os.environ.get("ENV", "dev")
_logger = logging.getLogger(__name__)


def _resolve_user_id(event: dict[str, object]) -> str:
    """
    リクエストからユーザー ID を取得する。
    prod 環境は Cognito JWT の sub クレームを使用し、dev 環境はデフォルト値を返す。

    Args:
        event: API Gateway プロキシ統合イベント

    Returns:
        ユーザー ID 文字列
    """
    if _ENV != "prod":
        return "demo-user"
    ctx = event.get("requestContext")
    if not isinstance(ctx, dict):
        return "demo-user"
    authorizer = ctx.get("authorizer")
    if not isinstance(authorizer, dict):
        return "demo-user"
    claims = authorizer.get("claims")
    if not isinstance(claims, dict):
        return "demo-user"
    user_id = claims.get("sub")
    return str(user_id) if user_id else "demo-user"


def handler(event: dict[str, object], _context: object) -> dict[str, object]:
    """
    Lambda ハンドラ。

    Args:
        event: API Gateway プロキシ統合イベント
        context: Lambda コンテキスト（未使用）

    Returns:
        API Gateway プロキシ統合レスポンス
    """
    if event.get("httpMethod") == "OPTIONS":
        return response.options()

    user_id = _resolve_user_id(event)

    try:
        meta = logic.get_latest_psv(user_id)
    except Exception:
        _logger.exception("最新 PSV 取得中に予期しないエラーが発生しました user_id=%s", user_id)
        return response.error(500, "最新 PSV の取得に失敗しました")

    if meta is None:
        return response.error(404, "PSV が存在しません")

    return response.ok({
        "psvId": meta.psvId,
        "meta": {
            "psvId": meta.psvId,
            "userId": meta.userId,
            "fileName": meta.fileName,
            "rowCount": meta.rowCount,
            "monthRange": meta.monthRange.to_dict(),
            "createdAt": meta.createdAt,
            "updatedAt": meta.updatedAt,
            "isLatest": meta.isLatest,
        },
    })
