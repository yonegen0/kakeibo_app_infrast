"""
@file logic.py
@description psv_create のビジネスロジック。
             取引一覧を受け取り PSV を生成して DynamoDB と S3 に保存する。
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from shared.infra import dynamodb, s3
from shared.models.psv import MonthRange, PsvMetaModel
from shared.models.transaction import Amount, TransactionModel, TransactionSource

_MAX_TRANSACTIONS = 1000


def _now_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_month(date: str) -> Optional[str]:
    m = re.match(r"^(\d{4})[/-](\d{2})", date)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def _build_month_range(transactions: list[TransactionModel]) -> MonthRange:
    months = sorted(
        m for t in transactions if (m := _parse_month(t.date)) is not None
    )
    if not months:
        now = datetime.now(tz=timezone.utc)
        current = f"{now.year:04d}-{now.month:02d}"
        return MonthRange(from_month=current, to=current)
    return MonthRange(from_month=months[0], to=months[-1])


def _deserialize_transaction(raw: dict[str, object]) -> TransactionModel:
    """
    リクエストボディの dict から TransactionModel を生成する。

    Args:
        raw: API リクエストの transactions 要素

    Returns:
        TransactionModel

    Raises:
        ValueError: 必須フィールド（id・date）が欠落している場合、または型が不正な場合
    """
    amount_raw = raw.get("amount", {})
    if not isinstance(amount_raw, dict):
        raise ValueError(f"amount の型が不正です: {type(amount_raw)}")

    try:
        tx_id = str(raw["id"])
        tx_date = str(raw["date"])
    except KeyError as e:
        raise ValueError(f"取引の必須フィールドが不足しています: {e}") from e

    return TransactionModel(
        id=tx_id,
        date=tx_date,
        amount=Amount(
            value=float(amount_raw.get("value", 0)),
            unit=str(amount_raw.get("unit", "JPY")),
        ),
        content=str(raw.get("content", "")),
        category=str(raw.get("category", "")),
        subCategory=str(raw.get("subCategory", "")),
        isFixedCost=bool(raw.get("isFixedCost", False)),
        memo=str(raw.get("memo", "")),
        source=TransactionSource(str(raw.get("source", "moneyforward"))),
        isCalculated=bool(raw.get("isCalculated", True)),
        isTransfer=bool(raw.get("isTransfer", False)),
    )


def create_psv(
    user_id: str,
    file_name: str,
    raw_transactions: list[dict[str, object]],
) -> tuple[str, PsvMetaModel]:
    """
    取引一覧から PSV を生成し、DynamoDB と S3 に保存する。

    Args:
        user_id: ユーザー ID
        file_name: アップロードファイル名
        raw_transactions: リクエストボディの transactions リスト（dict 形式）

    Returns:
        (psvId, PsvMetaModel) のタプル

    Raises:
        ValueError: transactions が空または上限超過の場合
    """
    if not raw_transactions:
        raise ValueError("transactions は必須です")
    if len(raw_transactions) > _MAX_TRANSACTIONS:
        raise ValueError(f"transactions は {_MAX_TRANSACTIONS} 件以下にしてください")

    transactions = [_deserialize_transaction(r) for r in raw_transactions]

    psv_id = f"psv_{uuid.uuid4().hex}"
    now = _now_utc()
    month_range = _build_month_range(transactions)

    meta = PsvMetaModel(
        psvId=psv_id,
        userId=user_id,
        fileName=file_name,
        rowCount=len(transactions),
        monthRange=month_range,
        createdAt=now,
        updatedAt=now,
        isLatest=True,
    )

    dynamodb.update_all_not_latest(exclude_id=psv_id)
    dynamodb.insert_psv(meta, transactions)
    s3.put_json(user_id=user_id, psv_id=psv_id, transactions=transactions)

    return psv_id, meta
