"""Paso 2 - Transform: orquesta los módulos de transformación y deja listas dimensiones + Fact_Bookings."""
import pandas as pd

from . import cancelaciones, config, dimensiones, duplicados, imputacion, limpieza, quality_gates
from .logger_etl import log, stats


def transformar(df: pd.DataFrame, dims_existentes: dict = None) -> dict:
    """Devuelve {'tiempo','vehiculo','pago','cancelacion','fact'} como DataFrames."""
    dims_existentes = dims_existentes or {}
    log.info(f"[transform] filas de entrada: {len(df)}")

    df = limpieza.limpiar_dataframe(df)                       # strip + tipos
    df = duplicados.resolver_duplicados(df)                   # unicidad Booking_ID
    df = quality_gates.aplicar_quality_gates(df)              # outliers -> NaN
    df = cancelaciones.consolidar_motivos(df)                 # Cancelled_By / Cancellation_Reason
    df = imputacion.imputar_booking_value(df)                 # promedio por Vehicle_Type
    df = dimensiones.agregar_atributos(df)                    # Business_Line, Franja, Time_SK

    dim_tiempo = dimensiones.construir_dim_tiempo(df)
    dim_veh = dimensiones.construir_dim_vehiculo(df, dims_existentes.get("vehiculo"))
    dim_pago = dimensiones.construir_dim_pago(df, dims_existentes.get("pago"))
    dim_canc = cancelaciones.construir_dim_cancelacion(df, dims_existentes.get("cancelacion"))
    dims = {"tiempo": dim_tiempo, "vehiculo": dim_veh, "pago": dim_pago, "cancelacion": dim_canc}
    dimensiones.registrar_stats_dims(dims)

    n = len(df)
    df = df.merge(dim_veh[["Vehicle_Type", "Vehicle_SK"]], on="Vehicle_Type", how="left")
    df = df.merge(dim_pago[["Payment_Method", "Payment_SK"]], on="Payment_Method", how="left")
    df = cancelaciones.asignar_cancellation_sk(df, dim_canc)
    assert len(df) == n, "Un merge duplicó filas: revisar unicidad de las dimensiones"

    fact = df[config.COLUMNAS["fact"]].copy()
    for sk in ("Vehicle_SK", "Payment_SK", "Cancellation_SK", "Time_SK"):
        if fact[sk].isna().any():
            raise ValueError(f"{sk} con nulos en Fact_Bookings")
        fact[sk] = fact[sk].astype("int64")

    stats.registrar("filas_fact_listas", len(fact))
    stats.registrar("nulos_finales_fact", {c: int(fact[c].isna().sum())
                                          for c in ("Booking_Value", "Ride_Distance", "Avg_VTAT")})
    log.info(f"[transform] Fact_Bookings lista: {len(fact)} filas | nulos finales: "
             f"{stats.datos['nulos_finales_fact']}")
    return {**dims, "fact": fact}
