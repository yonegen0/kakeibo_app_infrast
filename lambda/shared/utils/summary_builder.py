"""
@file summary_builder.py
@description 取引一覧から月次サマリーを計算する純粋関数。
             TypeScript 版 summary.ts の buildSummary() を移植。
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Optional

from shared.models.summary import (
    CategoryKind,
    DailyTrend,
    FixedCostItem,
    SummaryCategory,
    SummaryModel,
    TopExpense,
)
from shared.models.transaction import Amount, TransactionModel

_MONTH_RE = re.compile(r"^(\d{4})[/-](\d{2})")
_DATE_RE = re.compile(r"^(\d{4})[/-](\d{2})[/-](\d{2})")
_TOP_EXPENSES_LIMIT = 5


def _extract_month(date: str) -> Optional[str]:
    """日付文字列から YYYY-MM を抽出する。"""
    m = _MONTH_RE.match(date)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def _extract_date_key(date: str) -> Optional[str]:
    """日付文字列から YYYY-MM-DD を抽出する。"""
    m = _DATE_RE.match(date)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def build_summary(transactions: list[TransactionModel]) -> Optional[SummaryModel]:
    """
    取引一覧から月次サマリーを計算する。

    計算対象フラグが False または振替フラグが True の取引を除外し、
    残りから収支・カテゴリ別集計・日別トレンド・上位支出・固定費を算出する。

    Args:
        transactions: 取引明細リスト

    Returns:
        SummaryModel。取引が空または計算対象が存在しない場合は None
    """
    if not transactions:
        return None

    scoped = [
        t for t in transactions
        if t.isCalculated is not False and t.isTransfer is not True
    ]
    if not scoped:
        return None

    months = sorted(
        m for t in scoped if (m := _extract_month(t.date)) is not None
    )
    month = months[-1] if months else ""

    income_total = sum(t.amount.value for t in scoped if t.amount.value > 0)
    expense_total = sum(abs(t.amount.value) for t in scoped if t.amount.value < 0)
    balance = income_total - expense_total
    total_abs = income_total + expense_total

    cat_income: dict[str, float] = defaultdict(float)
    cat_expense: dict[str, float] = defaultdict(float)
    for t in scoped:
        if t.amount.value > 0:
            cat_income[t.category] += t.amount.value
        elif t.amount.value < 0:
            cat_expense[t.category] += abs(t.amount.value)

    all_category_names = set(cat_income) | set(cat_expense)
    categories: list[SummaryCategory] = []
    for name in all_category_names:
        inc = cat_income.get(name, 0.0)
        exp = cat_expense.get(name, 0.0)
        kind = CategoryKind.INCOME if inc >= exp else CategoryKind.EXPENSE
        amount = inc if kind == CategoryKind.INCOME else exp
        percentage = (amount / total_abs * 100) if total_abs > 0 else 0.0
        categories.append(
            SummaryCategory(name=name, amount=Amount(value=amount, unit="JPY"), percentage=percentage, kind=kind)
        )
    categories.sort(key=lambda c: c.amount.value, reverse=True)

    by_date: dict[str, dict[str, float]] = defaultdict(
        lambda: {"income": 0.0, "expense": 0.0}
    )
    for t in scoped:
        date_key = _extract_date_key(t.date)
        if date_key is None:
            continue
        if t.amount.value > 0:
            by_date[date_key]["income"] += t.amount.value
        elif t.amount.value < 0:
            by_date[date_key]["expense"] += abs(t.amount.value)

    daily_trend = [
        DailyTrend(
            date=date,
            income=Amount(value=vals["income"], unit="JPY"),
            expense=Amount(value=vals["expense"], unit="JPY"),
            balance=Amount(value=vals["income"] - vals["expense"], unit="JPY"),
        )
        for date, vals in sorted(by_date.items())
    ]

    top_expenses = [
        TopExpense(
            id=t.id,
            content=t.content,
            amount=Amount(value=abs(t.amount.value), unit=t.amount.unit),
            category=t.category,
            date=t.date,
        )
        for t in sorted(
            (t for t in scoped if t.amount.value < 0),
            key=lambda t: abs(t.amount.value),
            reverse=True,
        )[:_TOP_EXPENSES_LIMIT]
    ]

    fixed_costs = sorted(
        [
            FixedCostItem(
                id=t.id,
                content=t.content,
                amount=Amount(value=abs(t.amount.value), unit=t.amount.unit),
                category=t.category,
            )
            for t in scoped
            if t.isFixedCost
        ],
        key=lambda f: f.amount.value,
        reverse=True,
    )

    return SummaryModel(
        month=month,
        incomeTotal=Amount(value=income_total, unit="JPY"),
        expenseTotal=Amount(value=expense_total, unit="JPY"),
        balance=Amount(value=balance, unit="JPY"),
        categories=categories,
        dailyTrend=daily_trend,
        topExpenses=top_expenses,
        fixedCosts=fixed_costs,
    )
