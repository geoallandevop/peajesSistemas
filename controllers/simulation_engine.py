import math
import random
import secrets
from collections import deque
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Deque, Dict, List, Optional, Tuple, Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.base import (
    LaneStatus,
    LaneType,
    MembershipStatus,
    PaymentMethod,
    VehicleCategory,
    utc_now,
)
from models.lane import Lane
from models.membership import Membership
from models.tariff import Tariff
from models.transaction import Transaction


class SimVehicleState(str, Enum):
    """Estados del ciclo de vida de un vehículo en la simulación."""
    GENERATED = "GENERATED"
    QUEUED = "QUEUED"
    IN_SERVICE = "IN_SERVICE"
    COMPLETED = "COMPLETED"


@dataclass
class SimulatedVehicle:
    """Entidad de vehículo simulado con trazabilidad temporal."""
    sim_id: str
    plate: str
    category: VehicleCategory
    payment_method: PaymentMethod
    has_active_membership: bool
    membership_condition: str  # "ACTIVA" | "VENCIDA" | "SIN_MEMBRESIA"
    member_id: Optional[int]
    regular_price: float
    discount_amount: float
    final_price: float
    service_duration_cycles: int
    arrival_cycle: int

    assigned_lane_id: Optional[int] = None
    assigned_lane_code: Optional[str] = None
    service_start_cycle: Optional[int] = None
    completion_cycle: Optional[int] = None
    remaining_service_cycles: int = 0
    state: SimVehicleState = SimVehicleState.GENERATED

    @property
    def wait_cycles(self) -> int:
        if self.service_start_cycle is None:
            return 0
        return max(0, self.service_start_cycle - self.arrival_cycle)

    @property
    def system_cycles(self) -> int:
        if self.completion_cycle is None:
            return 0
        return max(0, self.completion_cycle - self.arrival_cycle)


@dataclass
class SimulatedLaneServer:
    """Servidor de carril con cola FIFO (M/G/1 en tiempo discreto)."""
    lane_id: int
    code: str
    name: str
    lane_type: LaneType
    queue: Deque[SimulatedVehicle] = field(default_factory=deque)
    active_vehicle: Optional[SimulatedVehicle] = None

    processed_count: int = 0
    max_queue_length: int = 0
    total_wait_cycles: int = 0
    total_service_cycles: int = 0
    busy_cycles: int = 0
    revenue_collected: float = 0.0

    def expected_workload_cycles(self) -> int:
        active_rem = self.active_vehicle.remaining_service_cycles if self.active_vehicle else 0
        queued_rem = sum(v.service_duration_cycles for v in self.queue)
        return active_rem + queued_rem


