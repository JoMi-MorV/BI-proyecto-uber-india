"""Transform 3: Quality Gates (Tabla 8). Fuera de rango -> NaN, conservando la fila."""
import numpy as np
import pandas as pd

from . import config
from .logger_etl import log, stats


def aplicar_quality_gates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    resumen = {}
    for col, (minimo, maximo) in config.RANGOS.items():
        fuera = df[col].notna() & ~df[col].between(minimo, maximo)
        n = int(fuera.sum())
        df.loc[fuera, col] = np.nan
        resumen[col] = {"rango": [minimo, maximo], "outliers_detectados": n,
                        "nulos_tras_gate": int(df[col].isna().sum())}
        log.info(f"[quality_gate] {col} fuera de [{minimo}, {maximo}] -> NaN: {n} "
                 f"(nulos totales ahora: {resumen[col]['nulos_tras_gate']})")
    stats.registrar("quality_gates", resumen)
    return df
