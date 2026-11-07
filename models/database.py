import os
import urllib.parse
from datetime import timedelta
from typing import Generator
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from models.base import Base, LaneStatus, LaneType, MembershipStatus, VehicleCategory, utc_now
from models.tariff import Tariff
from models.membership import Membership
from models.vehicle import Vehicle
from models.lane import Lane
from models.daily_closure import DailyClosure
from models.transaction import Transaction

# Configuración de Servidor de Base de Datos
SQL_SERVER_HOST = os.getenv("SQL_SERVER_HOST", "localhost")
SQL_SERVER_DB = os.getenv("SQL_SERVER_DB", "PeajesDB")
SQL_SERVER_USER = os.getenv("SQL_SERVER_USER", "")
SQL_SERVER_PASSWORD = os.getenv("SQL_SERVER_PASSWORD", "")
USE_SQL_SERVER = os.getenv("USE_SQL_SERVER", "false").lower() in ("true", "1", "yes")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    if USE_SQL_SERVER:
        if SQL_SERVER_USER and SQL_SERVER_PASSWORD:
            odbc_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={SQL_SERVER_HOST};"
                f"DATABASE={SQL_SERVER_DB};"
                f"UID={SQL_SERVER_USER};"
                f"PWD={SQL_SERVER_PASSWORD};"
                "TrustServerCertificate=yes;"
            )
        else:
            odbc_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={SQL_SERVER_HOST};"
                f"DATABASE={SQL_SERVER_DB};"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes;"
            )
        DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(odbc_str)}"
    else:
        DATABASE_URL = "sqlite:///./peajes.db"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
    if not DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            pass
except Exception:
    DATABASE_URL = "sqlite:///./peajes.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


def get_db_session() -> Session:
    """Retorna una nueva sesión de base de datos."""
    return SessionLocal()


def seed_initial_data(db: Session) -> None:
    """Inicializa datos semilla para Tarifas, Carriles y Membresías de prueba si la BD está vacía."""
    if not db.scalars(select(Tariff)).first():
        initial_tariffs = [
            Tariff(
                category=VehicleCategory.MOTO,
                description="Motocicletas y tricimoto",
                regular_price=1.50,
                member_price=1.00,
                avg_service_seconds_cash=10,
                avg_service_seconds_card=7,
                avg_service_seconds_member=3,
            ),
            Tariff(
                category=VehicleCategory.LIVIANO,
                description="Automóviles, SUVs y Pickups livianas",
                regular_price=3.00,
                member_price=2.10,
                avg_service_seconds_cash=14,
                avg_service_seconds_card=9,
                avg_service_seconds_member=4,
            ),
            Tariff(
                category=VehicleCategory.AUTOBUS,
                description="Autobuses de transporte público y turismo",
                regular_price=6.00,
                member_price=4.50,
                avg_service_seconds_cash=18,
                avg_service_seconds_card=11,
                avg_service_seconds_member=5,
            ),
            Tariff(
                category=VehicleCategory.CAMION_2_EJES,
                description="Camiones de carga mediana (2 ejes)",
                regular_price=8.50,
                member_price=6.50,
                avg_service_seconds_cash=20,
                avg_service_seconds_card=12,
                avg_service_seconds_member=6,
            ),
            Tariff(
                category=VehicleCategory.CAMION_PESADO,
                description="Tractocamiones y vehículos articulados (3+ ejes)",
                regular_price=14.00,
                member_price=10.50,
                avg_service_seconds_cash=25,
                avg_service_seconds_card=15,
                avg_service_seconds_member=7,
            ),
        ]
        db.add_all(initial_tariffs)
        db.commit()

    if not db.scalars(select(Lane)).first():
        initial_lanes = [
            Lane(
                code="CARRIL-01",
                name="Carril 1 - Efectivo / Manual",
                lane_type=LaneType.EFECTIVO,
                status=LaneStatus.ABIERTO,
                operator_name="Carlos Méndez",
            ),
            Lane(
                code="CARRIL-02",
                name="Carril 2 - Mixto Estándar",
                lane_type=LaneType.MIXTO,
                status=LaneStatus.ABIERTO,
                operator_name="Ana Gómez",
            ),
            Lane(
                code="CARRIL-03",
                name="Carril 3 - Mixto Rápido",
                lane_type=LaneType.MIXTO,
                status=LaneStatus.ABIERTO,
                operator_name="Luis Herrera",
            ),
            Lane(
                code="CARRIL-04",
                name="Carril 4 - Telepeaje Exclusivo Socios",
                lane_type=LaneType.EXCLUSIVO_MIEMBROS,
                status=LaneStatus.ABIERTO,
                operator_name="Sistema Automático RFID",
            ),
        ]
        db.add_all(initial_lanes)
        db.commit()

    if not db.scalars(select(Membership)).first():
        now = utc_now()
        active_member = Membership(
            member_code="MEM-2026-ACTIVO1",
            owner_name="Laura Fernández",
            owner_email="laura.fernandez@ejemplo.com",
            national_id="1029384756",
            status=MembershipStatus.ACTIVA,
            created_at=now - timedelta(days=10),
            expires_at=now + timedelta(days=20),
            renewal_count=0,
        )
        expired_member = Membership(
            member_code="MEM-2026-VENCID2",
            owner_name="Roberto Castillo",
            owner_email="roberto.castillo@ejemplo.com",
            national_id="5049382716",
            status=MembershipStatus.VENCIDA,
            created_at=now - timedelta(days=45),
            expires_at=now - timedelta(days=15),
            renewal_count=1,
        )
        db.add_all([active_member, expired_member])
        db.flush()

        v1 = Vehicle(
            plate="ABC-123",
            category=VehicleCategory.LIVIANO,
            brand_model="Toyota Corolla 2024",
            membership_id=active_member.id,
        )
        v2 = Vehicle(
            plate="EXP-999",
            category=VehicleCategory.CAMION_2_EJES,
            brand_model="Hino Serie 500",
            membership_id=expired_member.id,
        )
        db.add_all([v1, v2])
        db.commit()
