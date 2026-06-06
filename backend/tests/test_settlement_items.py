from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.settlement import SettlementRecord, SettlementItem
from app.services.reconciliation_service import daily_summary
from app.services.settlement_service import pre_settle, confirm_settlement, reverse_settlement, query_settlements
from app.schemas.settlement import PreSettlementRequest, ExpenseItem, SettlementConfirmRequest


TEST_ITEMS = [
    {
        "item_code": "DRUG001",
        "name": "阿莫西林胶囊",
        "category": "西药",
        "catalog_class": "甲类",
        "unit_price": "15.50",
        "quantity": "2",
        "amount": "31.00",
        "self_pay_ratio": "0.00"
    },
    {
        "item_code": "EXAM001",
        "name": "血常规检查",
        "category": "诊疗",
        "catalog_class": "乙类",
        "unit_price": "35.00",
        "quantity": "1",
        "amount": "35.00",
        "self_pay_ratio": "0.10"
    },
    {
        "item_code": "DRUG002",
        "name": "感冒灵颗粒",
        "category": "中成药",
        "catalog_class": "丙类",
        "unit_price": "28.00",
        "quantity": "3",
        "amount": "84.00",
        "self_pay_ratio": "1.00"
    }
]


def _build_pre_settle_request():
    return PreSettlementRequest(
        insured_id="INS001",
        region="北京市",
        items=[ExpenseItem(**item) for item in TEST_ITEMS]
    )


def test_confirm_settlement_saves_items(db_session: Session):
    principal = {"sub": "test_client", "scopes": ["*/*"]}

    pre_request = _build_pre_settle_request()
    pre_result = pre_settle(pre_request, principal)

    confirm_request = SettlementConfirmRequest(
        batch_no="BATCH001",
        insured_id="INS001",
        pre_settlement=pre_result
    )
    settle_result = confirm_settlement(confirm_request, db_session, principal)

    settlement_no = settle_result.settlement_no

    saved_items = db_session.scalars(
        select(SettlementItem).where(SettlementItem.settlement_no == settlement_no)
    ).all()

    assert len(saved_items) == 3, "结算明细数量应等于传入的费用项数量"

    item_codes = {item.item_code for item in saved_items}
    expected_codes = {item["item_code"] for item in TEST_ITEMS}
    assert item_codes == expected_codes, "所有费用项目编码都应被保存"

    drug1 = next(i for i in saved_items if i.item_code == "DRUG001")
    assert drug1.name == "阿莫西林胶囊"
    assert drug1.category == "西药"
    assert drug1.catalog_class == "甲类"
    assert drug1.unit_price == Decimal("15.50")
    assert drug1.quantity == Decimal("2")
    assert drug1.amount == Decimal("31.00")
    assert drug1.self_pay_ratio == Decimal("0.00")

    total_items_amount = sum((i.amount for i in saved_items), Decimal("0.00"))
    assert total_items_amount == pre_result.total_amount, "明细金额合计应等于结算单总金额"

    item_count = db_session.scalar(
        select(func.count(SettlementItem.id)).where(SettlementItem.settlement_no == settlement_no)
    )
    assert item_count == 3


def test_query_settlement_returns_complete_items(db_session: Session):
    principal = {"sub": "test_client", "scopes": ["*/*"]}

    pre_request = _build_pre_settle_request()
    pre_result = pre_settle(pre_request, principal)

    confirm_request = SettlementConfirmRequest(
        batch_no="BATCH002",
        insured_id="INS001",
        pre_settlement=pre_result
    )
    settled = confirm_settlement(confirm_request, db_session, principal)
    settlement_no = settled.settlement_no

    results = query_settlements(db_session, principal, settlement_no=settlement_no, insured_id=None, start=None, end=None)

    assert len(results) == 1
    record = results[0]

    assert record.settlement_no == settlement_no
    assert record.items is not None, "查询结果应包含明细项"
    assert len(record.items) == 3, "明细项数量应为3"

    returned_codes = {item.item_code for item in record.items}
    expected_codes = {item["item_code"] for item in TEST_ITEMS}
    assert returned_codes == expected_codes

    drug2 = next(i for i in record.items if i.item_code == "DRUG002")
    assert drug2.name == "感冒灵颗粒"
    assert drug2.category == "中成药"
    assert drug2.catalog_class == "丙类"
    assert drug2.unit_price == Decimal("28.00")
    assert drug2.quantity == Decimal("3")
    assert drug2.amount == Decimal("84.00")
    assert drug2.self_pay_ratio == Decimal("1.00")

    assert record.total_amount == pre_result.total_amount
    assert record.reimbursed_amount == pre_result.reimbursed_amount
    assert record.self_pay_amount == pre_result.self_pay_amount


