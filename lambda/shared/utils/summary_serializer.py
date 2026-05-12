"""
@file summary_serializer.py
@description SummaryModel を API レスポンス用 dict に変換するユーティリティ。
             summary_create / summary_get の両 Lambda から共通利用する。
"""
from __future__ import annotations

from shared.models.summary import SummaryModel


def serialize_summary(summary: SummaryModel) -> dict[str, object]:
    """
    SummaryModel を API レスポンス用 dict に変換する。

    Args:
        summary: 変換対象の SummaryModel

    Returns:
        API レスポンス用 dict
    """
    return {
        "month": summary.month,
        "incomeTotal": summary.incomeTotal.value,
        "expenseTotal": summary.expenseTotal.value,
        "balance": summary.balance.value,
        "categories": [
            {"name": c.name, "amount": c.amount.value, "percentage": c.percentage, "kind": c.kind.value}
            for c in summary.categories
        ],
        "dailyTrend": [
            {"date": t.date, "income": t.income.value, "expense": t.expense.value, "balance": t.balance.value}
            for t in summary.dailyTrend
        ],
        "topExpenses": [
            {"id": e.id, "content": e.content, "amount": e.amount.value, "category": e.category, "date": e.date}
            for e in summary.topExpenses
        ],
        "fixedCosts": [
            {"id": f.id, "content": f.content, "amount": f.amount.value, "category": f.category}
            for f in summary.fixedCosts
        ],
    }
