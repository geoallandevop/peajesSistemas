import secrets
from datetime import datetime, time, timezone, date
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.base import LaneStatus, LaneType, PaymentMethod, VehicleCategory, utc_now
from models.daily_closure import DailyClosure
from models.lane import Lane
from models.transaction import Transaction
from models.vehicle import Vehicle
from controllers.tariff_controller import calculate_toll_quote, estimate_service_seconds


def generate_receipt_code() -> str:
    """Genera folio único de cobro."""
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(3).upper()
    return f"TX-{stamp}-{suffix}"


def list_lanes(db: Session) -> List[Lane]:
    """Lista todos los carriles ordenados por ID."""
    return list(db.scalars(select(Lane).order_by(Lane.id)).all())


def update_lane_status(db: Session, lane_id: int, new_status: LaneStatus) -> Lane:
    """Actualiza el estado operativo de un carril (ABIERTO, CERRADO, MANTENIMIENTO)."""
    lane = db.get(Lane, lane_id)
    if not lane:
        raise ValueError(f"No existe el carril con ID {lane_id}.")
    lane.status = new_status
    db.add(lane)
    db.commit()
    db.refresh(lane)
    return lane


def process_toll_payment(
    db: Session,
    lane_id: int,
    plate: str,
    vehicle_category: VehicleCategory,
    payment_method: PaymentMethod,
    member_code: Optional[str] = None,
    wait_time_seconds: float = 6.0,
    service_time_seconds: Optional[float] = None,
) -> Transaction:
    """
    Procesa el cobro de peaje en la caseta física:
    - Valida carril abierto y compatibilidad con carriles exclusivos de socios.
    - Cotiza tarifa y aplica descuento si el socio está activo.
    - Registra el cruce y actualiza las estadísticas del carril en tiempo real.
    """
    lane = db.get(Lane, lane_id)
    if not lane:
        raise ValueError(f"El carril con ID {lane_id} no existe.")

    if lane.status != LaneStatus.ABIERTO:
        raise ValueError(f"El carril '{lane.code}' no está habilitado (Estado: {lane.status.value}).")

    clean_plate = plate.strip().upper()
    quote = calculate_toll_quote(
        db=db,
        category=vehicle_category,
        member_code=member_code,
        plate=clean_plate,
    )

    if lane.lane_type == LaneType.EXCLUSIVO_MIEMBROS and not quote["has_active_membership"]:
        raise ValueError(
            f"El carril '{lane.code}' es EXCLUSIVO_MIEMBROS y el vehículo '{clean_plate}' "
            f"no posee membresía activa ({quote['membership_status_detail']})."
        )

    vehicle = db.scalars(select(Vehicle).where(Vehicle.plate == clean_plate)).first()
    membership = quote["membership_model"]
    if not vehicle:
        vehicle = Vehicle(
            plate=clean_plate,
            category=vehicle_category,
            membership_id=membership.id if membership else None,
        )
        db.add(vehicle)
        db.flush()
    elif membership and not vehicle.membership_id:
        vehicle.membership_id = membership.id

    tariff = quote["tariff_model"]
    srv_seconds = (
        service_time_seconds
        if service_time_seconds is not None
        else estimate_service_seconds(tariff, payment_method, quote["has_active_membership"])
    )

    tx = Transaction(
        receipt_code=generate_receipt_code(),
        vehicle_id=vehicle.id,
        lane_id=lane.id,
        membership_id=membership.id if membership else None,
        plate=clean_plate,
        vehicle_category=vehicle_category,
        payment_method=payment_method,
        has_active_membership=quote["has_active_membership"],
        regular_amount=quote["regular_price"],
        discount_amount=quote["discount_applied"],
        amount_charged=quote["final_price"],
        wait_time_seconds=wait_time_seconds,
        service_time_seconds=srv_seconds,
        is_simulated=False,
        timestamp=utc_now(),
    )
    db.add(tx)

    # Actualizar acumuladores del carril
    lane.total_processed += 1
    lane.accumulated_wait_seconds += float(wait_time_seconds)
    lane.accumulated_service_seconds += float(srv_seconds)
    if lane.current_queue_length > 0:
        lane.current_queue_length -= 1
    db.add(lane)

    db.commit()
    db.refresh(tx)
    return tx


