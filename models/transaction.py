from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base, PaymentMethod, VehicleCategory, utc_now
from models.daily_closure import DailyClosure
from models.lane import Lane
from models.membership import Membership
from models.vehicle import Vehicle


class Transaction(Base):
    """
    Entidad de Transacciones de Peaje (SQL Server: dbo.Transacciones).
    Registra cobros físicos en caseta y los eventos generados por la simulación DES.
    """
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    receipt_code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    vehicle_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True
    )
    lane_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lanes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    membership_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("memberships.id", ondelete="SET NULL"), nullable=True, index=True
    )
    daily_closure_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("daily_closures.id", ondelete="SET NULL"), nullable=True, index=True
    )

    plate: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    vehicle_category: Mapped[VehicleCategory] = mapped_column(Enum(VehicleCategory), nullable=False, index=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False, index=True)

    has_active_membership: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    regular_amount: Mapped[float] = mapped_column(Float, nullable=False)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    amount_charged: Mapped[float] = mapped_column(Float, nullable=False)

    wait_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    service_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    # Relaciones
    vehicle: Mapped[Optional["Vehicle"]] = relationship("Vehicle", back_populates="transactions")
    lane: Mapped["Lane"] = relationship("Lane", back_populates="transactions")
    membership: Mapped[Optional["Membership"]] = relationship("Membership", back_populates="transactions")
    daily_closure: Mapped[Optional["DailyClosure"]] = relationship("DailyClosure", back_populates="transactions")
