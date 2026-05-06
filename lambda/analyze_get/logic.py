"""
@file logic.py
@description analyze_get のビジネスロジック。
             分析用プロンプトを取得する。analyze テーブルに保存済みがあればそれを返し、
             なければ PSV・サマリーから動的に生成する。
"""
from __future__ import annotations

from typing import Optional

from shared.infra import dynamodb
from shared.utils.prompt_builder import build_analysis_prompt


def get_analyze_prompt(psv_id: str) -> Optional[str]:
    """
    分析用プロンプトを取得する。

    analyze テーブルに保存済みプロンプトがある場合はそれを返す（前回 analyze_post 実行時のもの）。
    存在しない場合は PSV・サマリーから動的に生成して返す。

    Args:
        psv_id: 対象 PSV ID

    Returns:
        プロンプト文字列。PSV が存在しない場合は None

    Raises:
        ValueError: サマリーが存在しない（422）

    Note:
        インフラ設計書のギャップ: TABLE_PSV・TABLE_SUMMARY env var と
        dynamodb:PartiQLSelect 権限の追加が必要。
    """
    cached = dynamodb.get_analyze_record(psv_id)
    if cached:
        return cached

    psv_data = dynamodb.get_psv_full(psv_id)
    if psv_data is None:
        return None  # 404

    summary = dynamodb.get_summary(psv_id)
    if summary is None:
        raise ValueError("サマリーが存在しません。先に POST /api/summary/{psvId} を実行してください")

    return build_analysis_prompt(summary, psv_data.transactions)