def generate_daily_closure(
    db: Session,
    closure_date: Optional[date] = None,
    closed_by: str = "Supervisor de Turno",
    include_already_closed: bool = True,
) -> DailyClosure:
    """
    Genera el Cierre Diario de Caja en Quetzales (Q) con desglose por:
    1. Método de pago (Efectivo vs Tarjeta)
    2. Categoría vehicular (volumen, recaudación, efectivo, tarjeta)
    3. Condición de membresía (Socios activos vs Usuarios regulares)
    4. Carril de peaje
    (Excluyendo la sección de ahorro según requerimiento).
    """
    target_date = closure_date or utc_now().date()
    start_dt = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

    stmt = select(Transaction).where(
        Transaction.timestamp >= start_dt,
        Transaction.timestamp <= end_dt,
    )
    if not include_already_closed:
        stmt = stmt.where(Transaction.daily_closure_id.is_(None))

    transactions = list(db.scalars(stmt).all())

    total_transactions = len(transactions)
    total_revenue = round(sum(t.amount_charged for t in transactions), 2)
    total_cash = round(
        sum(t.amount_charged for t in transactions if t.payment_method == PaymentMethod.EFECTIVO), 2
    )
    total_card = round(
        sum(t.amount_charged for t in transactions if t.payment_method == PaymentMethod.TARJETA), 2
    )
    total_discounts = round(sum(t.discount_amount for t in transactions), 2)

    # 1. Desglose por Categoría
    breakdown_by_category: Dict[str, Any] = {}
    for cat in VehicleCategory:
        cat_txs = [t for t in transactions if t.vehicle_category == cat]
        cat_rev = round(sum(t.amount_charged for t in cat_txs), 2)
        breakdown_by_category[cat.value] = {
            "vehicles_count": len(cat_txs),
            "net_revenue": cat_rev,
            "cash_revenue": round(
                sum(t.amount_charged for t in cat_txs if t.payment_method == PaymentMethod.EFECTIVO), 2
            ),
            "card_revenue": round(
                sum(t.amount_charged for t in cat_txs if t.payment_method == PaymentMethod.TARJETA), 2
            ),
            "share_of_revenue_pct": round((cat_rev / total_revenue * 100.0), 2) if total_revenue > 0 else 0.0,
        }

    # 2. Desglose por Condición de Membresía
    member_txs = [t for t in transactions if t.has_active_membership]
    regular_txs = [t for t in transactions if not t.has_active_membership]
    mem_rev = round(sum(t.amount_charged for t in member_txs), 2)
    reg_rev = round(sum(t.amount_charged for t in regular_txs), 2)

    breakdown_by_membership = {
        "CON_MEMBRESIA_ACTIVA": {
            "vehicles_count": len(member_txs),
            "net_revenue": mem_rev,
            "cash_revenue": round(
                sum(t.amount_charged for t in member_txs if t.payment_method == PaymentMethod.EFECTIVO), 2
            ),
            "card_revenue": round(
                sum(t.amount_charged for t in member_txs if t.payment_method == PaymentMethod.TARJETA), 2
            ),
            "share_of_revenue_pct": round((mem_rev / total_revenue * 100.0), 2) if total_revenue > 0 else 0.0,
        },
        "SIN_MEMBRESIA_O_VENCIDA": {
            "vehicles_count": len(regular_txs),
            "net_revenue": reg_rev,
            "cash_revenue": round(
                sum(t.amount_charged for t in regular_txs if t.payment_method == PaymentMethod.EFECTIVO), 2
            ),
            "card_revenue": round(
                sum(t.amount_charged for t in regular_txs if t.payment_method == PaymentMethod.TARJETA), 2
            ),
            "share_of_revenue_pct": round((reg_rev / total_revenue * 100.0), 2) if total_revenue > 0 else 0.0,
        },
    }

    # 3. Desglose por Carril
    lanes = {lane.id: lane for lane in db.scalars(select(Lane)).all()}
    breakdown_by_lane: Dict[str, Any] = {}
    for lane_id, lane in lanes.items():
        lane_txs = [t for t in transactions if t.lane_id == lane_id]
        lane_rev = round(sum(t.amount_charged for t in lane_txs), 2)
        avg_wait = (
            round(sum(t.wait_time_seconds for t in lane_txs) / len(lane_txs), 2) if lane_txs else 0.0
        )
        breakdown_by_lane[lane.code] = {
            "lane_name": lane.name,
            "lane_type": lane.lane_type.value,
            "status": lane.status.value,
            "vehicles_count": len(lane_txs),
            "net_revenue": lane_rev,
            "avg_wait_seconds": avg_wait,
        }

    closure = DailyClosure(
        closure_date=target_date,
        generated_at=utc_now(),
        closed_by=closed_by,
        total_transactions=total_transactions,
        total_revenue=total_revenue,
        total_cash=total_cash,
        total_card=total_card,
        total_discounts_granted=total_discounts,
        breakdown_by_category=breakdown_by_category,
        breakdown_by_membership=breakdown_by_membership,
        breakdown_by_lane=breakdown_by_lane,
    )
    db.add(closure)
    db.flush()

    for tx in transactions:
        tx.daily_closure_id = closure.id
        db.add(tx)

    db.commit()
    db.refresh(closure)
    return closure
