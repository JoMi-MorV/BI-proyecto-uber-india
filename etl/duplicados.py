"""Transform 2: tratamiento de Booking_ID duplicados (se ejecuta tras la limpieza)."""
import pandas as pd

from . import config
from .logger_etl import log, stats


def resolver_duplicados(df: pd.DataFrame) -> pd.DataFrame:
    n0 = len(df)
    exactos = df.duplicated(keep="first")
    df1 = df[~exactos]
    conflictivos = df1.duplicated(subset=["Booking_ID"], keep="first")

    if config.POLITICA_DUPLICADOS == "rechazar" and conflictivos.any():
        raise ValueError(f"{int(conflictivos.sum())} Booking_ID repetidos con datos distintos")

    rechazados = pd.concat([
        df[exactos].assign(Motivo="duplicado_exacto"),
        df1[conflictivos].assign(Motivo="booking_id_conflictivo"),
    ])
    if len(rechazados):
        config.DIR_STAGING.mkdir(parents=True, exist_ok=True)
        rechazados.to_csv(config.DIR_STAGING / "duplicados_descartados.csv", index=False)

    df2 = df1[~conflictivos].copy()
    stats.registrar("duplicados_exactos_descartados", int(exactos.sum()))
    stats.registrar("duplicados_conflictivos_descartados", int(conflictivos.sum()))
    stats.registrar("filas_tras_duplicados", len(df2))
    log.info(f"[duplicados] {n0} -> {len(df2)} filas | exactos={int(exactos.sum())} | "
             f"conflictivos={int(conflictivos.sum())} (política: {config.POLITICA_DUPLICADOS})")
    return df2
