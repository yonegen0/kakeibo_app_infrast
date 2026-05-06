"""
@file logic.py
@description psv_latest のビジネスロジック。最新 PSV のメタデータを取得する。
"""
from __future__ import annotations

from typing import Optional

from shared.infra import dynamodb
from shared.models.psv import PsvMetaModel


def get_latest_psv(user_id: str) -> Optional[PsvMetaModel]:
    """
    指定ユーザーの最新 PSV メタデータを取得する。

    Args:
        user_id: ユーザー ID

    Returns:
        PsvMetaModel。存在しない場合は None
    """
    return dynamodb.get_latest_psv_meta(user_id)
