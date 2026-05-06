"""
@file logic.py
@description report_get のビジネスロジック。レポート ID からレポートを取得する。
"""
from __future__ import annotations

from typing import Optional

from shared.infra import dynamodb
from shared.models.report import AIReportModel


def get_report(report_id: str) -> Optional[AIReportModel]:
    """
    レポート ID からレポートを取得する。

    Args:
        report_id: 取得対象のレポート ID

    Returns:
        AIReportModel。存在しない場合は None
    """
    return dynamodb.get_report(report_id)
