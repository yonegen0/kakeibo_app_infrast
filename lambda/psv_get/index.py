"""
@file index.py
@description GET /api/psv/{psvId} のエントリポイント。
             PSV メタデータ・取引一覧・サマリーを返す。

環境変数:
    ENV: 実行環境（dev / prod）
    TABLE_PSV: kakeibo-psv-{env}
    TABLE_SUMMARY: kakeibo-summary-{env}
"""
from __future__ import annotations

import logging

from shared.utils import response
from shared.utils.summary_serializer import serialize_summary
from psv_get import logic

_logger = logging.getLogger(__name__)


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

    path_params = event.get("pathParameters") or {}
    psv_id = str(path_params.get("psvId", ""))
    if not psv_id:
        return response.error(400, "psvId は必須です")

    try:
        result = logic.get_psv(psv_id)
    except Exception:
        _logger.exception("PSV 取得中に予期しないエラーが発生しました psv_id=%s", psv_id)
        return response.error(500, "PSV の取得に失敗しました")

    if result is None:
        return response.error(404, "指定された PSV が見つかりません")

    psv_data, summary = result
    meta = psv_data.meta

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
        "transactions": [
            {
                "id": tx.id,
                "date": tx.date,
                "amount": {"value": tx.amount.value, "unit": tx.amount.unit},
                "content": tx.content,
                "category": tx.category,
                "subCategory": tx.subCategory,
                "isFixedCost": tx.isFixedCost,
                "isCalculated": tx.isCalculated,
                "isTransfer": tx.isTransfer,
                "memo": tx.memo,
                "source": tx.source.value,
            }
            for tx in psv_data.transactions
        ],
        "summary": serialize_summary(summary) if summary is not None else None,
    })
