from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.base import MembershipStatus, PaymentMethod, VehicleCategory, utc_now
from models.membership import Membership
from models.tariff import Tariff
from models.vehicle import Vehicle


def sync_membership_expiration(db: Session, membership: Membership) -> Membership:
    """Sincroniza el estado a VENCIDA si la fecha de vencimiento ya expiró."""
    now = utc_now()
    exp = membership.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=now.tzinfo)
    if exp < now and membership.status == MembershipStatus.ACTIVA:
        membership.status = MembershipStatus.VENCIDA
        db.add(membership)
        db.commit()
        db.refresh(membership)
    return membership


def resolve_membership(
    db: Session,
    member_code: Optional[str] = None,
    plate: Optional[str] = None,
) -> Optional[Membership]:
    """Busca al socio por su código único de miembro o mediante la placa del vehículo."""
    membership: Optional[Membership] = None

    if member_code:
        stmt = select(Membership).where(Membership.member_code == member_code.strip().upper())
        membership = db.scalars(stmt).first()

    if not membership and plate:
        clean_plate = plate.strip().upper()
        vehicle = db.scalars(select(Vehicle).where(Vehicle.plate == clean_plate)).first()
        if vehicle and vehicle.membership_id:
            membership = db.get(Membership, vehicle.membership_id)

    if membership:
        membership = sync_membership_expiration(db, membership)

    return membership


def calculate_toll_quote(
    db: Session,
    category: VehicleCategory,
    member_code: Optional[str] = None,
    plate: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calcula la tarifa a cobrar según el tamaño/categoría y valida si cuenta con membresía activa.
    """
    tariff = db.scalars(select(Tariff).where(Tariff.category == category)).first()
    if not tariff:
        raise ValueError(f"No existe tarifa configurada para la categoría '{category.value}'.")

    membership = resolve_membership(db, member_code=member_code, plate=plate)
    has_active_membership = False
    status_detail = "SIN_MEMBRESIA"
    resolved_code: Optional[str] = None

    if membership:
        resolved_code = membership.member_code
        if membership.is_currently_active():
            has_active_membership = True
            status_detail = f"MEMBRESIA_ACTIVA (Vence: {membership.expires_at.date().isoformat()})"
        else:
            status_detail = f"MEMBRESIA_{membership.status.value} (Venció: {membership.expires_at.date().isoformat()})"

    regular_price = round(float(tariff.regular_price), 2)
    final_price = round(float(tariff.member_price if has_active_membership else tariff.regular_price), 2)
    discount_applied = round(max(0.0, regular_price - final_price), 2)

    return {
        "category": category,
        "has_active_membership": has_active_membership,
        "member_code": resolved_code,
        "membership_status_detail": status_detail,
        "regular_price": regular_price,
        "discount_applied": discount_applied,
        "final_price": final_price,
        "tariff_model": tariff,
        "membership_model": membership,
    }


def estimate_service_seconds(
    tariff: Tariff,
    payment_method: PaymentMethod,
    has_active_membership: bool,
) -> float:
    """Estima el tiempo medio de atención según categoría, pago y condición de socio."""
    if has_active_membership:
        return float(tariff.avg_service_seconds_member)
    if payment_method == PaymentMethod.TARJETA:
        return float(tariff.avg_service_seconds_card)
    return float(tariff.avg_service_seconds_cash)


def list_tariffs(db: Session) -> List[Tariff]:
    """Obtiene todas las tarifas registradas."""
    return list(db.scalars(select(Tariff).order_by(Tariff.id)).all())
