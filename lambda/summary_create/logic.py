"""
@file logic.py
@description summary_create のビジネスロジック。
             取引一覧から月次サマリーを計算する純粋関数。
"""
from __future__ import annotations

from shared.models.summary import SummaryModel
from shared.models.transaction import TransactionModel
from shared.utils.summary_builder import build_summary


def create_summary(transactions: list[TransactionModel]) -> SummaryModel:
    """
    取引一覧から月次サマリーを生成する。

    Args:
        transactions: PSV の取引明細リスト

    Returns:
        生成した SummaryModel

    Raises:
        ValueError: 取引が空または計算対象外の場合
    """
    summary = build_summary(transactions)
    if summary is None:
        raise ValueError("サマリーの生成に失敗しました（取引が空か計算対象外です）")
    return summary
