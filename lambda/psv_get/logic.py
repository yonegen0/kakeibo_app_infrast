"""
@file logic.py
@description psv_get のビジネスロジック。PSV の完全データとサマリーを取得する。
"""
from __future__ import annotations

from typing import Optional

from shared.infra import dynamodb
from shared.models.psv import PsvFullData
from shared.models.summary import SummaryModel


def get_psv(psv_id: str) -> Optional[tuple[PsvFullData, Optional[SummaryModel]]]:
    """
    PSV の完全データ（メタ・取引一覧）とサマリーを取得する。

    Args:
        psv_id: 対象 PSV ID

    Returns:
        (PsvFullData, SummaryModel | None) のタプル。PSV が存在しない場合は None

    Note:
        インフラ設計書のギャップ: psv_get は TABLE_SUMMARY へのアクセスも必要。
        env var TABLE_SUMMARY と dynamodb:PartiQLSelect 権限の追加が必要。
    """
    psv_data = dynamodb.get_psv_full(psv_id)
    if psv_data is None:
        return None
    summary = dynamodb.get_summary(psv_id)
    return psv_data, summary
