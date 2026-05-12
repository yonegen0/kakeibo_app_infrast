"""
@file index.py
@description POST /api/summary/{psvId} のエントリポイント。
             PSV の取引一覧からサマリーを生成して保存し、結果を返す。

環境変数:
    ENV: 実行環境（dev / prod）
    TABLE_PSV: kakeibo-psv-{env}
    TABLE_SUMMARY: kakeibo-summary-{env}
"""
from __future__ import annotations

import logging

from shared.infra import dynamodb
from shared.utils import response
from shared.utils.summary_serializer import serialize_summary
from summary_create import logic

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

    psv_data = dynamodb.get_psv_full(psv_id)
    if psv_data is None:
        return response.error(404, "指定された PSV が見つかりません")

    try:
        summary = logic.create_summary(psv_data.transactions)
    except ValueError as e:
        return response.error(422, str(e))
    except Exception:
        logger.exception("サマリー生成中に予期しないエラーが発生しました psv_id=%s", psv_id)
        return response.error(500, "サマリーの生成に失敗しました")

    dynamodb.upsert_summary(psv_id, summary)

    return response.ok({"summary": serialize_summary(summary)})
