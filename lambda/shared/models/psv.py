"""
@file psv.py
@description PSV（取引バッチセッション）メタデータのドメインモデル。PsvFullData も含む。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.models.transaction import TransactionModel


@dataclass
class MonthRange:
    """
    月範囲（from/to ペア）

    Attributes:
        from_month: 開始月（YYYY-MM）。"from" はPython予約語のため from_month を使用。
        to: 終了月（YYYY-MM）
    """

    from_month: str
    to: str

    def to_dict(self) -> dict[str, str]:
        """
        API レスポンス用シリアライズ。JSON キー "from" を維持する。

        Returns:
            {"from": from_month, "to": to} の dict
        """
        return {"from": self.from_month, "to": self.to}


@dataclass
class PsvMetaModel:
    """
    PSV セッションのメタデータ

    Attributes:
        psvId: PSV ID（psv_ プレフィックス付き UUID）
        userId: ユーザー ID
        fileName: アップロードファイル名
        rowCount: 取引件数
        monthRange: 取引の月範囲
        createdAt: 作成日時（ISO 8601）
        updatedAt: 更新日時（ISO 8601）
        isLatest: 最新フラグ
    """

    psvId: str
    userId: str
    fileName: str
    rowCount: int
    monthRange: MonthRange
    createdAt: str
    updatedAt: str
    isLatest: bool


@dataclass
class PsvFullData:
    """
    PSV の完全データ（メタデータ + 取引一覧）

    Attributes:
        meta: PSV メタデータ
        transactions: 取引明細リスト
    """

    meta: PsvMetaModel
    transactions: list[TransactionModel]
