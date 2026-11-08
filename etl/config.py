"""Configuración central del ETL: rutas, conexión, rangos, catálogos y SKs centinela."""
import os
from pathlib import Path
from urllib.parse import quote_plus

# ---------------------------------------------------------------- Rutas
RAIZ = Path(__file__).resolve().parent.parent
CSV_ORIGEN = RAIZ / "data" / "raw" / "uber_india_2024.csv"
DIR_STAGING = RAIZ / "data" / "staging"
DIR_PROCESSED = RAIZ / "data" / "processed"
DIR_LOGS = RAIZ / "logs"

# ---------------------------------------------------------------- Base de datos
# Se leen de variables de entorno para no dejar la contraseña en el repo.
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "BD_UBER_INDIA")   # ojo: Postgres distingue mayúsculas si se creó con comillas
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

# True si el DDL creó tablas/columnas sin comillas (Postgres las guarda en minúscula)
NOMBRES_EN_MINUSCULAS = True


def url_conexion() -> str:
    return (f"postgresql+psycopg2://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@{DB_HOST}:{DB_PORT}/{DB_NAME}")


# ---------------------------------------------------------------- Origen
# Las 13 columnas del origen que entran al DW (Tabla 6). Los espacios se normalizan a "_".
COLUMNAS_ORIGEN = [
    "Date", "Time", "Booking_ID", "Booking_Status", "Customer_ID", "Vehicle_Type",
    "Avg_VTAT", "Reason_for_cancelling_by_Customer", "Driver_Cancellation_Reason",
    "Incomplete_Rides_Reason", "Booking_Value", "Ride_Distance", "Payment_Method",
]
COL_MOTIVO_CLIENTE = "Reason_for_cancelling_by_Customer"
COL_MOTIVO_CONDUCTOR = "Driver_Cancellation_Reason"
COL_MOTIVO_INCOMPLETO = "Incomplete_Rides_Reason"
METRICAS = ["Booking_Value", "Ride_Distance", "Avg_VTAT"]

# ---------------------------------------------------------------- Quality Gates (Tabla 8)
RANGOS = {
    "Booking_Value": (0, 10_000),    # INR
    "Ride_Distance": (0.1, 500),     # km
    "Avg_VTAT": (0, 120),            # minutos
}

# ---------------------------------------------------------------- Duplicados de Booking_ID
# "conservar_primero": descarta duplicados exactos y, ante conflictos, deja la 1ª aparición.
# "rechazar": detiene el ETL si hay Booking_ID repetidos con datos distintos.
POLITICA_DUPLICADOS = "conservar_primero"

# ---------------------------------------------------------------- Catálogos
ESTADO_COMPLETADO = "Completed"
ESTADO_CLIENTE = "Cancelled by Customer"
ESTADO_CONDUCTOR = "Cancelled by Driver"
ESTADO_INCOMPLETO = "Incomplete"
ESTADO_SIN_CONDUCTOR = "No Driver Found"

BUSINESS_LINE = {
    "Auto": "Liviana", "eBike": "Liviana", "Bike": "Liviana",
    "Go Mini": "Estándar", "Go Sedan": "Estándar",
    "Premier Sedan": "Premium", "UberXL": "Premium", "Uber XL": "Premium",
}
BUSINESS_LINE_DEFECTO = "Sin Clasificar"
VEHICULO_DEFECTO = "No Especificado"

PAGO_NA = "N/A / No Especificado"          # Payment_SK = 0

FRANJAS_BINS = [-1, 5, 11, 16, 23]
FRANJAS_LABELS = ["Madrugada", "Mañana", "Tarde", "Noche"]

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Responsables (Cancelled_By)
CB_CLIENTE = "Cliente"
CB_CONDUCTOR = "Conductor"
CB_SISTEMA = "Sistema / Operación"
CB_NA = "N/A - Viaje Completado"

# Registros centinela de Dim_Cancelacion (Tabla 14, fila 8): (SK, Cancelled_By, Cancellation_Reason)
SENTINELAS_CANCELACION = [
    (0, CB_NA, "Viaje Completado Sin Incidencias"),
    (1, CB_SISTEMA, "Sin Conductor Asignado"),
    (2, CB_CLIENTE, "Motivo No Registrado"),
    (3, CB_CONDUCTOR, "Motivo No Registrado"),
    (4, CB_SISTEMA, "Motivo No Registrado"),
]
SENTINELA_PAGO = [(0, PAGO_NA)]

# ---------------------------------------------------------------- Esquema destino
TABLAS = {
    "tiempo": "dim_tiempo",
    "vehiculo": "dim_vehiculo",
    "pago": "dim_metodopago",
    "cancelacion": "dim_cancelacion",
    "fact": "fact_bookings",
}
COLUMNAS = {
    "tiempo": ["Time_SK", "Fecha", "Anio", "Mes", "Dia", "Nombre_Mes", "Dia_Semana", "Hora", "Franja_Horaria"],
    "vehiculo": ["Vehicle_SK", "Vehicle_Type", "Business_Line"],
    "pago": ["Payment_SK", "Payment_Method"],
    "cancelacion": ["Cancellation_SK", "Cancelled_By", "Cancellation_Reason"],
    "fact": ["Booking_ID", "Booking_Status", "Customer_ID", "Booking_Value", "Ride_Distance",
             "Avg_VTAT", "Vehicle_SK", "Payment_SK", "Cancellation_SK", "Time_SK"],
}
SK_COL = {"tiempo": "Time_SK", "vehiculo": "Vehicle_SK", "pago": "Payment_SK", "cancelacion": "Cancellation_SK"}
CLAVES_NATURALES = {
    "tiempo": ["Time_SK"],
    "vehiculo": ["Vehicle_Type"],
    "pago": ["Payment_Method"],
    "cancelacion": ["Cancelled_By", "Cancellation_Reason"],
}
ORDEN_CARGA_DIMS = ["tiempo", "vehiculo", "pago", "cancelacion"]   # dimensiones primero, luego fact
