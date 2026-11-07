from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base, LaneStatus, LaneType

if TYPE_CHECKING:
    from models.transaction import Transaction


class Lane(Base):
    """
    Entidad de Carriles de Peaje (SQL Server: dbo.Carriles).
    Gestiona colas en tiempo real, operador asignado y estadísticas operativas acumuladas.
    """
    __tablename__ = "lanes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    lane_type: Mapped[LaneType] = mapped_column(Enum(LaneType), default=LaneType.MIXTO, nullable=False)
    status: Mapped[LaneStatus] = mapped_column(Enum(LaneStatus), default=LaneStatus.ABIERTO, nullable=False)
    operator_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    current_queue_length: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accumulated_wait_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    accumulated_service_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relaciones
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="lane")