class DiscreteEventTollSimulator:
    """
    Motor de Simulación de Eventos Discretos (DES) por Ciclos Temporales.
    Permite configurar:
    - Densidad de Tráfico (Baja, Media, Alta, Extrema)
    - Tiempos de verde en semáforos / paso fluido (segundos)
    - Porcentajes por tipo de vehículo (Livianos, Motos, Autobuses, Camiones)
    - Duración en minutos
    """

    DENSITY_MAP = {
        "Baja (Hora Valle)": {"prob": 0.25, "max_arr": 1},
        "Media (Tráfico Regular)": {"prob": 0.45, "max_arr": 2},
        "Alta (Hora Pico)": {"prob": 0.65, "max_arr": 3},
        "Extrema (Congestión)": {"prob": 0.85, "max_arr": 4},
    }

    def __init__(
        self,
        db: Session,
        traffic_density: str = "Media (Tráfico Regular)",
        traffic_light_green_seconds: int = 15,
        duration_minutes: int = 5,
        pct_liviano: float = 50.0,
        pct_moto: float = 20.0,
        pct_autobus: float = 10.0,
        pct_camion_2_ejes: float = 12.0,
        pct_camion_pesado: float = 8.0,
        persist_to_db: bool = True,
    ):
        self.db = db
        self.traffic_density = traffic_density
        self.traffic_light_green_seconds = max(5, traffic_light_green_seconds)
        self.duration_minutes = max(1, duration_minutes)
        self.horizon_cycles = self.duration_minutes * 60
        self.persist_to_db = persist_to_db

        density_cfg = self.DENSITY_MAP.get(traffic_density, self.DENSITY_MAP["Media (Tráfico Regular)"])
        self.arrival_probability = density_cfg["prob"]
        self.max_arrivals = density_cfg["max_arr"]

        # Normalizar porcentajes
        total_pct = pct_liviano + pct_moto + pct_autobus + pct_camion_2_ejes + pct_camion_pesado
        if total_pct <= 0:
            total_pct = 100.0
        self.category_weights = [
            (VehicleCategory.LIVIANO, pct_liviano / total_pct),
            (VehicleCategory.MOTO, pct_moto / total_pct),
            (VehicleCategory.AUTOBUS, pct_autobus / total_pct),
            (VehicleCategory.CAMION_2_EJES, pct_camion_2_ejes / total_pct),
            (VehicleCategory.CAMION_PESADO, pct_camion_pesado / total_pct),
        ]
        self.vehicle_distribution_summary = (
            f"Livianos {pct_liviano:.0f}%, Motos {pct_moto:.0f}%, "
            f"Autobuses {pct_autobus:.0f}%, Camiones 2E {pct_camion_2_ejes:.0f}%, Camiones Pesados {pct_camion_pesado:.0f}%"
        )

        self.rng = random.Random(42)
        self.simulation_id = f"SIM-{utc_now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"

        tariffs_list = list(db.scalars(select(Tariff)).all())
        if not tariffs_list:
            raise ValueError("No existen tarifas configuradas en la base de datos.")
        self.tariffs: Dict[VehicleCategory, Tariff] = {t.category: t for t in tariffs_list}

        open_lanes = list(
            db.scalars(select(Lane).where(Lane.status == LaneStatus.ABIERTO).order_by(Lane.id)).all()
        )
        if not open_lanes:
            raise ValueError("Debe haber al menos un carril ABIERTO para simular.")

        self.lanes: Dict[int, SimulatedLaneServer] = {
            l.id: SimulatedLaneServer(
                lane_id=l.id,
                code=l.code,
                name=l.name,
                lane_type=l.lane_type,
            )
            for l in open_lanes
        }

        self.active_memberships = [
            m for m in db.scalars(select(Membership)).all() if m.is_currently_active()
        ]

        self.vehicle_registry: Dict[str, SimulatedVehicle] = {}
        self.completed_vehicles: List[SimulatedVehicle] = []
        self._seq_counter = 0

    def _choose_category(self) -> VehicleCategory:
        cats = [c for c, _ in self.category_weights]
        weights = [w for _, w in self.category_weights]
        return self.rng.choices(cats, weights=weights, k=1)[0]

    def _generate_vehicle(self, current_cycle: int) -> SimulatedVehicle:
        self._seq_counter += 1
        sim_id = f"VEH-{self._seq_counter:05d}"
        plate = f"P{self.rng.randint(100, 999)}-{self._seq_counter:03d}"
        category = self._choose_category()
        tariff = self.tariffs[category]

        roll = self.rng.random()
        member_id: Optional[int] = None
        if roll < 0.35:
            has_active_membership = True
            membership_condition = "ACTIVA"
            if self.active_memberships:
                member_id = self.rng.choice(self.active_memberships).id
        elif roll < 0.43:
            has_active_membership = False
            membership_condition = "VENCIDA"
        else:
            has_active_membership = False
            membership_condition = "SIN_MEMBRESIA"

        if has_active_membership:
            payment_method = PaymentMethod.TARJETA if self.rng.random() < 0.80 else PaymentMethod.EFECTIVO
        else:
            payment_method = PaymentMethod.EFECTIVO if self.rng.random() < 0.60 else PaymentMethod.TARJETA

        regular_price = round(float(tariff.regular_price), 2)
        final_price = round(
            float(tariff.member_price if has_active_membership else tariff.regular_price), 2
        )
        discount_amount = round(max(0.0, regular_price - final_price), 2)

        if has_active_membership:
            base_srv = tariff.avg_service_seconds_member
        elif payment_method == PaymentMethod.TARJETA:
            base_srv = tariff.avg_service_seconds_card
        else:
            base_srv = tariff.avg_service_seconds_cash

        # El tiempo de verde del semáforo agiliza el flujo si es amplio
        green_factor = max(0.8, 1.0 - (self.traffic_light_green_seconds - 15) * 0.01)
        service_cycles = max(1, int(round((base_srv + self.rng.randint(-1, 2)) * green_factor)))

        vehicle = SimulatedVehicle(
            sim_id=sim_id,
            plate=plate,
            category=category,
            payment_method=payment_method,
            has_active_membership=has_active_membership,
            membership_condition=membership_condition,
            member_id=member_id,
            regular_price=regular_price,
            discount_amount=discount_amount,
            final_price=final_price,
            service_duration_cycles=service_cycles,
            arrival_cycle=current_cycle,
        )
        self.vehicle_registry[sim_id] = vehicle
        return vehicle

    def _route_vehicle_to_lane(self, vehicle: SimulatedVehicle) -> None:
        compat: List[SimulatedLaneServer] = []
        for lane in self.lanes.values():
            if lane.lane_type == LaneType.EXCLUSIVO_MIEMBROS:
                if vehicle.has_active_membership:
                    compat.append(lane)
            elif lane.lane_type == LaneType.EFECTIVO:
                compat.append(lane)
            else:  # LaneType.MIXTO
                compat.append(lane)

        chosen = min(compat, key=lambda l: (l.expected_workload_cycles(), len(l.queue), l.lane_id))
        vehicle.assigned_lane_id = chosen.lane_id
        vehicle.assigned_lane_code = chosen.code
        vehicle.state = SimVehicleState.QUEUED
        chosen.queue.append(vehicle)

        if len(chosen.queue) > chosen.max_queue_length:
            chosen.max_queue_length = len(chosen.queue)

    def _step_lane_servers(self, current_cycle: int) -> None:
        for lane in self.lanes.values():
            if lane.active_vehicle is None and lane.queue:
                next_veh = lane.queue.popleft()
                next_veh.state = SimVehicleState.IN_SERVICE
                next_veh.service_start_cycle = current_cycle
                next_veh.remaining_service_cycles = next_veh.service_duration_cycles
                lane.active_vehicle = next_veh

            if lane.active_vehicle is not None:
                active = lane.active_vehicle
                lane.busy_cycles += 1
                active.remaining_service_cycles -= 1

                if active.remaining_service_cycles <= 0:
                    active.state = SimVehicleState.COMPLETED
                    active.completion_cycle = current_cycle + 1
                    lane.processed_count += 1
                    lane.total_wait_cycles += active.wait_cycles
                    lane.total_service_cycles += active.service_duration_cycles
                    lane.revenue_collected = round(lane.revenue_collected + active.final_price, 2)

                    self.completed_vehicles.append(active)
                    lane.active_vehicle = None

    def _has_pending_vehicles(self) -> bool:
        for lane in self.lanes.values():
            if lane.active_vehicle is not None or len(lane.queue) > 0:
                return True
        return False

    def verify_conservation_invariant(self) -> Tuple[bool, int, int, int, int, str]:
        generated_ids = set(self.vehicle_registry.keys())
        completed_ids = {v.sim_id for v in self.completed_vehicles}
        queued_ids = {v.sim_id for l in self.lanes.values() for v in l.queue}
        in_service_ids = {l.active_vehicle.sim_id for l in self.lanes.values() if l.active_vehicle}

        total_gen = len(generated_ids)
        total_comp = len(completed_ids)
        total_q = len(queued_ids)
        total_srv = len(in_service_ids)

        disjoint = (
            completed_ids.isdisjoint(queued_ids)
            and completed_ids.isdisjoint(in_service_ids)
            and queued_ids.isdisjoint(in_service_ids)
        )
        exact_union = generated_ids == (completed_ids | queued_ids | in_service_ids)
        counts_match = total_gen == (total_comp + total_q + total_srv)
        drain_complete = (total_q == 0 and total_srv == 0)

        is_valid = disjoint and exact_union and counts_match and drain_complete
        eq = f"Generados ({total_gen}) = Completados ({total_comp}) + En Cola ({total_q}) + En Servicio ({total_srv})"
        return is_valid, total_gen, total_comp, total_q, total_srv, eq

    def _persist_results(self) -> None:
        base_time = utc_now()
        db_lanes = {l.id: l for l in self.db.scalars(select(Lane)).all()}

        for idx, v in enumerate(self.completed_vehicles):
            tx = Transaction(
                receipt_code=f"{self.simulation_id}-{idx + 1:05d}",
                vehicle_id=None,
                lane_id=v.assigned_lane_id,
                membership_id=v.member_id,
                plate=v.plate,
                vehicle_category=v.category,
                payment_method=v.payment_method,
                has_active_membership=v.has_active_membership,
                regular_amount=v.regular_price,
                discount_amount=v.discount_amount,
                amount_charged=v.final_price,
                wait_time_seconds=float(v.wait_cycles),
                service_time_seconds=float(v.service_duration_cycles),
                is_simulated=True,
                timestamp=base_time + timedelta(seconds=idx % 60),
            )
            self.db.add(tx)

        for lane_id, sim_lane in self.lanes.items():
            db_l = db_lanes.get(lane_id)
            if db_l:
                db_l.total_processed += sim_lane.processed_count
                db_l.accumulated_wait_seconds += float(sim_lane.total_wait_cycles)
                db_l.accumulated_service_seconds += float(sim_lane.total_service_cycles)
                db_l.current_queue_length = len(sim_lane.queue)
                self.db.add(db_l)

        self.db.commit()

    def run(self) -> Dict[str, Any]:
        for cycle in range(self.horizon_cycles):
            if self.rng.random() <= self.arrival_probability:
                arrivals = self.rng.randint(1, self.max_arrivals)
                for _ in range(arrivals):
                    veh = self._generate_vehicle(current_cycle=cycle)
                    self._route_vehicle_to_lane(veh)
            self._step_lane_servers(current_cycle=cycle)

        # Drenado de colas automático para garantizar pérdida cero
        drain_cycles = 0
        while self._has_pending_vehicles() and drain_cycles < 60000:
            self._step_lane_servers(current_cycle=self.horizon_cycles + drain_cycles)
            drain_cycles += 1

        total_cycles = self.horizon_cycles + drain_cycles
        valid, n_gen, n_comp, n_q, n_srv, eq = self.verify_conservation_invariant()
        if not valid:
            raise RuntimeError(f"Violación del invariante de conservación: {eq}")

        if self.persist_to_db and self.completed_vehicles:
            self._persist_results()

        wait_times = sorted(v.wait_cycles for v in self.completed_vehicles)
        n = len(self.completed_vehicles)
        avg_wait = round(sum(wait_times) / n, 2) if n > 0 else 0.0
        max_wait = float(wait_times[-1]) if n > 0 else 0.0
        p95_idx = min(n - 1, max(0, math.ceil(0.95 * n) - 1)) if n > 0 else 0
        p95_wait = float(wait_times[p95_idx]) if n > 0 else 0.0

        srv_times = [v.service_duration_cycles for v in self.completed_vehicles]
        avg_srv = round(sum(srv_times) / n, 2) if n > 0 else 0.0
        eff_sec = max(1, total_cycles)
        tp_min = round((n / eff_sec) * 60.0, 2)
        tp_hour = round((n / eff_sec) * 3600.0, 2)

        tot_rev = round(sum(v.final_price for v in self.completed_vehicles), 2)
        tot_disc = round(sum(v.discount_amount for v in self.completed_vehicles), 2)
        rev_cash = round(
            sum(v.final_price for v in self.completed_vehicles if v.payment_method == PaymentMethod.EFECTIVO), 2
        )
        rev_card = round(
            sum(v.final_price for v in self.completed_vehicles if v.payment_method == PaymentMethod.TARJETA), 2
        )

        lane_stats = []
        for l in self.lanes.values():
            proc = l.processed_count
            lane_stats.append({
                "lane_id": l.lane_id,
                "code": l.code,
                "lane_type": l.lane_type.value,
                "processed": proc,
                "max_queue": l.max_queue_length,
                "avg_wait": round(l.total_wait_cycles / proc, 2) if proc > 0 else 0.0,
                "avg_srv": round(l.total_service_cycles / proc, 2) if proc > 0 else 0.0,
                "utilization": round((l.busy_cycles / eff_sec) * 100.0, 1),
                "revenue": l.revenue_collected,
            })

        return {
            "simulation_id": self.simulation_id,
            "traffic_density": self.traffic_density,
            "traffic_light_green_seconds": self.traffic_light_green_seconds,
            "duration_minutes": self.duration_minutes,
            "horizon_cycles": self.horizon_cycles,
            "total_cycles": total_cycles,
            "drain_cycles": drain_cycles,
            "vehicle_distribution_summary": self.vehicle_distribution_summary,
            "total_vehicles_generated": n_gen,
            "total_vehicles_completed": n_comp,
            "vehicles_remaining_in_queue": n_q,
            "vehicles_remaining_in_service": n_srv,
            "zero_loss_verified": valid,
            "conservation_equation": eq,
            "avg_wait_time_seconds": avg_wait,
            "max_wait_time_seconds": max_wait,
            "p95_wait_time_seconds": p95_wait,
            "avg_service_time_seconds": avg_srv,
            "throughput_vehicles_per_minute": tp_min,
            "throughput_vehicles_per_hour": tp_hour,
            "total_revenue": tot_rev,
            "total_discounts": tot_disc,
            "total_cash": rev_cash,
            "total_card": rev_card,
            "lane_metrics": lane_stats,
        }
