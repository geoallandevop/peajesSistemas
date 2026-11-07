-- ============================================================================
-- SISTEMA DE GESTIÓN DE PEAJES WEB Y SIMULACIÓN DE EVENTOS DISCRETOS (DES)
-- SCRIPT DDL COMPLETO PARA MICROSOFT SQL SERVER (T-SQL)
-- ============================================================================

-- 1. Creación de la Base de Datos (opcional si ya existe)
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'PeajesDB')
BEGIN
    CREATE DATABASE PeajesDB;
END
GO

USE PeajesDB;
GO

-- 2. Eliminar tablas existentes si se desea regenerar el esquema
IF OBJECT_ID(N'dbo.Transacciones', N'U') IS NOT NULL DROP TABLE dbo.Transacciones;
IF OBJECT_ID(N'dbo.CierresDiarios', N'U') IS NOT NULL DROP TABLE dbo.CierresDiarios;
IF OBJECT_ID(N'dbo.Vehiculos', N'U') IS NOT NULL DROP TABLE dbo.Vehiculos;
IF OBJECT_ID(N'dbo.Membresias', N'U') IS NOT NULL DROP TABLE dbo.Membresias;
IF OBJECT_ID(N'dbo.Carriles', N'U') IS NOT NULL DROP TABLE dbo.Carriles;
IF OBJECT_ID(N'dbo.Tarifas', N'U') IS NOT NULL DROP TABLE dbo.Tarifas;
GO

-- ============================================================================
-- ENTIDAD 1: TARIFAS (dbo.Tarifas)
-- Precios basados en tamaño/categoría y tiempos promedio de atención
-- ============================================================================
CREATE TABLE dbo.Tarifas (
    id INT IDENTITY(1,1) NOT NULL,
    category NVARCHAR(30) NOT NULL,
    description NVARCHAR(120) NOT NULL,
    regular_price DECIMAL(10,2) NOT NULL,
    member_price DECIMAL(10,2) NOT NULL,
    avg_service_seconds_cash INT NOT NULL DEFAULT 14,
    avg_service_seconds_card INT NOT NULL DEFAULT 9,
    avg_service_seconds_member INT NOT NULL DEFAULT 4,
    updated_at DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_Tarifas PRIMARY KEY CLUSTERED (id),
    CONSTRAINT UQ_Tarifas_Category UNIQUE (category),
    CONSTRAINT CK_Tarifas_Prices CHECK (regular_price >= 0 AND member_price >= 0),
    CONSTRAINT CK_Tarifas_Category CHECK (category IN (
        N'MOTO', N'LIVIANO', N'AUTOBUS', N'CAMION_2_EJES', N'CAMION_PESADO'
    ))
);
GO

-- ============================================================================
-- ENTIDAD 2: MEMBRESÍAS / SOCIOS (dbo.Membresias)
-- Código único, fechas de vencimiento y soporte de renovación
-- ============================================================================
CREATE TABLE dbo.Membresias (
    id INT IDENTITY(1,1) NOT NULL,
    member_code NVARCHAR(32) NOT NULL,
    owner_name NVARCHAR(120) NOT NULL,
    owner_email NVARCHAR(120) NOT NULL,
    national_id NVARCHAR(40) NOT NULL,
    status NVARCHAR(20) NOT NULL DEFAULT N'ACTIVA',
    created_at DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    expires_at DATETIME2(7) NOT NULL,
    last_renewed_at DATETIME2(7) NULL,
    renewal_count INT NOT NULL DEFAULT 0,

    CONSTRAINT PK_Membresias PRIMARY KEY CLUSTERED (id),
    CONSTRAINT UQ_Membresias_Code UNIQUE (member_code),
    CONSTRAINT UQ_Membresias_Email UNIQUE (owner_email),
    CONSTRAINT CK_Membresias_Status CHECK (status IN (N'ACTIVA', N'VENCIDA', N'SUSPENDIDA')),
    CONSTRAINT CK_Membresias_Renewal CHECK (renewal_count >= 0)
);
GO

CREATE NONCLUSTERED INDEX IX_Membresias_NationalId ON dbo.Membresias (national_id);
CREATE NONCLUSTERED INDEX IX_Membresias_Status ON dbo.Membresias (status, expires_at);
GO

-- ============================================================================
-- ENTIDAD 3: VEHÍCULOS (dbo.Vehiculos)
-- Padrón de placas y vinculación opcional con socios
-- ============================================================================
CREATE TABLE dbo.Vehiculos (
    id INT IDENTITY(1,1) NOT NULL,
    plate NVARCHAR(20) NOT NULL,
    category NVARCHAR(30) NOT NULL,
    brand_model NVARCHAR(100) NULL,
    membership_id INT NULL,
    registered_at DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_Vehiculos PRIMARY KEY CLUSTERED (id),
    CONSTRAINT UQ_Vehiculos_Plate UNIQUE (plate),
    CONSTRAINT FK_Vehiculos_Membresias FOREIGN KEY (membership_id) 
        REFERENCES dbo.Membresias(id) ON DELETE SET NULL,
    CONSTRAINT CK_Vehiculos_Category CHECK (category IN (
        N'MOTO', N'LIVIANO', N'AUTOBUS', N'CAMION_2_EJES', N'CAMION_PESADO'
    ))
);
GO