def test_reverse_settlement_preserves_items(db_session: Session):
    principal = {"sub": "test_client", "scopes": ["*/*"]}

    pre_request = _build_pre_settle_request()
    pre_result = pre_settle(pre_request, principal)

    confirm_request = SettlementConfirmRequest(
        batch_no="BATCH003",
        insured_id="INS001",
        pre_settlement=pre_result
    )
    settled = confirm_settlement(confirm_request, db_session, principal)
    settlement_no = settled.settlement_no

    reversed_result = reverse_settlement(settlement_no, db_session, principal)

    assert reversed_result.status == "REVERSED", "冲正后状态应为REVERSED"
    assert reversed_result.settlement_no == settlement_no
    assert reversed_result.items is not None, "冲正后明细项应保留"
    assert len(reversed_result.items) == 3, "冲正后明细项数量不应改变"

    record = db_session.scalar(
        select(SettlementRecord).where(SettlementRecord.settlement_no == settlement_no)
    )
    assert record.status == "REVERSED"

    item_count = db_session.scalar(
        select(func.count(SettlementItem.id)).where(SettlementItem.settlement_no == settlement_no)
    )
    assert item_count == 3, "冲正后明细记录不应被删除"

    drug1 = db_session.scalar(
        select(SettlementItem).where(
            SettlementItem.settlement_no == settlement_no,
            SettlementItem.item_code == "DRUG001"
        )
    )
    assert drug1 is not None
    assert drug1.amount == Decimal("31.00")

    query_results = query_settlements(db_session, principal, settlement_no=settlement_no, insured_id=None, start=None, end=None)
    assert len(query_results) == 1
    assert query_results[0].status == "REVERSED"
    assert query_results[0].items is not None
    assert len(query_results[0].items) == 3


def test_daily_reconciliation_unaffected_by_items_table(db_session: Session):
    principal = {"sub": "test_client", "scopes": ["*/*"]}

    pre_request_1 = _build_pre_settle_request()
    pre_result_1 = pre_settle(pre_request_1, principal)

    confirm_request_1 = SettlementConfirmRequest(
        batch_no="BATCH004",
        insured_id="INS001",
        pre_settlement=pre_result_1
    )
    confirm_settlement(confirm_request_1, db_session, principal)

    items_2 = [TEST_ITEMS[0], TEST_ITEMS[1]]
    pre_request_2 = PreSettlementRequest(
        insured_id="INS002",
        region="上海市",
        items=[ExpenseItem(**item) for item in items_2]
    )
    pre_result_2 = pre_settle(pre_request_2, principal)

    confirm_request_2 = SettlementConfirmRequest(
        batch_no="BATCH005",
        insured_id="INS002",
        pre_settlement=pre_result_2
    )
    confirm_settlement(confirm_request_2, db_session, principal)

    from datetime import date, datetime
    today = date.today()

    result = daily_summary(today, db_session, principal)

    expected_total = pre_result_1.total_amount + pre_result_2.total_amount
    assert result["total_count"] == 2
    assert result["success_count"] == 2
    assert result["failed_count"] == 0
    assert result["total_amount"] == str(expected_total.quantize(Decimal("0.00")))

    settlement_count = db_session.scalar(select(func.count(SettlementRecord.id)))
    item_count = db_session.scalar(select(func.count(SettlementItem.id)))
    assert settlement_count == 2
    assert item_count == 5

    settlement_amounts = db_session.scalars(select(SettlementRecord.total_amount)).all()
    direct_total = sum(settlement_amounts, Decimal("0.00"))
    assert str(direct_total.quantize(Decimal("0.00"))) == result["total_amount"]

    item_amounts = db_session.scalars(select(SettlementItem.amount)).all()
    items_total = sum(item_amounts, Decimal("0.00"))
    assert items_total == direct_total, "明细表金额合计应等于结算表金额合计"

    result_items_only = db_session.scalars(
        select(SettlementItem)
    ).all()
    assert len(result_items_only) == 5
