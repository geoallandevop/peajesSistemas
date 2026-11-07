import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

from models.database import SessionLocal
from controllers.simulation_engine import DiscreteEventTollSimulator
from controllers.pdf_generator import generate_simulation_pdf


class SimulationView(ctk.CTkFrame):
    """
    Vista del Motor de Simulación de Eventos Discretos (DES):
    - Nuevos parámetros: Densidad de tráfico, Tiempos de verde en semáforos, Porcentajes por categoría y Duración.
    - Previsualización en formato de hoja blanca estilo documento PDF.
    - Descarga oficial de reporte en PDF con ReportLab.
    - Valores monetarios en Quetzales (Q).
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)

        self.last_sim_data = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            self,
            text="⏱️ Motor de Simulación de Eventos Discretos (DES)",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, columnspan=2, padx=16, pady=(12, 8), sticky="w")

        # ==========================================
        # Panel Izquierdo: Configuración de Parámetros
        # ==========================================
        ctrl_card = ctk.CTkScrollableFrame(self)
        ctrl_card.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        ctrl_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            ctrl_card,
            text="Parámetros de Simulación",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=8, pady=(4, 10), sticky="w")

        # 1. Densidad de Tráfico
        ctk.CTkLabel(ctrl_card, text="Densidad de Tráfico:").grid(row=1, column=0, padx=8, pady=5, sticky="w")
        self.density_menu = ctk.CTkOptionMenu(
            ctrl_card,
            values=[
                "Media (Tráfico Regular)",
                "Baja (Hora Valle)",
                "Alta (Hora Pico)",
                "Extrema (Congestión)",
            ],
        )
        self.density_menu.grid(row=1, column=1, padx=8, pady=5, sticky="ew")

        # 2. Tiempo de Verde en Semáforos (segundos)
        ctk.CTkLabel(ctrl_card, text="Tiempo Verde Semáforo (s):").grid(row=2, column=0, padx=8, pady=5, sticky="w")
        self.green_entry = ctk.CTkEntry(ctrl_card)
        self.green_entry.insert(0, "15")
        self.green_entry.grid(row=2, column=1, padx=8, pady=5, sticky="ew")

        # 3. Duración en Minutos
        ctk.CTkLabel(ctrl_card, text="Duración (Minutos):").grid(row=3, column=0, padx=8, pady=5, sticky="w")
        self.duration_entry = ctk.CTkEntry(ctrl_card)
        self.duration_entry.insert(0, "5")
        self.duration_entry.grid(row=3, column=1, padx=8, pady=5, sticky="ew")

        # 4. Sección de Porcentajes de Tipos de Vehículos
        ctk.CTkLabel(
            ctrl_card,
            text="Distribución Vehicular (%):",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=4, column=0, columnspan=2, padx=8, pady=(12, 4), sticky="w")

        ctk.CTkLabel(ctrl_card, text="% Vehículos Livianos:").grid(row=5, column=0, padx=8, pady=3, sticky="w")
        self.pct_liviano = ctk.CTkEntry(ctrl_card)
        self.pct_liviano.insert(0, "50")
        self.pct_liviano.grid(row=5, column=1, padx=8, pady=3, sticky="ew")

        ctk.CTkLabel(ctrl_card, text="% Motocicletas:").grid(row=6, column=0, padx=8, pady=3, sticky="w")
        self.pct_moto = ctk.CTkEntry(ctrl_card)
        self.pct_moto.insert(0, "20")
        self.pct_moto.grid(row=6, column=1, padx=8, pady=3, sticky="ew")

        ctk.CTkLabel(ctrl_card, text="% Autobuses:").grid(row=7, column=0, padx=8, pady=3, sticky="w")
        self.pct_bus = ctk.CTkEntry(ctrl_card)
        self.pct_bus.insert(0, "10")
        self.pct_bus.grid(row=7, column=1, padx=8, pady=3, sticky="ew")

        ctk.CTkLabel(ctrl_card, text="% Camiones 2 Ejes:").grid(row=8, column=0, padx=8, pady=3, sticky="w")
        self.pct_cam2 = ctk.CTkEntry(ctrl_card)
        self.pct_cam2.insert(0, "12")
        self.pct_cam2.grid(row=8, column=1, padx=8, pady=3, sticky="ew")

        ctk.CTkLabel(ctrl_card, text="% Camiones Pesados:").grid(row=9, column=0, padx=8, pady=3, sticky="w")
        self.pct_campes = ctk.CTkEntry(ctrl_card)
        self.pct_campes.insert(0, "8")
        self.pct_campes.grid(row=9, column=1, padx=8, pady=3, sticky="ew")

        # Botón Iniciar Simulación
        ctk.CTkButton(
            ctrl_card,
            text="▶️ Iniciar Simulación DES",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.execute_simulation,
        ).grid(row=10, column=0, columnspan=2, padx=8, pady=(16, 6), sticky="ew")

        # Botón Descargar PDF
        ctk.CTkButton(
            ctrl_card,
            text="📥 Descargar Reporte en PDF",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.download_pdf,
        ).grid(row=11, column=0, columnspan=2, padx=8, pady=6, sticky="ew")

        # ==========================================
        # Panel Derecho: Previsualización de Hoja en Blanco
        # ==========================================
        res_card = ctk.CTkFrame(self)
        res_card.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        res_card.grid_columnconfigure(0, weight=1)
        res_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            res_card,
            text="Previsualización de Documento de Simulación (Estilo Hoja PDF)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=8, sticky="w")

        # Contenedor tipo hoja de papel blanco
        self.paper_frame = ctk.CTkScrollableFrame(
            res_card,
            fg_color="#f8fafc",
            border_width=1,
            border_color="#cbd5e1",
            corner_radius=6,
        )
        self.paper_frame.grid(row=1, column=0, padx=10, pady=(4, 10), sticky="nsew")

        self.paper_text = tk.Text(
            self.paper_frame,
            wrap="word",
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#0f172a",
            relief="flat",
            font=("Consolas", 10),
            padx=18,
            pady=18,
        )
        self.paper_text.pack(fill="both", expand=True)
        self.paper_text.insert(
            tk.END,
            "================================================================================\n"
            "             PREVISUALIZACIÓN DE INFORME EJECUTIVO DE SIMULACIÓN DES            \n"
            "================================================================================\n\n"
            "Configura las variables de entrada a la izquierda y presiona 'Iniciar Simulación DES'.\n"
            "El sistema calculará las métricas acumuladas, rendimiento, finanzas y estadísticas por carril.\n",
        )
        self.paper_text.config(state="disabled")

    def execute_simulation(self):
        try:
            density = self.density_menu.get()
            green_s = int(self.green_entry.get().strip() or "15")
            duration_m = int(self.duration_entry.get().strip() or "5")
            p_liv = float(self.pct_liviano.get().strip() or "50")
            p_mot = float(self.pct_moto.get().strip() or "20")
            p_bus = float(self.pct_bus.get().strip() or "10")
            p_c2 = float(self.pct_cam2.get().strip() or "12")
            p_cpes = float(self.pct_campes.get().strip() or "8")

            with SessionLocal() as db:
                sim = DiscreteEventTollSimulator(
                    db=db,
                    traffic_density=density,
                    traffic_light_green_seconds=green_s,
                    duration_minutes=duration_m,
                    pct_liviano=p_liv,
                    pct_moto=p_mot,
                    pct_autobus=p_bus,
                    pct_camion_2_ejes=p_c2,
                    pct_camion_pesado=p_cpes,
                    persist_to_db=True,
                )
                res = sim.run()
                self.last_sim_data = res

                # Formatear salida con la estructura exacta solicitada por el usuario
                txt = (
                    "================================================================================\n"
                    "         SISTEMA DE GESTIÓN DE PEAJES - INFORME EJECUTIVO DE SIMULACIÓN         \n"
                    "================================================================================\n"
                    f"ID de Simulación       : {res['simulation_id']}\n"
                    f"Densidad de Tráfico    : {res['traffic_density']}\n"
                    f"Tiempo Verde Semáforo  : {res['traffic_light_green_seconds']} segundos\n"
                    f"Ciclos Ejecutados      : {res['total_cycles']} ({res['horizon_cycles']}s Horizonte + {res['drain_cycles']}s Drenado)\n"
                    f"Distribución Vehicular : {res['vehicle_distribution_summary']}\n"
                    "--------------------------------------------------------------------------------\n"
                    "MÉTRICAS ACUMULADAS Y RENDIMIENTO:\n"
                    f"  * Tiempo de Espera Medio : {res['avg_wait_time_seconds']:.2f} segundos\n"
                    f"  * Espera Máxima          : {res['max_wait_time_seconds']:.2f} segundos\n"
                    f"  * Tiempo Medio de Atención: {res['avg_service_time_seconds']:.2f} segundos\n"
                    f"  * El flujo vehicular por Minuto  : {res['throughput_vehicles_per_minute']:.2f} veh/min\n"
                    f"  * El flujo vehicular por Hora    : {res['throughput_vehicles_per_hour']:.2f} veh/hora\n"
                    "--------------------------------------------------------------------------------\n"
                    "FINANZAS DE LA SIMULACIÓN:\n"
                    f"  * Recaudación Total      : Q {res['total_revenue']:,.2f}\n"
                    f"  * Descuentos Socios      : Q {res['total_discounts']:,.2f}\n"
                    f"  * Efectivo               : Q {res['total_cash']:,.2f}\n"
                    f"  * Tarjeta                : Q {res['total_card']:,.2f}\n"
                    "--------------------------------------------------------------------------------\n"
                    "ESTADÍSTICAS POR CARRIL:\n"
                )
                for lm in res["lane_metrics"]:
                    txt += (
                        f"  * [{lm['code']}] ({lm['lane_type']:<18}): {lm['processed']:>3} veh. | "
                        f"Espera: {lm['avg_wait']:>6.2f}s | Atención: {lm['avg_srv']:>5.2f}s | "
                        f"Cola Máx: {lm['max_queue']:>2} | Ocupación: {lm['utilization']:>5.1f}% | "
                        f"Recaudado: Q {lm['revenue']:>8.2f}\n"
                    )

                txt += (
                    "--------------------------------------------------------------------------------\n"
                    f"LEY DE CONSERVACIÓN: {res['conservation_equation']}\n"
                    f"PÉRDIDA CERO (0)   : {'VERIFICADA EXITOSAMENTE (100% de vehículos atendidos)' if res['zero_loss_verified'] else 'FALLÓ'}\n"
                    "================================================================================\n"
                )

                self.paper_text.config(state="normal")
                self.paper_text.delete("1.0", tk.END)
                self.paper_text.insert(tk.END, txt)
                self.paper_text.config(state="disabled")

                messagebox.showinfo(
                    "Simulación Completa",
                    f"Simulación ejecutada con éxito!\n{res['total_vehicles_completed']} vehículos procesados con CERO pérdida.",
                )
        except Exception as e:
            messagebox.showerror("Error en Simulación", str(e))

    def download_pdf(self):
        if not self.last_sim_data:
            messagebox.showwarning("Atención", "Por favor ejecuta la simulación antes de descargar el PDF.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Guardar Informe de Simulación en PDF",
            defaultextension=".pdf",
            filetypes=[("Archivos PDF", "*.pdf")],
            initialfile=f"Simulacion_DES_{self.last_sim_data.get('simulation_id', 'reporte')}.pdf",
        )
        if not filepath:
            return

        try:
            generate_simulation_pdf(self.last_sim_data, filepath)
            messagebox.showinfo(
                "PDF Generado",
                f"El informe ejecutivo en PDF fue generado exitosamente en:\n{filepath}",
            )
        except Exception as e:
            messagebox.showerror("Error al generar PDF", str(e))
