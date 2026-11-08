"""Paso 1 - Extract / Staging: lectura del CSV y validación de unicidad de Booking_ID."""
from pathlib import Path

import pandas as pd

from . import config
from .limpieza import limpiar_texto
from .logger_etl import log, stats


def leer_csv(ruta=None) -> pd.DataFrame:
    ruta = Path(ruta) if ruta else config.CSV_ORIGEN
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el CSV de origen: {ruta}")
    log.info(f"[extract] leyendo {ruta}")
    # Todo como texto: la conversión de tipos se hace de forma controlada en limpieza.py
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8")
    stats.registrar("filas_leidas", len(df))
    stats.registrar("columnas_origen", df.shape[1])

    df.columns = [c.strip().replace(" ", "_") for c in df.columns]
    faltantes = [c for c in config.COLUMNAS_ORIGEN if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en el CSV: {faltantes}")
    excluidas = [c for c in df.columns if c not in config.COLUMNAS_ORIGEN]
    log.info(f"[extract] filas={len(df)} | columnas físicas={df.shape[1]} | "
             f"incorporadas={len(config.COLUMNAS_ORIGEN)} | excluidas={len(excluidas)}")
    stats.registrar("columnas_excluidas", excluidas)
    return df[config.COLUMNAS_ORIGEN].copy()


def validar_unicidad(df: pd.DataFrame) -> dict:
    """Reporta Booking_ID repetidos (exactos vs. conflictivos). No modifica los datos."""
    ids = limpiar_texto(df["Booking_ID"])
    nulos = int(ids.isna().sum())
    repetidos_extra = int(ids.duplicated(keep="first").sum())
    sub = df[ids.duplicated(keep=False) & ids.notna()].apply(limpiar_texto)
    exactos = int(sub.duplicated(keep="first").sum())
    info = {
        "booking_id_nulos": nulos,
        "booking_id_unicos": int(ids.nunique()),
        "filas_excedentes_por_id_repetido": repetidos_extra,
        "duplicados_exactos": exactos,
        "duplicados_conflictivos": repetidos_extra - exactos,
    }
    stats.registrar("validacion_unicidad", info)
    if repetidos_extra or nulos:
        log.warning(f"[extract] unicidad de Booking_ID NO cumplida: {info}")
    else:
        log.info("[extract] unicidad de Booking_ID OK")
    return info
