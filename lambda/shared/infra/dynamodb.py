"""
@file dynamodb.py
@description DynamoDB PartiQL を使用したデータアクセス層。
             PSV・サマリー・分析・レポートの読み書きを
             ExecuteStatement / BatchExecuteStatement で担当する。
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

from shared.models.psv import MonthRange, PsvFullData, PsvMetaModel
from shared.models.report import AIReportModel
from shared.models.summary import (
    CategoryKind,
    DailyTrend,
    FixedCostItem,
    SummaryCategory,
    SummaryModel,
    TopExpense,
)
from shared.models.transaction import Amount, TransactionModel, TransactionSource

_client = boto3.client(
    "dynamodb",
    region_name=os.environ.get("AWS_REGION", "ap-northeast-1"),
)
_deser = TypeDeserializer()
_ser = TypeSerializer()

TABLE_PSV: str = os.environ.get("TABLE_PSV", "kakeibo-psv-dev")
TABLE_SUMMARY: str = os.environ.get("TABLE_SUMMARY", "kakeibo-summary-dev")
TABLE_ANALYZE: str = os.environ.get("TABLE_ANALYZE", "kakeibo-analyze-dev")
TABLE_REPORT: str = os.environ.get("TABLE_REPORT", "kakeibo-report-dev")
# INDEX は psv_latest / reports_list のみ使用。それ以外では参照しない
_INDEX_USER_CREATED: str = os.environ.get("INDEX", "userId-createdAt-index")
_INDEX_PSV = "psvId-index"

_BATCH_SIZE = 25  # batch_execute_statement の上限


# ─────────────────────────── 内部ヘルパー ───────────────────────────


def _now_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _d(raw: dict) -> dict[str, object]:
    """DynamoDB 型付き JSON → Python dict 変換"""
    return {k: _deser.deserialize(v) for k, v in raw.items()}


def _to_float(v: object) -> float:
    return float(v)  # type: ignore[arg-type]


def _to_decimal(v: object) -> object:
    """dict/list を再帰的に walk し、float を Decimal に変換する。str 経由で精度を保つ。"""
    if isinstance(v, float):
        return Decimal(str(v))
    if isinstance(v, dict):
        return {k: _to_decimal(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_to_decimal(x) for x in v]
    return v


def _insert(table: str, item: dict[str, object]) -> None:
    """PartiQL INSERT ヘルパー。item のキー順に ? プレースホルダーを並べて実行する。"""
    keys = list(item.keys())
    placeholders = ", ".join(f"'{k}': ?" for k in keys)
    safe = {k: _to_decimal(item[k]) for k in keys}
    params = [_ser.serialize(safe[k]) for k in keys]
    _client.execute_statement(
        Statement=f'INSERT INTO "{table}" VALUE {{{placeholders}}}',
        Parameters=params,
    )


def _delete_by_pk(table: str, pk_name: str, pk_value: str) -> None:
    """PartiQL DELETE ヘルパー（単一 PK）"""
    _client.execute_statement(
        Statement=f'DELETE FROM "{table}" WHERE "{pk_name}" = ?',
        Parameters=[{"S": pk_value}],
    )


def _select_one(table: str, pk_name: str, pk_value: str) -> Optional[dict[str, object]]:
    """PK 一致する単一アイテムを取得する。存在しない場合は None を返す。"""
    res = _client.execute_statement(
        Statement=f'SELECT * FROM "{table}" WHERE "{pk_name}" = ?',
        Parameters=[{"S": pk_value}],
    )
    items = res.get("Items", [])
    return _d(items[0]) if items else None


def _upsert(table: str, pk_name: str, pk_value: str, item: dict[str, object]) -> None:
    """PartiQL で upsert を行う（DELETE → INSERT）。"""
    _delete_by_pk(table, pk_name, pk_value)
    _insert(table, item)


# ─────────────────────────── モデル変換 ───────────────────────────


def _tx_to_dict(tx: TransactionModel) -> dict[str, object]:
    return {
        "id": tx.id,
        "date": tx.date,
        "amountValue": tx.amount.value,
        "amountUnit": tx.amount.unit,
        "content": tx.content,
        "category": tx.category,
        "subCategory": tx.subCategory,
        "isFixedCost": tx.isFixedCost,
        "memo": tx.memo,
        "source": tx.source.value,
        "isCalculated": tx.isCalculated,
        "isTransfer": tx.isTransfer,
    }


def _dict_to_tx(d: dict[str, object]) -> TransactionModel:
    return TransactionModel(
        id=str(d["id"]),
        date=str(d["date"]),
        amount=Amount(
            value=_to_float(d["amountValue"]),
            unit=str(d["amountUnit"]),
        ),
        content=str(d["content"]),
        category=str(d["category"]),
        subCategory=str(d["subCategory"]),
        isFixedCost=bool(d["isFixedCost"]),
        memo=str(d.get("memo", "")),
        source=TransactionSource(str(d["source"])),
        isCalculated=bool(d.get("isCalculated", True)),
        isTransfer=bool(d.get("isTransfer", False)),
    )


def _item_to_meta(d: dict[str, object]) -> PsvMetaModel:
    mr = d["monthRange"]
    if not isinstance(mr, dict):
        raise ValueError(f"monthRange の型が不正です: {type(mr)}")
    return PsvMetaModel(
        psvId=str(d["psvId"]),
        userId=str(d["userId"]),
        fileName=str(d["fileName"]),
        rowCount=int(_to_float(d["rowCount"])),
        monthRange=MonthRange(
            from_month=str(mr.get("from", "")),
            to=str(mr.get("to", "")),
        ),
        createdAt=str(d["createdAt"]),
        updatedAt=str(d["updatedAt"]),
        isLatest=bool(d["isLatest"]),
    )


def _cat_to_dict(c: SummaryCategory) -> dict[str, object]:
    return {"name": c.name, "amount": c.amount.value, "percentage": c.percentage, "kind": c.kind.value}


def _dict_to_cat(d: dict[str, object]) -> SummaryCategory:
    return SummaryCategory(
        name=str(d["name"]),
        amount=Amount(value=_to_float(d["amount"]), unit="JPY"),
        percentage=_to_float(d["percentage"]),
        kind=CategoryKind(str(d["kind"])),
    )


def _trend_to_dict(t: DailyTrend) -> dict[str, object]:
    return {"date": t.date, "income": t.income.value, "expense": t.expense.value, "balance": t.balance.value}


def _dict_to_trend(d: dict[str, object]) -> DailyTrend:
    return DailyTrend(
        date=str(d["date"]),
        income=Amount(value=_to_float(d["income"]), unit="JPY"),
        expense=Amount(value=_to_float(d["expense"]), unit="JPY"),
        balance=Amount(value=_to_float(d["balance"]), unit="JPY"),
    )


def _top_to_dict(e: TopExpense) -> dict[str, object]:
    return {"id": e.id, "content": e.content, "amount": e.amount.value, "category": e.category, "date": e.date}


def _dict_to_top(d: dict[str, object]) -> TopExpense:
    return TopExpense(
        id=str(d["id"]),
        content=str(d["content"]),
        amount=Amount(value=_to_float(d["amount"]), unit="JPY"),
        category=str(d["category"]),
        date=str(d["date"]),
    )


def _fixed_to_dict(f: FixedCostItem) -> dict[str, object]:
    return {"id": f.id, "content": f.content, "amount": f.amount.value, "category": f.category}


def _dict_to_fixed(d: dict[str, object]) -> FixedCostItem:
    return FixedCostItem(
        id=str(d["id"]),
        content=str(d["content"]),
        amount=Amount(value=_to_float(d["amount"]), unit="JPY"),
        category=str(d["category"]),
    )


def _item_to_summary(d: dict[str, object]) -> SummaryModel:
    return SummaryModel(
        month=str(d["month"]),
        incomeTotal=Amount(value=_to_float(d["incomeTotal"]), unit="JPY"),
        expenseTotal=Amount(value=_to_float(d["expenseTotal"]), unit="JPY"),
        balance=Amount(value=_to_float(d["balance"]), unit="JPY"),
        categories=[_dict_to_cat(c) for c in d.get("categories", []) if isinstance(c, dict)],  # type: ignore[union-attr]
        dailyTrend=[_dict_to_trend(t) for t in d.get("dailyTrend", []) if isinstance(t, dict)],  # type: ignore[union-attr]
        topExpenses=[_dict_to_top(e) for e in d.get("topExpenses", []) if isinstance(e, dict)],  # type: ignore[union-attr]
        fixedCosts=[_dict_to_fixed(f) for f in d.get("fixedCosts", []) if isinstance(f, dict)],  # type: ignore[union-attr]
    )


def _item_to_report(d: dict[str, object]) -> AIReportModel:
    return AIReportModel(
        reportId=str(d["reportId"]),
        psvId=str(d["psvId"]),
        title=str(d["title"]),
        summary=str(d["summary"]),
        highlights=[str(h) for h in d.get("highlights", []) if isinstance(h, str)],  # type: ignore[union-attr]
        promptSnapshot=str(d["promptSnapshot"]),
        reportMarkdown=str(d["reportMarkdown"]),
        createdAt=str(d["createdAt"]),
    )


# ─────────────────────────── PSV ───────────────────────────


def insert_psv(meta: PsvMetaModel, transactions: list[TransactionModel]) -> None:
    """
    PSV メタデータと取引一覧を DynamoDB に保存する。

    Args:
        meta: PSV メタデータ
        transactions: 取引明細リスト
    """
    item: dict[str, object] = {
        "psvId": meta.psvId,
        "userId": meta.userId,
        "fileName": meta.fileName,
        "rowCount": meta.rowCount,
        "monthRange": {"from": meta.monthRange.from_month, "to": meta.monthRange.to},
        "createdAt": meta.createdAt,
        "updatedAt": meta.updatedAt,
        "isLatest": meta.isLatest,
        "transactions": [_tx_to_dict(tx) for tx in transactions],
    }
    _insert(TABLE_PSV, item)


def update_all_not_latest(exclude_id: str) -> None:
    """
    指定 PSV 以外の isLatest フラグをすべて False に更新する。
    新規 PSV 作成時に既存レコードの最新フラグを解除するために使用する。

    Args:
        exclude_id: 除外する PSV ID（新規作成対象）
    """
    res = _client.execute_statement(
        Statement=f'SELECT "psvId" FROM "{TABLE_PSV}" WHERE "isLatest" = ?',
        Parameters=[{"BOOL": True}],
    )
    psv_ids = [
        str(_deser.deserialize(item["psvId"]))
        for item in res.get("Items", [])
        if str(_deser.deserialize(item["psvId"])) != exclude_id
    ]
    if not psv_ids:
        return

    statements = [
        {
            "Statement": f'UPDATE "{TABLE_PSV}" SET "isLatest" = ? WHERE "psvId" = ?',
            "Parameters": [{"BOOL": False}, {"S": pid}],
        }
        for pid in psv_ids
    ]
    for i in range(0, len(statements), _BATCH_SIZE):
        _client.batch_execute_statement(Statements=statements[i : i + _BATCH_SIZE])


def get_psv_full(psv_id: str) -> Optional[PsvFullData]:
    """
    PSV の完全データ（メタ・取引一覧）を取得する。

    Args:
        psv_id: 対象 PSV ID

    Returns:
        PsvFullData。存在しない場合は None
    """
    item = _select_one(TABLE_PSV, "psvId", psv_id)
    if item is None:
        return None
    meta = _item_to_meta(item)
    transactions = [
        _dict_to_tx(t)
        for t in item.get("transactions", [])  # type: ignore[union-attr]
        if isinstance(t, dict)
    ]
    return PsvFullData(meta=meta, transactions=transactions)


def get_latest_psv_meta(user_id: str) -> Optional[PsvMetaModel]:
    """
    指定ユーザーの最新 PSV メタデータを取得する。
    userId-createdAt-index GSI を使用し、isLatest=True のアイテムを返す。

    Args:
        user_id: ユーザー ID

    Returns:
        PsvMetaModel。存在しない場合は None
    """
    res = _client.execute_statement(
        Statement=(
            f'SELECT * FROM "{TABLE_PSV}"."{_INDEX_USER_CREATED}" '
            f'WHERE "userId" = ? AND "isLatest" = ?'
        ),
        Parameters=[{"S": user_id}, {"BOOL": True}],
    )
    items = res.get("Items", [])
    if not items:
        return None
    return _item_to_meta(_d(items[0]))


# ─────────────────────────── Summary ───────────────────────────


def upsert_summary(psv_id: str, summary: SummaryModel) -> None:
    """
    サマリーを kakeibo-summary テーブルに保存する（存在する場合は上書き）。

    Args:
        psv_id: 対象 PSV ID
        summary: 保存する SummaryModel
    """
    item: dict[str, object] = {
        "psvId": psv_id,
        "month": summary.month,
        "incomeTotal": summary.incomeTotal.value,
        "expenseTotal": summary.expenseTotal.value,
        "balance": summary.balance.value,
        "categories": [_cat_to_dict(c) for c in summary.categories],
        "dailyTrend": [_trend_to_dict(t) for t in summary.dailyTrend],
        "topExpenses": [_top_to_dict(e) for e in summary.topExpenses],
        "fixedCosts": [_fixed_to_dict(f) for f in summary.fixedCosts],
    }
    _upsert(TABLE_SUMMARY, "psvId", psv_id, item)


def get_summary(psv_id: str) -> Optional[SummaryModel]:
    """
    指定 PSV のサマリーを取得する。

    Args:
        psv_id: 対象 PSV ID

    Returns:
        SummaryModel。存在しない場合は None
    """
    item = _select_one(TABLE_SUMMARY, "psvId", psv_id)
    return _item_to_summary(item) if item else None


# ─────────────────────────── Analyze ───────────────────────────


def upsert_analyze_record(psv_id: str, prompt_snapshot: str) -> None:
    """
    分析プロンプトのスナップショットを analyze テーブルに保存する。

    Args:
        psv_id: 対象 PSV ID
        prompt_snapshot: 送信したプロンプト全文
    """
    item: dict[str, object] = {
        "psvId": psv_id,
        "promptSnapshot": prompt_snapshot,
        "updatedAt": _now_utc(),
    }
    _upsert(TABLE_ANALYZE, "psvId", psv_id, item)


def get_analyze_record(psv_id: str) -> Optional[str]:
    """
    保存済みの分析プロンプトを取得する。

    Args:
        psv_id: 対象 PSV ID

    Returns:
        プロンプト文字列。存在しない場合は None
    """
    item = _select_one(TABLE_ANALYZE, "psvId", psv_id)
    if item is None:
        return None
    return str(item.get("promptSnapshot", "")) or None


# ─────────────────────────── Report ───────────────────────────


def insert_report(report: AIReportModel, user_id: str) -> None:
    """
    AI レポートを report テーブルに保存する。
    userId は userId-createdAt-index GSI のために保存するが、レスポンスには含めない。

    Args:
        report: 保存する AIReportModel
        user_id: ユーザー ID（GSI 用）
    """
    item: dict[str, object] = {
        "reportId": report.reportId,
        "psvId": report.psvId,
        "userId": user_id,
        "title": report.title,
        "summary": report.summary,
        "highlights": report.highlights,
        "promptSnapshot": report.promptSnapshot,
        "reportMarkdown": report.reportMarkdown,
        "createdAt": report.createdAt,
    }
    _insert(TABLE_REPORT, item)


def get_report(report_id: str) -> Optional[AIReportModel]:
    """
    レポート ID からレポートを取得する。

    Args:
        report_id: 取得対象のレポート ID

    Returns:
        AIReportModel。存在しない場合は None
    """
    item = _select_one(TABLE_REPORT, "reportId", report_id)
    return _item_to_report(item) if item else None


def list_reports_by_psv(psv_id: str) -> list[AIReportModel]:
    """
    指定 PSV のレポート一覧を取得する（psvId-index GSI を使用）。

    Args:
        psv_id: 対象 PSV ID

    Returns:
        AIReportModel のリスト（createdAt 降順）
    """
    res = _client.execute_statement(
        Statement=(
            f'SELECT * FROM "{TABLE_REPORT}"."{_INDEX_PSV}" '
            f'WHERE "psvId" = ?'
        ),
        Parameters=[{"S": psv_id}],
    )
    reports = [_item_to_report(_d(item)) for item in res.get("Items", [])]
    reports.sort(key=lambda r: r.createdAt, reverse=True)
    return reports


def list_reports_by_user(user_id: str) -> list[AIReportModel]:
    """
    指定ユーザーのレポート一覧を取得する（userId-createdAt-index GSI を使用）。

    Args:
        user_id: ユーザー ID

    Returns:
        AIReportModel のリスト（createdAt 降順）
    """
    res = _client.execute_statement(
        Statement=(
            f'SELECT * FROM "{TABLE_REPORT}"."{_INDEX_USER_CREATED}" '
            f'WHERE "userId" = ?'
        ),
        Parameters=[{"S": user_id}],
    )
    reports = [_item_to_report(_d(item)) for item in res.get("Items", [])]
    reports.sort(key=lambda r: r.createdAt, reverse=True)
    return reports
