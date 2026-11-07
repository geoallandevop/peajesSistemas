-- ============================================================================
-- DATOS SEMILLA PARA MICROSOFT SQL SERVER (PeajesDB)
-- ============================================================================
USE PeajesDB;
GO

-- 1. Insertar Tarifas por Categoría
IF NOT EXISTS (SELECT 1 FROM dbo.Tarifas)
BEGIN
    INSERT INTO dbo.Tarifas (category, description, regular_price, member_price, avg_service_seconds_cash, avg_service_seconds_card, avg_service_seconds_member)
    VALUES
        (N'MOTO', N'Motocicletas y tricimoto', 1.50, 1.00, 10, 7, 3),
        (N'LIVIANO', N'Automóviles, SUVs y Pickups livianas', 3.00, 2.10, 14, 9, 4),
        (N'AUTOBUS', N'Autobuses de transporte público y turismo', 6.00, 4.50, 18, 11, 5),
        (N'CAMION_2_EJES', N'Camiones de carga mediana (2 ejes)', 8.50, 6.50, 20, 12, 6),
        (N'CAMION_PESADO', N'Tractocamiones y vehículos articulados (3+ ejes)', 14.00, 10.50, 25, 15, 7);
END
GO

-- 2. Insertar Carriles Iniciales
IF NOT EXISTS (SELECT 1 FROM dbo.Carriles)
BEGIN
    INSERT INTO dbo.Carriles (code, name, lane_type, status, operator_name)
    VALUES
        (N'CARRIL-01', N'Carril 1 - Efectivo / Manual', N'EFECTIVO', N'ABIERTO', N'Carlos Méndez'),
        (N'CARRIL-02', N'Carril 2 - Mixto Estándar', N'MIXTO', N'ABIERTO', N'Ana Gómez'),
        (N'CARRIL-03', N'Carril 3 - Mixto Rápido', N'MIXTO', N'ABIERTO', N'Luis Herrera'),
        (N'CARRIL-04', N'Carril 4 - Telepeaje Exclusivo Socios', N'EXCLUSIVO_MIEMBROS', N'ABIERTO', N'Sistema Automático RFID');
END
GO

-- 3. Insertar Membresías de Prueba (1 Activa y 1 Vencida para probar renovación)
IF NOT EXISTS (SELECT 1 FROM dbo.Membresias)
BEGIN
    INSERT INTO dbo.Membresias (member_code, owner_name, owner_email, national_id, status, created_at, expires_at, renewal_count)
    VALUES
        (N'MEM-2026-ACTIVO1', N'Laura Fernández', N'laura.fernandez@ejemplo.com', N'1029384756', N'ACTIVA', DATEADD(DAY, -10, SYSUTCDATETIME()), DATEADD(DAY, 20, SYSUTCDATETIME()), 0),
        (N'MEM-2026-VENCID2', N'Roberto Castillo', N'roberto.castillo@ejemplo.com', N'5049382716', N'VENCIDA', DATEADD(DAY, -45, SYSUTCDATETIME()), DATEADD(DAY, -15, SYSUTCDATETIME()), 1);

    DECLARE @ActiveId INT = (SELECT id FROM dbo.Membresias WHERE member_code = N'MEM-2026-ACTIVO1');
    DECLARE @ExpiredId INT = (SELECT id FROM dbo.Membresias WHERE member_code = N'MEM-2026-VENCID2');

    INSERT INTO dbo.Vehiculos (plate, category, brand_model, membership_id)
    VALUES
        (N'ABC-123', N'LIVIANO', N'Toyota Corolla 2024', @ActiveId),
        (N'EXP-999', N'CAMION_2_EJES', N'Hino Serie 500', @ExpiredId);
END
GO