CREATE NONCLUSTERED INDEX IX_Vehiculos_Membership ON dbo.Vehiculos (membership_id);
GO

-- ============================================================================
-- ENTIDAD 4: CARRILES DE PEAJE (dbo.Carriles)
-- Vista Empleado: configuración, estados operativos y métricas acumuladas
-- ============================================================================
CREATE TABLE dbo.Carriles (
    id INT IDENTITY(1,1) NOT NULL,
    code NVARCHAR(20) NOT NULL,
    name NVARCHAR(80) NOT NULL,
    lane_type NVARCHAR(30) NOT NULL DEFAULT N'MIXTO',
    status NVARCHAR(20) NOT NULL DEFAULT N'ABIERTO',
    operator_name NVARCHAR(100) NULL,
    current_queue_length INT NOT NULL DEFAULT 0,
    total_processed INT NOT NULL DEFAULT 0,
    accumulated_wait_seconds FLOAT NOT NULL DEFAULT 0.0,
    accumulated_service_seconds FLOAT NOT NULL DEFAULT 0.0,

    CONSTRAINT PK_Carriles PRIMARY KEY CLUSTERED (id),
    CONSTRAINT UQ_Carriles_Code UNIQUE (code),
    CONSTRAINT CK_Carriles_Type CHECK (lane_type IN (N'MIXTO', N'EFECTIVO', N'EXCLUSIVO_MIEMBROS')),
    CONSTRAINT CK_Carriles_Status CHECK (status IN (N'ABIERTO', N'CERRADO', N'MANTENIMIENTO'))
);
GO

-- ============================================================================
-- ENTIDAD 5: CIERRES DIARIOS (dbo.CierresDiarios)
-- Cuadre de caja y desgloses analíticos en JSON
-- ============================================================================
CREATE TABLE dbo.CierresDiarios (
    id INT IDENTITY(1,1) NOT NULL,
    closure_date DATE NOT NULL,
    generated_at DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    closed_by NVARCHAR(100) NOT NULL,
    total_transactions INT NOT NULL DEFAULT 0,
    total_revenue DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    total_cash DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    total_card DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    total_discounts_granted DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    breakdown_by_category NVARCHAR(MAX) NOT NULL DEFAULT N'{}',
    breakdown_by_membership NVARCHAR(MAX) NOT NULL DEFAULT N'{}',
    breakdown_by_lane NVARCHAR(MAX) NOT NULL DEFAULT N'{}',

    CONSTRAINT PK_CierresDiarios PRIMARY KEY CLUSTERED (id),
    CONSTRAINT CK_CierresDiarios_Revenue CHECK (total_revenue >= 0)
);
GO

CREATE NONCLUSTERED INDEX IX_CierresDiarios_Date ON dbo.CierresDiarios (closure_date);
GO

-- ============================================================================
-- ENTIDAD 6: TRANSACCIONES (dbo.Transacciones)
-- Cruces reales y eventos procesados por la simulación
-- ============================================================================
CREATE TABLE dbo.Transacciones (
    id INT IDENTITY(1,1) NOT NULL,
    receipt_code NVARCHAR(40) NOT NULL,
    vehicle_id INT NULL,
    lane_id INT NOT NULL,
    membership_id INT NULL,
    daily_closure_id INT NULL,
    plate NVARCHAR(20) NOT NULL,
    vehicle_category NVARCHAR(30) NOT NULL,
    payment_method NVARCHAR(20) NOT NULL,
    has_active_membership BIT NOT NULL DEFAULT 0,
    regular_amount DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    amount_charged DECIMAL(10,2) NOT NULL,
    wait_time_seconds FLOAT NOT NULL DEFAULT 0.0,
    service_time_seconds FLOAT NOT NULL DEFAULT 0.0,
    is_simulated BIT NOT NULL DEFAULT 0,
    timestamp DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_Transacciones PRIMARY KEY CLUSTERED (id),
    CONSTRAINT UQ_Transacciones_Receipt UNIQUE (receipt_code),
    CONSTRAINT FK_Transacciones_Vehiculos FOREIGN KEY (vehicle_id) 
        REFERENCES dbo.Vehiculos(id) ON DELETE SET NULL,
    CONSTRAINT FK_Transacciones_Carriles FOREIGN KEY (lane_id) 
        REFERENCES dbo.Carriles(id),
    CONSTRAINT FK_Transacciones_Membresias FOREIGN KEY (membership_id) 
        REFERENCES dbo.Membresias(id) ON DELETE SET NULL,
    CONSTRAINT FK_Transacciones_CierresDiarios FOREIGN KEY (daily_closure_id) 
        REFERENCES dbo.CierresDiarios(id) ON DELETE SET NULL,
    CONSTRAINT CK_Transacciones_Payment CHECK (payment_method IN (N'EFECTIVO', N'TARJETA'))
);
GO

CREATE NONCLUSTERED INDEX IX_Transacciones_Timestamp ON dbo.Transacciones (timestamp);
CREATE NONCLUSTERED INDEX IX_Transacciones_Lane ON dbo.Transacciones (lane_id);
CREATE NONCLUSTERED INDEX IX_Transacciones_Closure ON dbo.Transacciones (daily_closure_id);
GO
