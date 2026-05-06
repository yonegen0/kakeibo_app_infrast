"""
@file index.py
@description GET /api/analyze/{psvId} のエントリポイント。
             分析用デフォルトプロンプトを返す。

環境変数:
    ENV: 実行環境（dev / prod）
    TABLE_ANALYZE: kakeibo-analyze-{env}
    TABLE_PSV: kakeibo-psv-{env}（設計ギャップ: 追加が必要）
    TABLE_SUMMARY: kakeibo-summary-{env}（設計ギャップ: 追加が必要）
"""
from __future__ import annotations

import logging

from shared.utils import response
from analyze_get import logic

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
    psv_id_raw = path_params.get("psvId")
    if not psv_id_raw or not isinstance(psv_id_raw, str):
        return response.error(400, "psvId は必須です")
    psv_id = psv_id_raw

    try:
        prompt = logic.get_analyze_prompt(psv_id)
    except ValueError as e:
        return response.error(422, str(e))
    except Exception:
        _logger.exception("プロンプト取得中に予期しないエラーが発生しました psv_id=%s", psv_id)
        return response.error(500, "プロンプトの取得に失敗しました")

    if prompt is None:
        return response.error(404, "指定された PSV が見つかりません")

    return response.ok({"prompt": prompt})
