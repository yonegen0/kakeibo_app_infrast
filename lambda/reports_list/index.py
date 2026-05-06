"""
@file index.py
@description GET /api/reports のエントリポイント。
             レポート一覧を返す。psvId クエリパラメータで絞り込み可能。

環境変数:
    ENV: 実行環境（dev / prod）
    TABLE_REPORT: kakeibo-report-{env}
    INDEX: userId-createdAt-index
"""
from __future__ import annotations

import logging
import os

from shared.utils import response
from reports_list import logic

_ENV = os.environ.get("ENV", "dev")
_logger = logging.getLogger(__name__)


def _resolve_user_id(event: dict[str, object]) -> str:
    """
    リクエストからユーザー ID を解決する。
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
        _context: Lambda コンテキスト（未使用）

    Returns:
        API Gateway プロキシ統合レスポンス
    """
    if event.get("httpMethod") == "OPTIONS":
        return response.options()

    query_params = event.get("queryStringParameters")
    if not isinstance(query_params, dict):
        query_params = {}
    psv_id_raw = query_params.get("psvId")
    psv_id = str(psv_id_raw).strip() if isinstance(psv_id_raw, str) and psv_id_raw.strip() else None

    user_id = _resolve_user_id(event)

    try:
        reports = logic.list_reports(user_id=user_id, psv_id=psv_id)
    except Exception:
        _logger.exception("レポート一覧取得中に予期しないエラーが発生しました user_id=%s", user_id)
        return response.error(500, "レポート一覧の取得に失敗しました")

    return response.ok({
        "reports": [
            {
                "reportId": r.reportId,
                "psvId": r.psvId,
                "title": r.title,
                "summary": r.summary,
                "highlights": r.highlights,
                "promptSnapshot": r.promptSnapshot,
                "reportMarkdown": r.reportMarkdown,
                "createdAt": r.createdAt,
            }
            for r in reports
        ]
    })
