from datetime import datetime, date
from typing import List, TYPE_CHECKING
from sqlalchemy import Date, DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base, utc_now

if TYPE_CHECKING:
    from models.transaction import Transaction


class DailyClosure(Base):
    """
    Entidad de Cierres Diarios (SQL Server: dbo.CierresDiarios).
    Consolida arqueo de caja y desgloses analíticos en JSON por categoría, membresía y carril.
    """
    __tablename__ = "daily_closures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    closure_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    closed_by: Mapped[str] = mapped_column(String(100), default="Supervisor General", nullable=False)
    total_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_cash: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_card: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_discounts_granted: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Desgloses analíticos estructurados (compatibles con NVARCHAR(MAX) JSON en SQL Server)
    breakdown_by_category: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    breakdown_by_membership: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    breakdown_by_lane: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relación con transacciones
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="daily_closure")
