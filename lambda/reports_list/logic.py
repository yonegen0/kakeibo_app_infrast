"""
@file logic.py
@description reports_list のビジネスロジック。レポート一覧を取得する。
"""
from __future__ import annotations

from typing import Optional

from shared.infra import dynamodb
from shared.models.report import AIReportModel


def list_reports(
    user_id: str,
    psv_id: Optional[str],
) -> list[AIReportModel]:
    """
    レポート一覧を取得する。

    psvId 指定時は psvId-index GSI で絞り込む。
    未指定時は userId-createdAt-index GSI でユーザー全レポートを返す。

    Args:
        user_id: ユーザー ID（psvId 未指定時の絞り込みに使用）
        psv_id: 絞り込む PSV ID（省略可）

    Returns:
        AIReportModel のリスト（createdAt 降順）
    """
    if psv_id:
        return dynamodb.list_reports_by_psv(psv_id)
    return dynamodb.list_reports_by_user(user_id)
