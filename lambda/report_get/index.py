"""
@file index.py
@description GET /api/report/{reportId} のエントリポイント。
             レポート ID に対応するレポートを返す。

環境変数:
    ENV: 実行環境（dev / prod）
    TABLE_REPORT: kakeibo-report-{env}
"""
from __future__ import annotations

import logging

from shared.utils import response
from report_get import logic

_logger = logging.getLogger(__name__)


def handler(event: dict[str, object], _context: object) -> dict[str, object]:
    """
    Lambda ハンドラ。

    Args:
        event: API Gateway プロキシ統合イベント
        _context: Lambda コンテキスト（未使用）

    Returns:
        API Gateway プロキシ統合レスポンス
    """
    if event.get("httpMethod") == "OPTIONS":
        return response.options()

    path_params = event.get("pathParameters")
    if not isinstance(path_params, dict):
        path_params = {}
    report_id_raw = path_params.get("reportId")
    if not report_id_raw or not isinstance(report_id_raw, str):
        return response.error(400, "reportId は必須です")
    report_id = report_id_raw

    try:
        report = logic.get_report(report_id)
    except Exception:
        _logger.exception("レポート取得中に予期しないエラーが発生しました report_id=%s", report_id)
        return response.error(500, "レポートの取得に失敗しました")

    if report is None:
        return response.error(404, "指定されたレポートが見つかりません")

    return response.ok({
        "report": {
            "reportId": report.reportId,
            "psvId": report.psvId,
            "title": report.title,
            "summary": report.summary,
            "highlights": report.highlights,
            "promptSnapshot": report.promptSnapshot,
            "reportMarkdown": report.reportMarkdown,
            "createdAt": report.createdAt,
        }
    })
