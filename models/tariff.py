from datetime import datetime
from sqlalchemy import DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base, VehicleCategory, utc_now


class Tariff(Base):
    """
    Entidad de Tarifas por Categoría Vehicular (SQL Server: dbo.Tarifas).
    Define precios diferenciados (regular vs membresía) y tiempos promedio de atención.
    """
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[VehicleCategory] = mapped_column(
        Enum(VehicleCategory), unique=True, nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(120), nullable=False)
    regular_price: Mapped[float] = mapped_column(Float, nullable=False)
    member_price: Mapped[float] = mapped_column(Float, nullable=False)
    avg_service_seconds_cash: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    avg_service_seconds_card: Mapped[int] = mapped_column(Integer, default=9, nullable=False)
    avg_service_seconds_member: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
