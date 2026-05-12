"""
@file bedrock.py
@description AWS Bedrock（Claude）へのプロンプト送信を担当する。
"""
from __future__ import annotations

import json
import os

import boto3

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("AWS_REGION", "ap-northeast-1"),
)

DEFAULT_MODEL_ID: str = os.environ.get(
    "BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-5"
)


def invoke_claude(prompt: str, model_id: str = DEFAULT_MODEL_ID) -> str:
    """
    Claude モデルにプロンプトを送信し、テキストレスポンスを返す。

    Args:
        prompt: 送信するプロンプト文字列
        model_id: Bedrock モデル ID

    Returns:
        Claude のテキストレスポンス
    """
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
    )
    response = _bedrock.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    result: dict = json.loads(response["body"].read())
    return str(result["content"][0]["text"])
