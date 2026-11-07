import secrets
import string
from datetime import timedelta
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.base import MembershipStatus, VehicleCategory, utc_now
from models.membership import Membership
from models.vehicle import Vehicle
from controllers.tariff_controller import sync_membership_expiration


def generate_unique_member_code(db: Session) -> str:
    """Genera un código único alfanumérico con formato MEM-YYYY-XXXXXX."""
    alphabet = string.ascii_uppercase + string.digits
    year = utc_now().year
    for _ in range(30):
        token = "".join(secrets.choice(alphabet) for _ in range(6))
        candidate = f"MEM-{year}-{token}"
        exists = db.scalars(select(Membership.id).where(Membership.member_code == candidate)).first()
        if not exists:
            return candidate
    raise RuntimeError("No se pudo generar un código único de socio.")


def create_member(
    db: Session,
    owner_name: str,
    owner_email: str,
    national_id: str,
    duration_days: int = 30,
    plate: Optional[str] = None,
    category: Optional[VehicleCategory] = None,
) -> Membership:
    """Crea un nuevo socio con código único y fecha de vencimiento."""
    clean_email = owner_email.strip().lower()
    existing = db.scalars(select(Membership).where(Membership.owner_email == clean_email)).first()
    if existing:
        raise ValueError(f"Ya existe un socio registrado con el correo '{owner_email}'.")

    now = utc_now()
    member_code = generate_unique_member_code(db)
    expires_at = now + timedelta(days=duration_days)

    member = Membership(
        member_code=member_code,
        owner_name=owner_name.strip(),
        owner_email=clean_email,
        national_id=national_id.strip(),
        status=MembershipStatus.ACTIVA,
        created_at=now,
        expires_at=expires_at,
        renewal_count=0,
    )
    db.add(member)
    db.flush()

    if plate and category:
        clean_plate = plate.strip().upper()
        veh = db.scalars(select(Vehicle).where(Vehicle.plate == clean_plate)).first()
        if veh:
            veh.membership_id = member.id
            veh.category = category
        else:
            veh = Vehicle(plate=clean_plate, category=category, membership_id=member.id)
            db.add(veh)

    db.commit()
    db.refresh(member)
    return member


def renew_member(db: Session, member_code: str, duration_days: int = 30) -> Membership:
    """
    Lógica de renovación:
    - Si está VENCIDA (expires_at < now), reactiva el estado a ACTIVA y parte desde la fecha actual.
    - Si aún está VIGENTE (expires_at >= now), extiende los días a partir de la fecha de vencimiento actual.
    """
    clean_code = member_code.strip().upper()
    member = db.scalars(select(Membership).where(Membership.member_code == clean_code)).first()
    if not member:
        raise ValueError(f"No se encontró el socio con código '{clean_code}'.")

    now = utc_now()
    exp = member.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=now.tzinfo)

    base_date = now if exp < now else exp
    member.expires_at = base_date + timedelta(days=duration_days)
    member.status = MembershipStatus.ACTIVA
    member.last_renewed_at = now
    member.renewal_count += 1

    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def list_members(db: Session) -> List[Membership]:
    """Lista todos los socios sincronizando vigencia."""
    members = list(db.scalars(select(Membership).order_by(Membership.id.desc())).all())
    for m in members:
        sync_membership_expiration(db, m)
    return members
