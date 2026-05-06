"""
@file logic.py
@description analyze_post のビジネスロジック。
             PSV を AI（Bedrock/Claude）で分析し、AIReportModel を生成して保存する。
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from shared.infra import bedrock, dynamodb
from shared.models.report import AIReportModel
from shared.utils.prompt_builder import build_analysis_prompt
from shared.utils.summary_builder import build_summary

_REPORT_MARKDOWN_MAX_SUMMARY_LEN = 300


def _now_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_title(markdown: str) -> str:
    """Markdown テキストから H1 見出しを抽出する。"""
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "家計レポート"


def _extract_summary(markdown: str) -> str:
    """
    Markdown テキストから最初の本文段落を抽出する（見出し・箇条書き除外）。
    """
    in_para = False
    lines: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or re.match(r"^[-*]\s+", stripped):
            if in_para:
                break
            continue
        in_para = True
        lines.append(stripped)

    text = " ".join(lines)
    return text[:_REPORT_MARKDOWN_MAX_SUMMARY_LEN]


def _extract_highlights(markdown: str) -> list[str]:
    """Markdown テキストから箇条書き項目を最大 10 件抽出する。"""
    highlights: list[str] = []
    for line in markdown.splitlines():
        m = re.match(r"^[-*]\s+(.+)$", line.strip())
        if m:
            highlights.append(m.group(1).strip())
            if len(highlights) >= 10:
                break
    return highlights


def _parse_report(
    markdown: str,
    report_id: str,
    psv_id: str,
    prompt_snapshot: str,
    created_at: str,
) -> AIReportModel:
    """
    Claude の Markdown レスポンスを AIReportModel に変換する。

    Args:
        markdown: Claude が出力した Markdown テキスト
        report_id: レポート ID
        psv_id: 対象 PSV ID
        prompt_snapshot: 送信したプロンプト全文
        created_at: 生成日時（ISO 8601）

    Returns:
        AIReportModel
    """
    return AIReportModel(
        reportId=report_id,
        psvId=psv_id,
        title=_extract_title(markdown),
        summary=_extract_summary(markdown),
        highlights=_extract_highlights(markdown),
        promptSnapshot=prompt_snapshot,
        reportMarkdown=markdown,
        createdAt=created_at,
    )


def analyze_and_create_report(
    psv_id: str,
    user_id: str,
    prompt_override: Optional[str],
) -> Optional[AIReportModel]:
    """
    PSV を AI 分析してレポートを生成し、DynamoDB に保存する。

    処理順:
    1. PSV + 取引一覧を取得
    2. サマリーを取得（なければ生成）
    3. プロンプトを確定（override 優先、なければ build_analysis_prompt）
    4. Bedrock（Claude）にプロンプトを送信
    5. レスポンスを解析して AIReportModel を生成
    6. analyze テーブルにプロンプトスナップショットを保存
    7. report テーブルにレポートを保存

    Args:
        psv_id: 対象 PSV ID
        user_id: ユーザー ID（report テーブルの GSI 用）
        prompt_override: ユーザーが指定したカスタムプロンプト（空白のみは無視）

    Returns:
        AIReportModel。PSV が存在しない場合は None

    Raises:
        ValueError: サマリーが存在せず生成もできない（422）
        RuntimeError: Bedrock の呼び出しまたはレスポンス解析に失敗（500）

    Note:
        インフラ設計書のギャップ:
        - TABLE_PSV / TABLE_SUMMARY env var と PartiQLSelect 権限の追加が必要
        - TABLE_REPORT env var と PartiQLInsert 権限の追加が必要
        - bedrock:InvokeModel IAM 権限の追加が必要
    """
    psv_data = dynamodb.get_psv_full(psv_id)
    if psv_data is None:
        return None  # 404

    summary = dynamodb.get_summary(psv_id)
    if summary is None:
        summary = build_summary(psv_data.transactions)
    if summary is None:
        raise ValueError("サマリーが存在しません。先に POST /api/summary/{psvId} を実行してください")

    effective_prompt = (prompt_override or "").strip() or build_analysis_prompt(
        summary, psv_data.transactions
    )

    try:
        markdown = bedrock.invoke_claude(effective_prompt)
    except Exception as e:
        raise RuntimeError(f"Bedrock の呼び出しに失敗しました: {e}") from e

    report_id = f"rep_{uuid.uuid4().hex}"
    created_at = _now_utc()
    report = _parse_report(
        markdown=markdown,
        report_id=report_id,
        psv_id=psv_id,
        prompt_snapshot=effective_prompt,
        created_at=created_at,
    )

    dynamodb.upsert_analyze_record(psv_id, effective_prompt)
    dynamodb.insert_report(report, user_id)

    return report
