"""
@file sqs.py
@description SQS へのメッセージ送信を担当する。
"""
from __future__ import annotations

import json
import os

import boto3

_sqs = boto3.client(
    "sqs",
    region_name=os.environ.get("AWS_REGION", "ap-northeast-1"),
)
CSV_QUEUE_URL: str = os.environ.get("CSV_QUEUE_URL", "")


def send_csv_processing_message(
    psv_id: str,
    user_id: str,
    s3_key: str,
) -> None:
    """
    CSV 非同期処理メッセージを SQS に送信する。

    Args:
        psv_id: 対象 PSV ID
        user_id: ユーザー ID
        s3_key: S3 上の CSV ファイルキー
    """
    _sqs.send_message(
        QueueUrl=CSV_QUEUE_URL,
        MessageBody=json.dumps(
            {"psv_id": psv_id, "user_id": user_id, "s3_key": s3_key},
            ensure_ascii=False,
        ),
    )
