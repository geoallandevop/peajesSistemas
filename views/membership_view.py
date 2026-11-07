from tkinter import messagebox
import customtkinter as ctk

from models.database import SessionLocal
from controllers.membership_controller import create_member, list_members, renew_member


class MembershipView(ctk.CTkFrame):
    """
    Vista de Socios y Membresías:
    - Registro de nuevos socios con DPI y código único.
    - Renovación de membresías vencidas.
    - Padrón con botones para copiar código y correo al portapapeles.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            self,
            text="💳 Gestión de Membresías y Socios",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, columnspan=2, padx=16, pady=(12, 8), sticky="w")

        # ==========================================
        # Panel Izquierdo: Formularios
        # ==========================================
        form_card = ctk.CTkFrame(self)
        form_card.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        form_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            form_card,
            text="Registrar Nuevo Socio",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=10, sticky="w")

        ctk.CTkLabel(form_card, text="Nombre:").grid(row=1, column=0, padx=10, pady=6, sticky="w")
        self.mem_name = ctk.CTkEntry(form_card, placeholder_text="María Rodríguez")
        self.mem_name.grid(row=1, column=1, padx=10, pady=6, sticky="ew")

        ctk.CTkLabel(form_card, text="Correo:").grid(row=2, column=0, padx=10, pady=6, sticky="w")
        self.mem_email = ctk.CTkEntry(form_card, placeholder_text="maria@ejemplo.com")
        self.mem_email.grid(row=2, column=1, padx=10, pady=6, sticky="ew")

        # Cambiado de DNI a DPI
        ctk.CTkLabel(form_card, text="Identificación / DPI:").grid(row=3, column=0, padx=10, pady=6, sticky="w")
        self.mem_dpi = ctk.CTkEntry(form_card, placeholder_text="1234567890123")
        self.mem_dpi.grid(row=3, column=1, padx=10, pady=6, sticky="ew")

        ctk.CTkLabel(form_card, text="Vigencia (Días):").grid(row=4, column=0, padx=10, pady=6, sticky="w")
        self.mem_days = ctk.CTkEntry(form_card)
        self.mem_days.insert(0, "30")
        self.mem_days.grid(row=4, column=1, padx=10, pady=6, sticky="ew")

        ctk.CTkButton(
            form_card,
            text="➕ Crear Socio y Generar Código",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            font=ctk.CTkFont(weight="bold"),
            command=self.submit_create_member,
        ).grid(row=5, column=0, columnspan=2, padx=10, pady=12, sticky="ew")

        # Renovación de Membresía
        ctk.CTkLabel(
            form_card,
            text="Renovación de Membresía Vencida o Próxima a Vencer",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=6, column=0, columnspan=2, padx=12, pady=(18, 6), sticky="w")

        ctk.CTkLabel(form_card, text="Código Socio:").grid(row=7, column=0, padx=10, pady=6, sticky="w")
        self.renew_code = ctk.CTkEntry(form_card, placeholder_text="MEM-2026-VENCID2")
        self.renew_code.grid(row=7, column=1, padx=10, pady=6, sticky="ew")

        ctk.CTkLabel(form_card, text="Días a Renovar:").grid(row=8, column=0, padx=10, pady=6, sticky="w")
        self.renew_days = ctk.CTkEntry(form_card)
        self.renew_days.insert(0, "30")
        self.renew_days.grid(row=8, column=1, padx=10, pady=6, sticky="ew")

        ctk.CTkButton(
            form_card,
            text="🔄 Renovar Membresía",
            fg_color="#f59e0b",
            hover_color="#d97706",
            font=ctk.CTkFont(weight="bold"),
            command=self.submit_renew_member,
        ).grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # ==========================================
        # Panel Derecho: Padrón de Socios
        # ==========================================
        list_card = ctk.CTkFrame(self)
        list_card.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        list_card.grid_columnconfigure(0, weight=1)
        list_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            list_card,
            text="Padrón de Socios & Estado de Vigencia",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=10, sticky="w")

        self.members_scroll = ctk.CTkScrollableFrame(list_card)
        self.members_scroll.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkButton(
            list_card,
            text="🔄 Recargar Lista de Socios",
            command=self.refresh_members,
        ).grid(row=2, column=0, padx=10, pady=10, sticky="ew")

    def copy_to_clipboard(self, text: str, label_name: str):
        """Copia el texto al portapapeles de Windows."""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
            messagebox.showinfo("Copiado", f"¡{label_name} copiado al portapapeles!\n\n{text}")
        except Exception as e:
            messagebox.showerror("Error al copiar", str(e))

    def refresh_members(self):
        for widget in self.members_scroll.winfo_children():
            widget.destroy()

        with SessionLocal() as db:
            members = list_members(db)
            for m in members:
                is_active = m.is_currently_active()
                card = ctk.CTkFrame(self.members_scroll, fg_color="#1e293b", corner_radius=8)
                card.pack(fill="x", padx=4, pady=5)

                badge_color = "#34d399" if is_active else "#f87171"

                # Encabezado del socio
                top_row = ctk.CTkFrame(card, fg_color="transparent")
                top_row.pack(fill="x", padx=8, pady=(6, 2))

                ctk.CTkLabel(
                    top_row,
                    text=f"Código: {m.member_code}",
                    font=ctk.CTkFont(size=12, weight="bold"),
                ).pack(side="left")

                ctk.CTkLabel(
                    top_row,
                    text=f"● {m.status.value} ({'VIGENTE' if is_active else 'VENCIDA'})",
                    text_color=badge_color,
                    font=ctk.CTkFont(size=11, weight="bold"),
                ).pack(side="right")

                # Información con DPI
                info_text = (
                    f"Propietario: {m.owner_name}\n"
                    f"Correo: {m.owner_email} | DPI: {m.national_id}\n"
                    f"Vence: {m.expires_at.date().isoformat()} | Renovaciones: {m.renewal_count}"
                )
                ctk.CTkLabel(card, text=info_text, justify="left", font=ctk.CTkFont(size=11), text_color="#cbd5e1").pack(
                    anchor="w", padx=8, pady=2
                )

                # BOTONES PARA COPIAR CÓDIGO Y CORREO
                btn_row = ctk.CTkFrame(card, fg_color="transparent")
                btn_row.pack(fill="x", padx=8, pady=(4, 6))

                ctk.CTkButton(
                    btn_row,
                    text="📋 Copiar Código",
                    width=100,
                    height=24,
                    font=ctk.CTkFont(size=10),
                    fg_color="#334155",
                    hover_color="#475569",
                    command=lambda code=m.member_code: self.copy_to_clipboard(code, "Código de Socio"),
                ).pack(side="left", padx=(0, 6))

                ctk.CTkButton(
                    btn_row,
                    text="📋 Copiar Correo",
                    width=100,
                    height=24,
                    font=ctk.CTkFont(size=10),
                    fg_color="#334155",
                    hover_color="#475569",
                    command=lambda mail=m.owner_email: self.copy_to_clipboard(mail, "Correo del Socio"),
                ).pack(side="left")

    def submit_create_member(self):
        name = self.mem_name.get().strip()
        email = self.mem_email.get().strip()
        dpi = self.mem_dpi.get().strip()
        days = int(self.mem_days.get().strip() or "30")

        if not name or not email or not dpi:
            messagebox.showwarning("Campos Requeridos", "Por favor completa todos los campos del socio (Nombre, Correo, DPI).")
            return

        try:
            with SessionLocal() as db:
                new_m = create_member(
                    db=db,
                    owner_name=name,
                    owner_email=email,
                    national_id=dpi,
                    duration_days=days,
                )
                messagebox.showinfo(
                    "Socio Creado",
                    f"Socio creado exitosamente!\nCódigo Único: {new_m.member_code}\nVence: {new_m.expires_at.date()}",
                )
                self.refresh_members()
        except Exception as e:
            messagebox.showerror("Error al crear socio", str(e))

    def submit_renew_member(self):
        code = self.renew_code.get().strip()
        days = int(self.renew_days.get().strip() or "30")

        if not code:
            messagebox.showwarning("Código Requerido", "Ingresa el código del socio a renovar.")
            return

        try:
            with SessionLocal() as db:
                m_renewed = renew_member(db=db, member_code=code, duration_days=days)
                messagebox.showinfo(
                    "Renovación Exitosa",
                    f"Membresía {m_renewed.member_code} renovada con éxito!\nNuevo Vencimiento: {m_renewed.expires_at.date()}\nEstado: {m_renewed.status.value}",
                )
                self.refresh_members()
        except Exception as e:
            messagebox.showerror("Error al renovar", str(e))
