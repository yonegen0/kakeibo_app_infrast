"""
@file index.py
@description POST /api/psv のエントリポイント。
             取引一覧を PSV として保存し、psvId とメタデータを返す。

環境変数:
    ENV: 実行環境（dev / prod）
    TABLE_PSV: kakeibo-psv-{env}
    RAW_BUCKET: kakeibo-raw-data-{env}
"""
from __future__ import annotations

import json
import logging

from shared.utils import response
from psv_create import logic

_logger = logging.getLogger(__name__)


def handler(event: dict[str, object], _context: object) -> dict[str, object]:
    """
    Lambda ハンドラ。バリデーションとレスポンス整形のみを担当する。

    Args:
        event: API Gateway プロキシ統合イベント
        _context: Lambda コンテキスト（未使用）

    Returns:
        API Gateway プロキシ統合レスポンス
    """
    if event.get("httpMethod") == "OPTIONS":
        return response.options()

    try:
        body: dict[str, object] = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return response.error(400, "リクエストボディが不正な JSON です")

    raw_transactions = body.get("transactions")
    if not isinstance(raw_transactions, list) or not raw_transactions:
        return response.error(400, "transactions は必須です")
    if not all(isinstance(tx, dict) for tx in raw_transactions):
        return response.error(400, "transactions の各要素はオブジェクト形式である必要があります")

    user_id_raw = body.get("userId")
    user_id = str(user_id_raw).strip() if isinstance(user_id_raw, str) and user_id_raw.strip() else "demo-user"

    file_name_raw = body.get("fileName")
    file_name = str(file_name_raw).strip() if isinstance(file_name_raw, str) and file_name_raw.strip() else "uploaded.csv"

    try:
        psv_id, meta = logic.create_psv(
            user_id=user_id,
            file_name=file_name,
            raw_transactions=raw_transactions,
        )
    except ValueError as e:
        return response.error(400, str(e))
    except Exception:
        _logger.exception("PSV 保存中に予期しないエラーが発生しました user_id=%s", user_id)
        return response.error(500, "PSV の保存に失敗しました")

    return response.ok({
        "psvId": psv_id,
        "meta": {
            "psvId": meta.psvId,
            "userId": meta.userId,
            "fileName": meta.fileName,
            "rowCount": meta.rowCount,
            "monthRange": meta.monthRange.to_dict(),
            "createdAt": meta.createdAt,
            "updatedAt": meta.updatedAt,
            "isLatest": meta.isLatest,
        },
    })
