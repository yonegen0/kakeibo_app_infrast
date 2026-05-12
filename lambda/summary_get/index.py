"""
@file index.py
@description GET /api/summary/{psvId} のエントリポイント。
             保存済みサマリーを返す。

環境変数:
    ENV: 実行環境（dev / prod）
    TABLE_SUMMARY: kakeibo-summary-{env}
"""
from __future__ import annotations

import logging

from shared.utils import response
from shared.utils.summary_serializer import serialize_summary
from summary_get import logic

logger = logging.getLogger(__name__)


def handler(event: dict[str, object], context: object) -> dict[str, object]:
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

    path_params = event.get("pathParameters") or {}
    psv_id = str(path_params.get("psvId", ""))
    if not psv_id:
        return response.error(400, "psvId は必須です")

    try:
        summary = logic.get_summary(psv_id)
    except Exception:
        logger.exception("サマリー取得中に予期しないエラーが発生しました psv_id=%s", psv_id)
        return response.error(500, "サマリーの取得に失敗しました")

    if summary is None:
        return response.error(404, "指定された PSV またはサマリーが見つかりません")

    return response.ok({"summary": serialize_summary(summary)})
