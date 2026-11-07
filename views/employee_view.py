from tkinter import messagebox
import customtkinter as ctk

from models.base import LaneStatus, PaymentMethod, VehicleCategory
from models.database import SessionLocal
from controllers.tariff_controller import calculate_toll_quote
from controllers.toll_controller import list_lanes, process_toll_payment, update_lane_status


class EmployeeView(ctk.CTkFrame):
    """
    Vista de Operación de Peaje para el Empleado / Cobro en Caseta.
    - Monitoreo y control de estado de carriles (Abrir, Cerrar, Poner en Mantenimiento).
    - Cobro de peaje en Quetzales (Q) con previsualización tipo tarjeta estilizada.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            self,
            text="🚗 Operación de Peaje - Vista de Empleado",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, columnspan=2, padx=16, pady=(12, 8), sticky="w")

        # ==========================================
        # Panel Izquierdo: Estado y Control de Carriles
        # ==========================================
        lanes_card = ctk.CTkFrame(self)
        lanes_card.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        lanes_card.grid_columnconfigure(0, weight=1)
        lanes_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            lanes_card,
            text="Estado de Carriles & Colas en Tiempo Real",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=10, sticky="w")

        self.lanes_scroll = ctk.CTkScrollableFrame(lanes_card)
        self.lanes_scroll.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkButton(
            lanes_card,
            text="🔄 Actualizar Carriles",
            command=self.refresh_lanes,
        ).grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # ==========================================
        # Panel Derecho: Registro de Cobro en Caseta
        # ==========================================
        pay_card = ctk.CTkFrame(self)
        pay_card.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        pay_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            pay_card,
            text="Registrar Cobro de Peaje",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=10, sticky="w")

        ctk.CTkLabel(pay_card, text="Carril:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.lane_option = ctk.CTkOptionMenu(pay_card, values=["1", "2", "3", "4"])
        self.lane_option.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(pay_card, text="Placa Vehículo:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.plate_entry = ctk.CTkEntry(pay_card, placeholder_text="Ej. P123ABC")
        self.plate_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(pay_card, text="Categoría:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.cat_option = ctk.CTkOptionMenu(
            pay_card,
            values=[c.value for c in VehicleCategory],
            command=lambda _: self.quote_rate(),
        )
        self.cat_option.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(pay_card, text="Método de Pago:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.pay_method_option = ctk.CTkOptionMenu(
            pay_card,
            values=[m.value for m in PaymentMethod],
        )
        self.pay_method_option.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(pay_card, text="Código Socio (Opcional):").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.member_code_entry = ctk.CTkEntry(pay_card, placeholder_text="Ej. MEM-2026-ACTIVO1")
        self.member_code_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkButton(
            pay_card,
            text="💲 Cotizar Tarifa en Caseta",
            fg_color="#4b5563",
            hover_color="#374151",
            command=self.quote_rate,
        ).grid(row=6, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.quote_label = ctk.CTkLabel(
            pay_card,
            text="Tarifa: Esperando cotización...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#60a5fa",
        )
        self.quote_label.grid(row=7, column=0, columnspan=2, padx=10, pady=2)

        ctk.CTkButton(
            pay_card,
            text="✅ Cobrar y Registrar Cruce",
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.submit_payment,
        ).grid(row=8, column=0, columnspan=2, padx=10, pady=8, sticky="ew")

        # TARJETA ESTILIZADA DE COMPROBANTE (Reemplaza la consola negra)
        self.ticket_card = ctk.CTkFrame(pay_card, fg_color="#1e293b", corner_radius=8)
        self.ticket_card.grid(row=9, column=0, columnspan=2, padx=10, pady=(4, 10), sticky="nsew")
        self.ticket_card.grid_columnconfigure(0, weight=1)

        self.ticket_title = ctk.CTkLabel(
            self.ticket_card,
            text="Comprobante de Cruce Generado",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#94a3b8",
        )
        self.ticket_title.pack(anchor="w", padx=12, pady=(8, 4))

        self.ticket_body = ctk.CTkLabel(
            self.ticket_card,
            text="Ningún cobro registrado en esta sesión.\nIngresa placa, categoría y haz clic en 'Cobrar y Registrar Cruce'.",
            justify="left",
            font=ctk.CTkFont(size=11),
            text_color="#cbd5e1",
        )
        self.ticket_body.pack(anchor="w", padx=12, pady=(0, 6))

        self.ticket_badge = ctk.CTkLabel(
            self.ticket_card,
            text="Monto: Q 0.00",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#34d399",
        )
        self.ticket_badge.pack(anchor="w", padx=12, pady=(0, 8))

    def refresh_lanes(self):
        for widget in self.lanes_scroll.winfo_children():
            widget.destroy()

        with SessionLocal() as db:
            lanes = list_lanes(db)
            self.lane_option.configure(values=[f"{l.id} - {l.code} ({l.lane_type.value})" for l in lanes])

            for l in lanes:
                card = ctk.CTkFrame(self.lanes_scroll, fg_color="#1e293b", corner_radius=8)
                card.pack(fill="x", padx=4, pady=5)

                if l.status == LaneStatus.ABIERTO:
                    status_color = "#34d399"
                elif l.status == LaneStatus.MANTENIMIENTO:
                    status_color = "#f59e0b"
                else:
                    status_color = "#f87171"

                # Cabecera del carril
                header_row = ctk.CTkFrame(card, fg_color="transparent")
                header_row.pack(fill="x", padx=8, pady=(6, 2))

                ctk.CTkLabel(
                    header_row,
                    text=f"ID {l.id} | {l.code}: {l.name}",
                    font=ctk.CTkFont(size=13, weight="bold"),
                ).pack(side="left")

                ctk.CTkLabel(
                    header_row,
                    text=f"● {l.status.value}",
                    text_color=status_color,
                    font=ctk.CTkFont(size=11, weight="bold"),
                ).pack(side="right")

                # Métricas operativas
                info = (
                    f"Tipo: {l.lane_type.value} | Operador: {l.operator_name or 'N/A'}\n"
                    f"Cola Actual: {l.current_queue_length} veh. | Procesados: {l.total_processed}"
                )
                ctk.CTkLabel(card, text=info, justify="left", text_color="#cbd5e1", font=ctk.CTkFont(size=11)).pack(
                    anchor="w", padx=8, pady=2
                )

                # BOTONES DE ACCIÓN: Cerrar, Inhabilitar / Mantenimiento, Abrir
                btn_row = ctk.CTkFrame(card, fg_color="transparent")
                btn_row.pack(fill="x", padx=8, pady=(4, 8))

                ctk.CTkButton(
                    btn_row,
                    text="Abrir",
                    width=65,
                    height=24,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color="#10b981" if l.status == LaneStatus.ABIERTO else "#334155",
                    command=lambda lid=l.id: self.change_lane_status(lid, LaneStatus.ABIERTO),
                ).pack(side="left", padx=2)

                ctk.CTkButton(
                    btn_row,
                    text="Cerrar",
                    width=65,
                    height=24,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color="#ef4444" if l.status == LaneStatus.CERRADO else "#334155",
                    command=lambda lid=l.id: self.change_lane_status(lid, LaneStatus.CERRADO),
                ).pack(side="left", padx=2)

                ctk.CTkButton(
                    btn_row,
                    text="Mantenimiento",
                    width=95,
                    height=24,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color="#f59e0b" if l.status == LaneStatus.MANTENIMIENTO else "#334155",
                    command=lambda lid=l.id: self.change_lane_status(lid, LaneStatus.MANTENIMIENTO),
                ).pack(side="left", padx=2)

    def change_lane_status(self, lane_id: int, new_status: LaneStatus):
        try:
            with SessionLocal() as db:
                update_lane_status(db, lane_id, new_status)
            self.refresh_lanes()
        except Exception as e:
            messagebox.showerror("Error al cambiar estado", str(e))

    def quote_rate(self):
        cat_str = self.cat_option.get()
        member_code = self.member_code_entry.get().strip() or None
        plate = self.plate_entry.get().strip() or None

        try:
            with SessionLocal() as db:
                quote = calculate_toll_quote(
                    db=db,
                    category=VehicleCategory(cat_str),
                    member_code=member_code,
                    plate=plate,
                )
                txt = (
                    f"Tarifa: Q {quote['final_price']:.2f} "
                    f"(Regular: Q {quote['regular_price']:.2f} | Descuento: Q {quote['discount_applied']:.2f})\n"
                    f"Estado Socio: {quote['membership_status_detail']}"
                )
                self.quote_label.configure(text=txt)
        except Exception as e:
            self.quote_label.configure(text=f"Error: {e}")

    def submit_payment(self):
        lane_str = self.lane_option.get()
        lane_id = int(lane_str.split(" - ")[0])
        plate = self.plate_entry.get().strip()
        cat_str = self.cat_option.get()
        method_str = self.pay_method_option.get()
        member_code = self.member_code_entry.get().strip() or None

        if not plate:
            messagebox.showwarning("Dato requerido", "Por favor ingresa la placa del vehículo.")
            return

        try:
            with SessionLocal() as db:
                tx = process_toll_payment(
                    db=db,
                    lane_id=lane_id,
                    plate=plate,
                    vehicle_category=VehicleCategory(cat_str),
                    payment_method=PaymentMethod(method_str),
                    member_code=member_code,
                )

                # Actualizar tarjeta estilizada de comprobante
                self.ticket_title.configure(text=f"Recibo: {tx.receipt_code}")
                body_txt = (
                    f"Fecha: {tx.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Carril ID: {tx.lane_id} | Placa: {tx.plate} ({tx.vehicle_category.value})\n"
                    f"Método de Pago: {tx.payment_method.value} | Tarifa Base: Q {tx.regular_amount:.2f}\n"
                    f"Descuento Membresía: Q {tx.discount_amount:.2f}"
                )
                self.ticket_body.configure(text=body_txt)
                self.ticket_badge.configure(text=f"TOTAL COBRADO: Q {tx.amount_charged:.2f}")

                messagebox.showinfo("Cobro Exitoso", f"Cruce cobrado con éxito!\nTotal: Q {tx.amount_charged:.2f}")
                self.refresh_lanes()
        except Exception as e:
            messagebox.showerror("Error en el Cobro", str(e))
