from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base, VehicleCategory, utc_now

if TYPE_CHECKING:
    from models.membership import Membership
    from models.transaction import Transaction


class Vehicle(Base):
    """
    Entidad de Vehículos (SQL Server: dbo.Vehiculos).
    Registra placas, categorías y asociación a membresía de socio.
    """
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plate: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    category: Mapped[VehicleCategory] = mapped_column(Enum(VehicleCategory), nullable=False, index=True)
    brand_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    membership_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("memberships.id", ondelete="SET NULL"), nullable=True
    )
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relaciones
    membership: Mapped[Optional["Membership"]] = relationship("Membership", back_populates="vehicles")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="vehicle")
