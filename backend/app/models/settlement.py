from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timezone import business_now
from app.db.session import Base


class SettlementRecord(Base):
    __tablename__ = "settlement_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    settlement_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    batch_no: Mapped[str] = mapped_column(String(64), index=True)
    insured_id: Mapped[str] = mapped_column(String(32), index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reimbursed_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    self_pay_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=business_now)

    items: Mapped[list["SettlementItem"]] = relationship(back_populates="settlement", cascade="all, delete-orphan")


class SettlementItem(Base):
    __tablename__ = "settlement_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_no: Mapped[str] = mapped_column(String(64), ForeignKey("settlement_records.settlement_no", ondelete="CASCADE"), index=True)
    item_code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32))
    catalog_class: Mapped[str] = mapped_column(String(8))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    self_pay_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=business_now)

    settlement: Mapped["SettlementRecord"] = relationship(back_populates="items")
