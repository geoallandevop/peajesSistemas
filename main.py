"""
Punto de Entrada Principal - Sistema de Gestión de Peajes (Aplicación de Escritorio).
Desarrollada con CustomTkinter y Microsoft SQL Server / SQLite.
"""
from views import MainWindow


def main():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
