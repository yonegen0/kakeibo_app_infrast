"""
@file prompt_builder.py
@description AI 分析用プロンプトの構築を担当する純粋関数。
             TypeScript 版 analysisInput.ts の buildAnalysisPromptSnapshot() を移植。
"""
from __future__ import annotations

import json
import math
import re

from shared.models.summary import SummaryModel
from shared.models.transaction import TransactionModel
from shared.utils.prompts import ANALYSIS_REPORT_PROMPT

_MAX_PSV_ROWS = 40
_AMOUNT_THRESHOLD = 10_000
_SANITIZE_RE = re.compile(r"[<>{}`|]")
_PSV_DELIM = "|"
_PSV_HEADER = "date|amount|content|category|subCategory|memo"
_WHITESPACE_RE = re.compile(r"\s+")
_MAX_FIELD_LEN = 80


def _sanitize(value: str) -> str:
    """
    AI プロンプト注入防止のためテキストをサニタイズする。

    Args:
        value: 対象文字列

    Returns:
        サニタイズ済み文字列（最大 80 文字）
    """
    cleaned = _SANITIZE_RE.sub("", value)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()[:_MAX_FIELD_LEN]


def _pick_important_rows(transactions: list[TransactionModel]) -> list[TransactionModel]:
    """
    高額取引・固定費を優先して最大 40 件を選択する。

    Args:
        transactions: 取引明細リスト

    Returns:
        優先度順に選択された取引明細リスト（最大 _MAX_PSV_ROWS 件）
    """
    sorted_txs = sorted(transactions, key=lambda t: abs(t.amount.value), reverse=True)
    high_amount = [t for t in sorted_txs if abs(t.amount.value) >= _AMOUNT_THRESHOLD]
    fixed_costs = [t for t in sorted_txs if t.isFixedCost]
    merged = high_amount + fixed_costs + sorted_txs

    seen: dict[str, TransactionModel] = {}
    for t in merged:
        if t.id not in seen:
            seen[t.id] = t
        if len(seen) >= _MAX_PSV_ROWS:
            break
    return list(seen.values())


def _encode_transactions_psv(transactions: list[TransactionModel]) -> str:
    """
    取引リストを PSV 文字列に変換する。

    Args:
        transactions: 取引明細リスト

    Returns:
        ヘッダー行 + データ行を改行結合した PSV 文字列
    """
    lines = [_PSV_HEADER]
    for t in transactions:
        lines.append(_PSV_DELIM.join([
            t.date,
            str(t.amount.value),
            _sanitize(t.content),
            _sanitize(t.category),
            _sanitize(t.subCategory),
            _sanitize(t.memo),
        ]))
    return "\n".join(lines)


def build_analysis_prompt(
    summary: SummaryModel,
    transactions: list[TransactionModel],
) -> str:
    """
    AI 分析用プロンプトを生成する。

    サマリーを JSON、取引明細を PSV でそれぞれ埋め込み、
    ANALYSIS_REPORT_PROMPT の後に付与する。

    Args:
        summary: 月次サマリー
        transactions: 取引明細リスト（ペイロード行の選択元）

    Returns:
        Bedrock に送信するプロンプト文字列
    """
    summary_payload = {
        "month": summary.month,
        "incomeTotal": summary.incomeTotal.value,
        "expenseTotal": summary.expenseTotal.value,
        "balance": summary.balance.value,
        "topCategories": [
            {
                "name": c.name,
                "amount": c.amount.value,
                "percentage": math.floor(c.percentage * 100) / 100,
                "kind": c.kind.value,
            }
            for c in summary.categories[:5]
        ],
        "topExpenses": [
            {
                "content": e.content,
                "amount": e.amount.value,
                "category": e.category,
                "date": e.date,
            }
            for e in summary.topExpenses[:5]
        ],
    }

    extraction_rule = {
        "maxRowsTotal": _MAX_PSV_ROWS,
        "amountThreshold": _AMOUNT_THRESHOLD,
        "sanitize": "strip < > { } ` | and collapse whitespace",
        "split": "isFixedCost によって fixedCostPsvRows と variablePsvRows に分割済み",
    }

    selected = _pick_important_rows(transactions)
    fixed_txs    = [t for t in selected if t.isFixedCost]
    variable_txs = [t for t in selected if not t.isFixedCost]

    fixed_psv    = _encode_transactions_psv(fixed_txs)
    variable_psv = _encode_transactions_psv(variable_txs)

    return (
        f"{ANALYSIS_REPORT_PROMPT}\n\n"
        f"# 解析入力\n\n"
        f"## summary (JSON)\n"
        f"{json.dumps(summary_payload, ensure_ascii=False, indent=2)}\n\n"
        f"## fixedCostPsvRows (固定費取引 / PSV / 区切り文字: パイプ)\n"
        f"{fixed_psv}\n\n"
        f"## variablePsvRows (変動費取引 / PSV / 区切り文字: パイプ)\n"
        f"{variable_psv}\n\n"
        f"## extractionRule (JSON)\n"
        f"{json.dumps(extraction_rule, ensure_ascii=False)}"
    )
