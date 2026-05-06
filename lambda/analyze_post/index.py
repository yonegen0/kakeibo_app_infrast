"""
@file index.py
@description POST /api/analyze/{psvId} のエントリポイント。
             PSV を AI 分析しレポートを生成して返す。

環境変数:
    ENV: 実行環境（dev / prod）
    TABLE_PSV: kakeibo-psv-{env}（設計ギャップ: 追加が必要）
    TABLE_SUMMARY: kakeibo-summary-{env}（設計ギャップ: 追加が必要）
    TABLE_ANALYZE: kakeibo-analyze-{env}
    TABLE_REPORT: kakeibo-report-{env}（設計ギャップ: 追加が必要）
    BEDROCK_MODEL_ID: 使用する Bedrock モデル ID（省略時はデフォルト値）
"""
from __future__ import annotations

import json
import logging
import os

from shared.utils import response
from analyze_post import logic

_ENV = os.environ.get("ENV", "dev")
_logger = logging.getLogger(__name__)


def _resolve_user_id(event: dict[str, object]) -> str:
    """
    リクエストからユーザー ID を解決する。
    prod 環境は Cognito JWT の sub クレームを使用し、dev 環境はデフォルト値を返す。

    Args:
        event: API Gateway プロキシ統合イベント

    Returns:
        ユーザー ID 文字列
    """
    if _ENV != "prod":
        return "demo-user"
    ctx = event.get("requestContext")
    if not isinstance(ctx, dict):
        return "demo-user"
    authorizer = ctx.get("authorizer")
    if not isinstance(authorizer, dict):
        return "demo-user"
    claims = authorizer.get("claims")
    if not isinstance(claims, dict):
        return "demo-user"
    user_id = claims.get("sub")
    return str(user_id) if user_id else "demo-user"


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
        body: dict[str, object] = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        body = {}

    prompt_override_raw = body.get("promptOverride")
    prompt_override = str(prompt_override_raw).strip() if isinstance(prompt_override_raw, str) else None
    if prompt_override == "":
        prompt_override = None

    user_id = _resolve_user_id(event)

    try:
        report = logic.analyze_and_create_report(
            psv_id=psv_id,
            user_id=user_id,
            prompt_override=prompt_override,
        )
    except ValueError as e:
        return response.error(422, str(e))
    except RuntimeError as e:
        _logger.error("Bedrock 呼び出しエラー psv_id=%s: %s", psv_id, e)
        return response.error(500, "AI 分析に失敗しました")
    except Exception:
        _logger.exception("AI 分析中に予期しないエラーが発生しました psv_id=%s", psv_id)
        return response.error(500, "AI 分析に失敗しました")

    if report is None:
        return response.error(404, "指定された PSV が見つかりません")

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
