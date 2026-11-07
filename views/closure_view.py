import os
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

from models.database import SessionLocal
from controllers.toll_controller import generate_daily_closure
from controllers.pdf_generator import generate_closure_pdf


class ClosureView(ctk.CTkFrame):
    """
    Vista de Cierre Diario de Caja:
    - Previsualización en formato de hoja en blanco (documento formal de papel).
    - Descarga oficial del reporte en PDF (ReportLab).
    - Moneda oficial en Quetzales (Q) y exclusión total de la sección de ahorro.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)

        self.last_closure_data = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        title = ctk.CTkLabel(
            self,
            text="📊 Cierre Diario de Caja y Auditoría",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, padx=16, pady=(12, 8), sticky="w")

        # Barra de Botones
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=1, column=0, padx=16, pady=6, sticky="ew")

        self.btn_generate = ctk.CTkButton(
            btn_bar,
            text="📑 Generar Cierre Diario Consolidado",
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.execute_daily_closure,
        )
        self.btn_generate.pack(side="left", padx=(0, 10), pady=4)

        self.btn_pdf = ctk.CTkButton(
            btn_bar,
            text="📥 Descargar Cierre en PDF",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.download_pdf,
        )
        self.btn_pdf.pack(side="left", padx=4, pady=4)

        # CONTENEDOR TIPO HOJA EN BLANCO (Paper Sheet Preview)
        self.paper_container = ctk.CTkScrollableFrame(
            self,
            fg_color="#f8fafc",
            border_width=1,
            border_color="#cbd5e1",
            corner_radius=6,
        )
        self.paper_container.grid(row=2, column=0, padx=16, pady=(6, 16), sticky="nsew")

        # Texto interior en la hoja blanca
        self.paper_text = tk.Text(
            self.paper_container,
            wrap="word",
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#0f172a",
            relief="flat",
            font=("Consolas", 10),
            padx=20,
            pady=20,
        )
        self.paper_text.pack(fill="both", expand=True)
        self.paper_text.insert(
            tk.END,
            "================================================================================\n"
            "                 PREVISUALIZACIÓN DE HOJA DE CIERRE DIARIO                      \n"
            "================================================================================\n\n"
            "Haz clic en 'Generar Cierre Diario Consolidado' para cuadrar caja y ver el reporte.\n"
            "Podrás previsualizar el documento y exportarlo en formato PDF oficial.\n",
        )
        self.paper_text.config(state="disabled")

    def execute_daily_closure(self):
        try:
            with SessionLocal() as db:
                closure = generate_daily_closure(
                    db=db,
                    closed_by="Supervisor de Turno",
                    include_already_closed=True,
                )

                # Construir diccionario de datos para PDF y vista
                self.last_closure_data = {
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

                # Formato de hoja en blanco sin ahorro
                txt = (
                    "================================================================================\n"
                    "               SISTEMA DE GESTIÓN DE PEAJES - REPORTE DE CAJA                   \n"
                    "                         CIERRE DIARIO CONSOLIDADO                              \n"
                    "================================================================================\n"
                    f"Fecha de Cierre     : {closure.closure_date.isoformat()}\n"
                    f"Generado el         : {closure.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    f"Cerrado por         : {closure.closed_by}\n"
                    f"Total Transacciones : {closure.total_transactions} vehículos atendidos\n"
                    "--------------------------------------------------------------------------------\n"
                    f"RECAUDACIÓN TOTAL   : Q {closure.total_revenue:,.2f}\n"
                    f" - Total en Efectivo: Q {closure.total_cash:,.2f}\n"
                    f" - Total en Tarjeta : Q {closure.total_card:,.2f}\n"
                    "================================================================================\n"
                    "DISTRIBUCIÓN POR CATEGORÍA DE VEHÍCULO:\n"
                )
                for cat, d in closure.breakdown_by_category.items():
                    txt += (
                        f"  * {cat:<15}: {d['vehicles_count']:>3} veh. | "
                        f"Recaudado: Q {d['net_revenue']:>8.2f} (Efectivo: Q {d['cash_revenue']:>7.2f}, "
                        f"Tarjeta: Q {d['card_revenue']:>7.2f}) | Part: {d['share_of_revenue_pct']}%\n"
                    )

                txt += "--------------------------------------------------------------------------------\n"
                txt += "DISTRIBUCIÓN POR CONDICIÓN DE MEMBRESÍA:\n"
                for mem, d in closure.breakdown_by_membership.items():
                    txt += (
                        f"  * {mem:<25}: {d['vehicles_count']:>3} veh. | "
                        f"Recaudado: Q {d['net_revenue']:>8.2f} | "
                        f"Participación: {d['share_of_revenue_pct']}%\n"
                    )

                txt += "--------------------------------------------------------------------------------\n"
                txt += "DISTRIBUCIÓN POR CARRIL DE PEAJE:\n"
                for code, d in closure.breakdown_by_lane.items():
                    txt += (
                        f"  * {code:<10} ({d['lane_name']}): {d['vehicles_count']:>3} veh. | "
                        f"Recaudado: Q {d['net_revenue']:>8.2f} | Espera Prom: {d['avg_wait_seconds']}s\n"
                    )
                txt += (
                    "================================================================================\n"
                    "                     DOCUMENTO CONTABLE OFICIAL GENERADO                        \n"
                    "================================================================================\n"
                )

                self.paper_text.config(state="normal")
                self.paper_text.delete("1.0", tk.END)
                self.paper_text.insert(tk.END, txt)
                self.paper_text.config(state="disabled")

                messagebox.showinfo("Cierre Generado", f"Cierre generado con éxito!\nTotal Recaudado: Q {closure.total_revenue:,.2f}")
        except Exception as e:
            messagebox.showerror("Error en Cierre Diario", str(e))

    def download_pdf(self):
        if not self.last_closure_data:
            messagebox.showwarning("Atención", "Por favor genera primero el cierre diario antes de descargar el PDF.")
            return

        fecha = self.last_closure_data.get("closure_date", "hoy")
        filepath = filedialog.asksaveasfilename(
            title="Guardar Cierre Diario en PDF",
            defaultextension=".pdf",
            filetypes=[("Archivos PDF", "*.pdf")],
            initialfile=f"Cierre_Diario_{fecha}.pdf",
        )
        if not filepath:
            return

        try:
            generate_closure_pdf(self.last_closure_data, filepath)
            messagebox.showinfo(
                "PDF Generado",
                f"El reporte de cierre diario fue generado exitosamente en:\n{filepath}",
            )
        except Exception as e:
            messagebox.showerror("Error al generar PDF", str(e))
