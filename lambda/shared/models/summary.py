"""
@file summary.py
@description 月次サマリーのドメインモデル群。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from shared.models.transaction import Amount


class CategoryKind(Enum):
    """カテゴリの収支区分"""

    INCOME = "income"
    EXPENSE = "expense"


@dataclass
class SummaryCategory:
    """
    カテゴリ別集計

    Attributes:
        name: カテゴリ名
        amount: 金額
        percentage: 全体に占める割合（%）
        kind: 収支区分
    """

    name: str
    amount: Amount
    percentage: float
    kind: CategoryKind


@dataclass
class DailyTrend:
    """
    日別収支トレンド

    Attributes:
        date: 日付（YYYY-MM-DD）
        income: 当日収入合計
        expense: 当日支出合計
        balance: 当日収支（income - expense）
    """

    date: str
    income: Amount
    expense: Amount
    balance: Amount


@dataclass
class TopExpense:
    """
    上位支出明細

    Attributes:
        id: 取引 ID
        content: 取引内容
        amount: 金額（正数）
        category: カテゴリ
        date: 取引日（YYYY-MM-DD）
    """

    id: str
    content: str
    amount: Amount
    category: str
    date: str


@dataclass
class FixedCostItem:
    """
    固定費明細

    Attributes:
        id: 取引 ID
        content: 取引内容
        amount: 金額（正数）
        category: カテゴリ
    """

    id: str
    content: str
    amount: Amount
    category: str


@dataclass
class SummaryModel:
    """
    月次サマリー

    Attributes:
        month: 対象月（YYYY-MM）
        incomeTotal: 収入合計
        expenseTotal: 支出合計
        balance: 収支（incomeTotal - expenseTotal）
        categories: カテゴリ別集計リスト（金額降順）
        dailyTrend: 日別トレンドリスト（日付昇順）
        topExpenses: 上位支出リスト（最大 5 件）
        fixedCosts: 固定費リスト（金額降順）
    """

    month: str
    incomeTotal: Amount
    expenseTotal: Amount
    balance: Amount
    categories: list[SummaryCategory]
    dailyTrend: list[DailyTrend]
    topExpenses: list[TopExpense]
    fixedCosts: list[FixedCostItem]
