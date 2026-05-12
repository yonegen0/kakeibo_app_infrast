"""
@file s3.py
@description S3 に対するファイルの読み書きを担当する。
             CSV の読み取りと取引 JSON のバックアップ保存を行う。
             パス構造: raw/{userId}/{psvId}.csv / raw/{userId}/{psvId}.json
"""
from __future__ import annotations

import json
import os

import boto3

from shared.models.transaction import TransactionModel

_s3 = boto3.client(
    "s3",
    region_name=os.environ.get("AWS_REGION", "ap-northeast-1"),
)
RAW_BUCKET: str = os.environ.get("RAW_BUCKET", "kakeibo-raw-data-dev")


def _csv_key(user_id: str, psv_id: str) -> str:
    return f"raw/{user_id}/{psv_id}.csv"


def _json_key(user_id: str, psv_id: str) -> str:
    return f"raw/{user_id}/{psv_id}.json"


def _tx_to_json_dict(tx: TransactionModel) -> dict[str, object]:
    return {
        "id": tx.id,
        "date": tx.date,
        "amount": {"value": tx.amount.value, "unit": tx.amount.unit},
        "content": tx.content,
        "category": tx.category,
        "subCategory": tx.subCategory,
        "isFixedCost": tx.isFixedCost,
        "memo": tx.memo,
        "source": tx.source.value,
        "isCalculated": tx.isCalculated,
        "isTransfer": tx.isTransfer,
    }


def put_csv(user_id: str, psv_id: str, content: bytes) -> None:
    """
    CSV ファイルを S3 に保存する。

    Args:
        user_id: ユーザー ID
        psv_id: PSV ID
        content: CSV の raw bytes（Shift_JIS 等）
    """
    _s3.put_object(
        Bucket=RAW_BUCKET,
        Key=_csv_key(user_id, psv_id),
        Body=content,
        ContentType="text/csv",
    )


def put_json(user_id: str, psv_id: str, transactions: list[TransactionModel]) -> None:
    """
    取引一覧を JSON として S3 にバックアップ保存する。

    Args:
        user_id: ユーザー ID
        psv_id: PSV ID
        transactions: 保存する取引明細リスト
    """
    data = [_tx_to_json_dict(tx) for tx in transactions]
    content = json.dumps(data, ensure_ascii=False).encode("utf-8")
    _s3.put_object(
        Bucket=RAW_BUCKET,
        Key=_json_key(user_id, psv_id),
        Body=content,
        ContentType="application/json",
    )


def get_csv(user_id: str, psv_id: str) -> bytes:
    """
    S3 から CSV ファイルを取得する。

    Args:
        user_id: ユーザー ID
        psv_id: PSV ID

    Returns:
        CSV の raw bytes
    """
    response = _s3.get_object(Bucket=RAW_BUCKET, Key=_csv_key(user_id, psv_id))
    return response["Body"].read()
