import customtkinter as ctk

from version import __version__
from models.base import Base
from models.database import SessionLocal, engine, seed_initial_data
from views.employee_view import EmployeeView
from views.membership_view import MembershipView
from views.closure_view import ClosureView
from views.simulation_view import SimulationView

# Fijar tema oscuro exclusivo (sin opción de blanco/light)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    """
    Ventana Principal de la Aplicación de Escritorio del Sistema de Gestión de Peajes.
    Tema estrictamente oscuro con navegación modular.
    Versión 3.15.0.
    """

    def __init__(self):
        super().__init__()
        self.title(f"Sistema de Gestión de Peajes & Simulación DES (Desktop) v{__version__}")
        self.geometry("1200x780")
        self.minsize(1020, 700)

        # Inicialización de tablas y datos semilla
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_initial_data(db)

        # Layout Principal: Sidebar a la izquierda, Vistas a la derecha
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_views()
        self.show_view("carriles")

    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text=f"PEAJES & DES\nSISTEMA INTEGRAL\nv{__version__}",
            font=ctk.CTkFont(size=17, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(28, 24))

        self.btn_carriles = ctk.CTkButton(
            self.sidebar_frame,
            text="🚗 Vista Empleado",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.show_view("carriles"),
        )
        self.btn_carriles.grid(row=1, column=0, padx=20, pady=8, sticky="ew")

        self.btn_socios = ctk.CTkButton(
            self.sidebar_frame,
            text="💳 Socios & Membresías",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.show_view("socios"),
        )
        self.btn_socios.grid(row=2, column=0, padx=20, pady=8, sticky="ew")

        self.btn_cierre = ctk.CTkButton(
            self.sidebar_frame,
            text="📊 Cierre Diario",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.show_view("cierre"),
        )
        self.btn_cierre.grid(row=3, column=0, padx=20, pady=8, sticky="ew")

        self.btn_sim = ctk.CTkButton(
            self.sidebar_frame,
            text="⏱️ Simulación DES",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.show_view("sim"),
        )
        self.btn_sim.grid(row=4, column=0, padx=20, pady=8, sticky="ew")

        # Al pie: Indicador de Moneda Oficial y Versión
        currency_badge = ctk.CTkLabel(
            self.sidebar_frame,
            text=f"Versión: {__version__}\nMoneda: Quetzales (Q)\nModo: Oscuro Permanente",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="center",
        )
        currency_badge.grid(row=6, column=0, padx=20, pady=(10, 24), sticky="s")

    def _build_views(self):
        self.view_carriles = EmployeeView(self)
        self.view_socios = MembershipView(self)
        self.view_cierre = ClosureView(self)
        self.view_sim = SimulationView(self)

    def show_view(self, name: str):
        for v in (self.view_carriles, self.view_socios, self.view_cierre, self.view_sim):
            v.grid_forget()

        if name == "carriles":
            self.view_carriles.grid(row=0, column=1, padx=16, pady=16, sticky="nsew")
            self.view_carriles.refresh_lanes()
        elif name == "socios":
            self.view_socios.grid(row=0, column=1, padx=16, pady=16, sticky="nsew")
            self.view_socios.refresh_members()
        elif name == "cierre":
            self.view_cierre.grid(row=0, column=1, padx=16, pady=16, sticky="nsew")
        elif name == "sim":
            self.view_sim.grid(row=0, column=1, padx=16, pady=16, sticky="nsew")
