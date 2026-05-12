"""
@file transaction.py
@description 取引明細ドメインモデル。Amount・TransactionModel・MfRow を定義する。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TransactionSource(Enum):
    """取引の取込元"""

    MONEYFORWARD = "moneyforward"


@dataclass
class Amount:
    """
    金額値オブジェクト

    Attributes:
        value: 金額（正数=収入、負数=支出）
        unit: 通貨単位（例: "JPY"）
    """

    value: float
    unit: str


@dataclass
class TransactionModel:
    """
    取引明細 1 件

    Attributes:
        id: 取引 ID
        date: 取引日（YYYY-MM-DD）
        amount: 金額値オブジェクト
        content: 取引内容
        category: 大項目カテゴリ
        subCategory: 中項目カテゴリ
        isFixedCost: 固定費フラグ
        memo: 補足メモ
        source: 取込元
        isCalculated: 計算対象フラグ（デフォルト True）
        isTransfer: 振替フラグ（デフォルト False）
    """

    id: str
    date: str
    amount: Amount
    content: str
    category: str
    subCategory: str
    isFixedCost: bool
    memo: str
    source: TransactionSource
    isCalculated: bool = True
    isTransfer: bool = False


@dataclass
class MfRow:
    """
    MoneyForward CSV 1 行（パース済み）

    Attributes:
        isCalculated: 計算対象フラグ
        date: 取引日（YYYY-MM-DD、/ → - 変換済み）
        content: 取引内容
        amount: 金額（カンマ除去・数値変換済み）
        source: 保有金融機関
        category: 大項目
        subCategory: 中項目
        memo: メモ
        isTransfer: 振替フラグ
        mfId: MoneyForward 側の ID（オプション）
    """

    isCalculated: bool
    date: str
    content: str
    amount: float
    source: str
    category: str
    subCategory: str
    memo: str
    isTransfer: bool
    mfId: Optional[str] = None
