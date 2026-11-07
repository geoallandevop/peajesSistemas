from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base, MembershipStatus, utc_now

if TYPE_CHECKING:
    from models.vehicle import Vehicle
    from models.transaction import Transaction


class Membership(Base):
    """
    Entidad de Membresías y Socios (SQL Server: dbo.Membresias).
    Incluye código único generado, vencimiento y registro de renovaciones.
    """
    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    member_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    national_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus), default=MembershipStatus.ACTIVA, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_renewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    renewal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relaciones
    vehicles: Mapped[List["Vehicle"]] = relationship("Vehicle", back_populates="membership")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="membership")

    def is_currently_active(self, reference_time: Optional[datetime] = None) -> bool:
        """Verifica si la membresía está activa y no ha alcanzado su fecha de vencimiento."""
        now = reference_time or utc_now()
        exp = self.expires_at
        if exp.tzinfo is None and now.tzinfo is not None:
            exp = exp.replace(tzinfo=timezone.utc)
        elif exp.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return self.status == MembershipStatus.ACTIVA and exp >= now
