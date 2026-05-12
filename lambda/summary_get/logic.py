"""
@file logic.py
@description summary_get のビジネスロジック。保存済みサマリーを取得する。
"""
from __future__ import annotations

from typing import Optional

from shared.infra import dynamodb
from shared.models.summary import SummaryModel


def get_summary(psv_id: str) -> Optional[SummaryModel]:
    """
    指定 PSV の保存済みサマリーを取得する。

    Args:
        psv_id: 対象 PSV ID

    Returns:
        SummaryModel。存在しない場合は None
    """
    return dynamodb.get_summary(psv_id)
