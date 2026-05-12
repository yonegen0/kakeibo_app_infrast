"""
@file psv_encoder.py
@description MoneyForward CSV の解析と TransactionModel への変換を担当する。
             取り込み時のサニタイズ・エスケープ処理も含む。
"""
from __future__ import annotations

import csv
import io
import re
from typing import Optional

from shared.models.transaction import Amount, MfRow, TransactionModel, TransactionSource

_DATE_RE = re.compile(r"^(\d{4})/(\d{2})/(\d{2})$")
_AMOUNT_COMMA_RE = re.compile(r",")
_SANITIZE_RE = re.compile(r"[<>{}`]")
_WHITESPACE_RE = re.compile(r"\s+")

_MF_HEADER_FIELD = "計算対象"
_MAX_FIELD_LEN = 80


def _sanitize(value: str) -> str:
    """
    AI プロンプト注入防止のためテキストをサニタイズする。
    < > { } ` を除去し、連続空白を正規化する。

    Args:
        value: 対象文字列

    Returns:
        サニタイズ済み文字列（最大 80 文字）
    """
    cleaned = _SANITIZE_RE.sub("", value)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()[:_MAX_FIELD_LEN]


def _parse_date(raw: str) -> str:
    """
    YYYY/MM/DD → YYYY-MM-DD 変換。

    Args:
        raw: MoneyForward の日付文字列（YYYY/MM/DD 形式）

    Returns:
        ISO 形式日付文字列（YYYY-MM-DD）

    Raises:
        ValueError: 日付フォーマット不正
    """
    m = _DATE_RE.match(raw.strip())
    if not m:
        raise ValueError(f"不正な日付フォーマット: {raw!r}")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def _parse_amount(raw: str) -> float:
    """
    金額文字列（カンマ区切り）を float に変換する。

    Args:
        raw: 金額文字列（例: "-1,200"）

    Returns:
        金額の float 値

    Raises:
        ValueError: 数値変換失敗
    """
    return float(_AMOUNT_COMMA_RE.sub("", raw.strip()))


def parse_mf_csv(content: bytes) -> list[MfRow]:
    """
    MoneyForward 形式の CSV bytes をパースして MfRow リストを返す。
    Shift_JIS エンコーディングでデコードし、各フィールドをサニタイズする。

    Args:
        content: Shift_JIS エンコードされた CSV bytes

    Returns:
        MfRow のリスト

    Raises:
        ValueError: MoneyForward 形式のヘッダーが見つからない場合
    """
    text = content.decode("shift_jis", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None or _MF_HEADER_FIELD not in reader.fieldnames:
        raise ValueError(
            f"MoneyForward CSV のヘッダー '{_MF_HEADER_FIELD}' が見つかりません"
        )

    rows: list[MfRow] = []
    for row in reader:
        if not row.get("日付", "").strip():
            continue
        rows.append(
            MfRow(
                isCalculated=row.get("計算対象", "").strip() == "1",
                date=_parse_date(row.get("日付", "")),
                content=_sanitize(row.get("内容", "")),
                amount=_parse_amount(row.get("金額（円）", "0")),
                source=_sanitize(row.get("保有金融機関", "")),
                category=_sanitize(row.get("大項目", "")),
                subCategory=_sanitize(row.get("中項目", "")),
                memo=_sanitize(row.get("メモ", "")),
                isTransfer=row.get("振替", "").strip() == "1",
                mfId=row.get("ID", "").strip() or None,
            )
        )
    return rows


def mf_row_to_transaction(
    row: MfRow,
    file_name: str,
    index: int,
) -> TransactionModel:
    """
    MfRow を TransactionModel に変換する。

    Args:
        row: パース済み MfRow
        file_name: アップロードファイル名（ID 生成に使用）
        index: 行インデックス（ID 生成に使用）

    Returns:
        TransactionModel（isFixedCost は初期値 False）
    """
    return TransactionModel(
        id=f"{file_name}-{index}",
        date=row.date,
        amount=Amount(value=row.amount, unit="JPY"),
        content=row.content,
        category=row.category,
        subCategory=row.subCategory,
        isFixedCost=False,
        memo=row.memo,
        source=TransactionSource.MONEYFORWARD,
        isCalculated=row.isCalculated,
        isTransfer=row.isTransfer,
    )
