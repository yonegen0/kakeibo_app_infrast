"""
@file report.py
@description AI 生成レポートのドメインモデル。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AIReportModel:
    """
    AI 生成レポート 1 件

    Attributes:
        reportId: レポート ID（rep_ プレフィックス付き UUID）
        psvId: 元になった PSV の ID
        title: レポートタイトル
        summary: 1〜2 文の要約
        highlights: 重要ポイントの箇条書きリスト
        promptSnapshot: レポート生成時のプロンプト（監査用）
        reportMarkdown: Markdown 形式の本文
        createdAt: 生成日時（ISO 8601）
    """

    reportId: str
    psvId: str
    title: str
    summary: str
    highlights: list[str]
    promptSnapshot: str
    reportMarkdown: str
    createdAt: str
