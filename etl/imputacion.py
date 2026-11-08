"""Transform 5: imputación de Booking_Value con la tarifa promedio por Vehicle_Type."""
import pandas as pd

from . import config
from .logger_etl import log, stats


def imputar_booking_value(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    completados = df[(df["Booking_Status"] == config.ESTADO_COMPLETADO) & df["Booking_Value"].notna()]
    tarifa = completados.groupby("Vehicle_Type")["Booking_Value"].mean()
    tarifa_global = completados["Booking_Value"].mean()

    nulos = df["Booking_Value"].isna()
    n_antes = int(nulos.sum())
    por_estado = df.loc[nulos, "Booking_Status"].value_counts().to_dict()

    promedio_fila = df["Vehicle_Type"].map(tarifa).fillna(tarifa_global)
    df.loc[nulos, "Booking_Value"] = promedio_fila[nulos]
    df["Booking_Value"] = df["Booking_Value"].round(2)

    stats.registrar("booking_value_imputados", n_antes)
    stats.registrar("booking_value_imputados_por_estado", por_estado)
    stats.registrar("tarifa_promedio_por_vehiculo", tarifa.round(2).to_dict())
    log.info(f"[imputacion] Booking_Value imputados con promedio por Vehicle_Type: {n_antes}")
    log.info(f"[imputacion] por estado: {por_estado}")
    return df
