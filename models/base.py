import enum
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase


def utc_now() -> datetime:
    """Retorna la fecha y hora actual en UTC."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Clase base declarativa para los modelos ORM de SQL Server y SQLite."""
    pass


class VehicleCategory(str, enum.Enum):
    """Categorías de vehículos según tamaño y número de ejes."""
    MOTO = "MOTO"
    LIVIANO = "LIVIANO"
    AUTOBUS = "AUTOBUS"
    CAMION_2_EJES = "CAMION_2_EJES"
    CAMION_PESADO = "CAMION_PESADO"


class MembershipStatus(str, enum.Enum):
    """Estados posibles de una membresía."""
    ACTIVA = "ACTIVA"
    VENCIDA = "VENCIDA"
    SUSPENDIDA = "SUSPENDIDA"


class LaneType(str, enum.Enum):
    """Configuración operativa del carril de peaje."""
    MIXTO = "MIXTO"                             # Efectivo, Tarjeta y Membresía
    EFECTIVO = "EFECTIVO"                       # Solo efectivo y tarjeta manual
    EXCLUSIVO_MIEMBROS = "EXCLUSIVO_MIEMBROS"   # Telepeaje / Socios con membresía activa


class LaneStatus(str, enum.Enum):
    """Estado de disponibilidad de un carril en la vista de empleado."""
    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"
    MANTENIMIENTO = "MANTENIMIENTO"


class PaymentMethod(str, enum.Enum):
    """Métodos de pago soportados en el peaje."""
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
