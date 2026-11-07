"""
Suite de Pruebas Automatizadas para el Sistema de Gestión de Peajes (Aplicación de Escritorio).
Verifica:
1. Tarifas y precios diferenciados en Quetzales (Regular vs Socio Activo vs Socio Vencido).
2. Membresías con DPI: Alta con código único y renovación de vencidos.
3. Operación y cambio de estado de Carriles (Abierto, Cerrado, Mantenimiento).
4. Cobro en caseta física (Efectivo/Tarjeta) en Quetzales.
5. Cierre Diario sin sección de ahorro y exportación a PDF.
6. Simulación de Eventos Discretos (DES) con nuevos parámetros (densidad, semáforos, porcentajes) y PDF.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.base import Base, LaneStatus, PaymentMethod, VehicleCategory
from models.database import SessionLocal, engine, seed_initial_data
from controllers.tariff_controller import calculate_toll_quote
from controllers.membership_controller import create_member, renew_member
from controllers.toll_controller import process_toll_payment, generate_daily_closure, update_lane_status
from controllers.simulation_engine import DiscreteEventTollSimulator
from controllers.pdf_generator import generate_closure_pdf, generate_simulation_pdf
from version import __version__


def run_tests():
    # 0. Verificación de Versión del Sistema
    assert __version__ == "3.15.0", f"Versión esperada 3.15.0, pero se obtuvo {__version__}"

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        seed_initial_data(db)

        # 1. Verificación de Tarifas en Quetzales
        q_reg = calculate_toll_quote(db, category=VehicleCategory.LIVIANO, plate="P-REG01")
        assert q_reg["has_active_membership"] is False
        assert q_reg["final_price"] == 3.00

        q_act = calculate_toll_quote(db, category=VehicleCategory.LIVIANO, member_code="MEM-2026-ACTIVO1")
        assert q_act["has_active_membership"] is True
        assert q_act["final_price"] == 2.10
        assert q_act["discount_applied"] == 0.90

        q_venc = calculate_toll_quote(db, category=VehicleCategory.CAMION_2_EJES, member_code="MEM-2026-VENCID2")
        assert q_venc["has_active_membership"] is False
        assert q_venc["final_price"] == 8.50

        # 2. Renovación de Membresía Vencida y DPI
        m_renovado = renew_member(db, member_code="MEM-2026-VENCID2", duration_days=30)
        assert m_renovado.is_currently_active() is True
        assert m_renovado.status.value == "ACTIVA"

        q_post_renov = calculate_toll_quote(db, category=VehicleCategory.CAMION_2_EJES, member_code="MEM-2026-VENCID2")
        assert q_post_renov["has_active_membership"] is True
        assert q_post_renov["final_price"] == 6.50

        new_socio = create_member(
            db,
            owner_name="Williams Sequén",
            owner_email="williams.test@peaje.com",
            national_id="2294264648",  # DPI
            duration_days=60,
            plate="P-888GUA",
            category=VehicleCategory.AUTOBUS,
        )
        assert new_socio.member_code.startswith("MEM-")

        # 3. Cambio de Estado de Carriles (Cerrar, Mantenimiento, Abrir)
        lane_cerrado = update_lane_status(db, lane_id=2, new_status=LaneStatus.CERRADO)
        assert lane_cerrado.status == LaneStatus.CERRADO

        lane_mant = update_lane_status(db, lane_id=3, new_status=LaneStatus.MANTENIMIENTO)
        assert lane_mant.status == LaneStatus.MANTENIMIENTO

        lane_reabierto = update_lane_status(db, lane_id=2, new_status=LaneStatus.ABIERTO)
        assert lane_reabierto.status == LaneStatus.ABIERTO
        update_lane_status(db, lane_id=3, new_status=LaneStatus.ABIERTO)

        # 4. Cobros de Peaje en Caseta (Efectivo y Tarjeta en Q)
        tx1 = process_toll_payment(
            db,
            lane_id=1,
            plate="P-100REG",
            vehicle_category=VehicleCategory.CAMION_PESADO,
            payment_method=PaymentMethod.EFECTIVO,
            wait_time_seconds=10.0,
        )
        assert tx1.amount_charged == 14.00
        assert tx1.has_active_membership is False

        tx2 = process_toll_payment(
            db,
            lane_id=4,
            plate="P-888GUA",
            vehicle_category=VehicleCategory.AUTOBUS,
            payment_method=PaymentMethod.TARJETA,
            wait_time_seconds=2.0,
        )
        assert tx2.amount_charged == 4.50
        assert tx2.has_active_membership is True

        # 5. Cierre Diario y PDF (Sin ahorro)
        closure = generate_daily_closure(db, closed_by="Auditor de Pruebas", include_already_closed=True)
        assert closure.total_transactions == 2
        assert round(closure.total_cash + closure.total_card, 2) == round(closure.total_revenue, 2)

        closure_dict = {
            "closure_date": closure.closure_date.isoformat(),
            "generated_at": closure.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "closed_by": closure.closed_by,
            "total_transactions": closure.total_transactions,
            "total_revenue": closure.total_revenue,
            "total_cash": closure.total_cash,
            "total_card": closure.total_card,
            "breakdown_by_category": closure.breakdown_by_category,
            "breakdown_by_membership": closure.breakdown_by_membership,
            "breakdown_by_lane": closure.breakdown_by_lane,
        }
        test_closure_pdf = "tests/test_cierre.pdf"
        generate_closure_pdf(closure_dict, test_closure_pdf)
        assert os.path.exists(test_closure_pdf)
        os.remove(test_closure_pdf)

        # 6. Motor DES con Nuevos Parámetros (Densidad, Semáforos, % Vehículos) y PDF
        simulator = DiscreteEventTollSimulator(
            db=db,
            traffic_density="Media (Tráfico Regular)",
            traffic_light_green_seconds=15,
            duration_minutes=5,
            pct_liviano=50.0,
            pct_moto=20.0,
            pct_autobus=10.0,
            pct_camion_2_ejes=12.0,
            pct_camion_pesado=8.0,
            persist_to_db=True,
        )
        sim_res = simulator.run()

        assert sim_res["zero_loss_verified"] is True
        assert sim_res["total_vehicles_generated"] == sim_res["total_vehicles_completed"]
        assert sim_res["vehicles_remaining_in_queue"] == 0
        assert sim_res["vehicles_remaining_in_service"] == 0
        assert sim_res["throughput_vehicles_per_minute"] > 0
        assert sim_res["throughput_vehicles_per_hour"] > 0

        test_sim_pdf = "tests/test_simulacion.pdf"
        generate_simulation_pdf(sim_res, test_sim_pdf)
        assert os.path.exists(test_sim_pdf)
        os.remove(test_sim_pdf)

        print("=== TODAS LAS PRUEBAS ACTUALIZADAS PASARON CON ÉXITO ===")
        print(f"1. Moneda Oficial: Quetzales (Q)")
        print(f"2. Socio Creado con DPI: {new_socio.member_code} (DPI: {new_socio.national_id})")
        print(f"3. Estados de Carril verificados (Abrir, Cerrar, Mantenimiento)")
        print(f"4. Ecuación Invariante DES: {sim_res['conservation_equation']}")
        print(
            f"5. Rendimiento DES: Espera Media={sim_res['avg_wait_time_seconds']}s | "
            f"Flujo/Min={sim_res['throughput_vehicles_per_minute']} veh/min | "
            f"Flujo/Hora={sim_res['throughput_vehicles_per_hour']} veh/hora"
        )
        print(f"6. Generadores de PDF de Cierre y Simulación validados correctamente.")


if __name__ == "__main__":
    run_tests()
