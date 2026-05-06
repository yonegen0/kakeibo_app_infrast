"""
@file index.py
@description GET /api/psv/{psvId} のエントリポイント。
             PSV メタデータ・取引一覧・サマリーを返す。

環境変数:
    ENV: 実行環境（dev / prod）
    TABLE_PSV: kakeibo-psv-{env}
    TABLE_SUMMARY: kakeibo-summary-{env}（設計ギャップ: 追加が必要）
"""
from __future__ import annotations

import logging
from typing import Optional

from shared.models.summary import SummaryModel
from shared.utils import response
from psv_get import logic

_logger = logging.getLogger(__name__)


def _serialize_summary(summary: Optional[SummaryModel]) -> Optional[dict[str, object]]:
    """
    SummaryModel を dict に変換する。

    Args:
        summary: 月次サマリー。None の場合は None を返す。

    Returns:
        シリアライズ済み dict。summary が None の場合は None
    """
    if summary is None:
        return None
    return {
        "month": summary.month,
        "incomeTotal": summary.incomeTotal,
        "expenseTotal": summary.expenseTotal,
        "balance": summary.balance,
        "categories": [
            {"name": c.name, "amount": c.amount, "percentage": c.percentage, "kind": c.kind.value}
            for c in summary.categories
        ],
        "dailyTrend": [
            {"date": t.date, "income": t.income, "expense": t.expense, "balance": t.balance}
            for t in summary.dailyTrend
        ],
        "topExpenses": [
            {"id": e.id, "content": e.content, "amount": e.amount, "category": e.category, "date": e.date}
            for e in summary.topExpenses
        ],
        "fixedCosts": [
            {"id": f.id, "content": f.content, "amount": f.amount, "category": f.category}
            for f in summary.fixedCosts
        ],
    }


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
        "summary": _serialize_summary(summary),
    })
