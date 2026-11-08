-- ============================================================
-- 01_ddl.sql | MODELO MULTIDIMENSIONAL EN ESTRELLA (BD_UBER_INDIA)
-- Metodología Ralph Kimball - SCD Tipo 1
-- Reproducible: elimina y recrea las tablas (fact primero, por FK).
-- ============================================================

DROP TABLE IF EXISTS Fact_Bookings   CASCADE;
DROP TABLE IF EXISTS Dim_Tiempo      CASCADE;
DROP TABLE IF EXISTS Dim_Vehiculo    CASCADE;
DROP TABLE IF EXISTS Dim_MetodoPago  CASCADE;
DROP TABLE IF EXISTS Dim_Cancelacion CASCADE;

-- 1. Dimensión Tiempo (Time_SK = YYYYMMDDHH, la genera el ETL)
CREATE TABLE Dim_Tiempo (
    Time_SK INT PRIMARY KEY,
    Fecha DATE NOT NULL,
    Anio INT NOT NULL,
    Mes INT NOT NULL,
    Nombre_Mes VARCHAR(20) NOT NULL,
    Dia INT NOT NULL,
    Dia_Semana VARCHAR(20) NOT NULL,
    Hora INT NOT NULL,
    Franja_Horaria VARCHAR(30) NOT NULL,
    CONSTRAINT ck_tiempo_mes    CHECK (Mes  BETWEEN 1 AND 12),
    CONSTRAINT ck_tiempo_dia    CHECK (Dia  BETWEEN 1 AND 31),
    CONSTRAINT ck_tiempo_hora   CHECK (Hora BETWEEN 0 AND 23),
    CONSTRAINT ck_tiempo_franja CHECK (Franja_Horaria IN ('Madrugada','Mañana','Tarde','Noche'))
);

-- 2. Dimensión Vehículo
CREATE TABLE Dim_Vehiculo (
    Vehicle_SK SERIAL PRIMARY KEY,
    Vehicle_Type VARCHAR(30) NOT NULL,
    Business_Line VARCHAR(30) NOT NULL,
    CONSTRAINT uq_vehiculo_tipo  UNIQUE (Vehicle_Type),
    CONSTRAINT ck_vehiculo_linea CHECK (Business_Line IN ('Liviana','Estándar','Premium'))
);

-- 3. Dimensión Método de Pago (SK 0 = N/A, se siembra en 02_seed.sql)
CREATE TABLE Dim_MetodoPago (
    Payment_SK SERIAL PRIMARY KEY,
    Payment_Method VARCHAR(30) NOT NULL,
    CONSTRAINT uq_metodopago UNIQUE (Payment_Method)
);

-- 4. Dimensión Cancelación (SK 0..4 centinelas, se siembran en 02_seed.sql)
CREATE TABLE Dim_Cancelacion (
    Cancellation_SK SERIAL PRIMARY KEY,
    Cancelled_By VARCHAR(30) NOT NULL,
    Cancellation_Reason VARCHAR(255) NOT NULL,
    CONSTRAINT uq_cancelacion UNIQUE (Cancelled_By, Cancellation_Reason)
);

-- 5. Tabla de Hechos Central (grano: una fila por solicitud de viaje)
CREATE TABLE Fact_Bookings (
    Booking_ID VARCHAR(20) PRIMARY KEY,     -- Clave Natural (NK)

    Time_SK INT NOT NULL,
    Vehicle_SK INT NOT NULL,
    Payment_SK INT NOT NULL,
    Cancellation_SK INT NOT NULL,

    Booking_Status VARCHAR(30) NOT NULL,
    Customer_ID VARCHAR(20) NOT NULL,       -- Dimensión degenerada

    Booking_Value DECIMAL(10,2),            -- Métrica 1/3 (INR)
    Ride_Distance FLOAT,                    -- Métrica 2/3 (km)
    Avg_VTAT FLOAT,                         -- Métrica 3/3 (min)

    CONSTRAINT fk_fact_tiempo      FOREIGN KEY (Time_SK)         REFERENCES Dim_Tiempo (Time_SK),
    CONSTRAINT fk_fact_vehiculo    FOREIGN KEY (Vehicle_SK)      REFERENCES Dim_Vehiculo (Vehicle_SK),
    CONSTRAINT fk_fact_pago        FOREIGN KEY (Payment_SK)      REFERENCES Dim_MetodoPago (Payment_SK),
    CONSTRAINT fk_fact_cancelacion FOREIGN KEY (Cancellation_SK) REFERENCES Dim_Cancelacion (Cancellation_SK),

    -- Estados válidos y rangos de los Quality Gates (NULL pasa los CHECK)
    CONSTRAINT ck_fact_status   CHECK (Booking_Status IN ('Completed','Cancelled by Customer',
                                       'Cancelled by Driver','Incomplete','No Driver Found')),
    CONSTRAINT ck_fact_value    CHECK (Booking_Value BETWEEN 0 AND 10000),
    CONSTRAINT ck_fact_distance CHECK (Ride_Distance BETWEEN 0.1 AND 500),
    CONSTRAINT ck_fact_vtat     CHECK (Avg_VTAT      BETWEEN 0 AND 120)
);

CREATE INDEX ix_fact_time         ON Fact_Bookings (Time_SK);
CREATE INDEX ix_fact_vehicle      ON Fact_Bookings (Vehicle_SK);
CREATE INDEX ix_fact_payment      ON Fact_Bookings (Payment_SK);
CREATE INDEX ix_fact_cancellation ON Fact_Bookings (Cancellation_SK);
CREATE INDEX ix_fact_customer     ON Fact_Bookings (Customer_ID);
