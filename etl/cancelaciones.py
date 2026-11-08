"""Transform 6: consolidación de motivos (Cancelled_By / Cancellation_Reason) y asignación de Cancellation_SK."""
import numpy as np
import pandas as pd

from . import config
from .dimensiones import completar_dim
from .logger_etl import log, stats


def consolidar_motivos(df: pd.DataFrame) -> pd.DataFrame:
    """Une las 3 columnas de motivos. Prioridad si coexisten: Cliente > Conductor > Sistema."""
    df = df.copy()
    c, d, i = df[config.COL_MOTIVO_CLIENTE], df[config.COL_MOTIVO_CONDUCTOR], df[config.COL_MOTIVO_INCOMPLETO]

    por = pd.Series(pd.NA, index=df.index, dtype="string")
    por = (por.mask(i.notna(), config.CB_SISTEMA)
              .mask(d.notna(), config.CB_CONDUCTOR)
              .mask(c.notna(), config.CB_CLIENTE))
    df["Cancelled_By"] = por
    df["Cancellation_Reason"] = c.fillna(d).fillna(i)

    multiples = int(((c.notna().astype(int) + d.notna().astype(int) + i.notna().astype(int)) > 1).sum())
    con_motivo = int(df["Cancellation_Reason"].notna().sum())
    stats.registrar("filas_con_motivo", con_motivo)
    stats.registrar("filas_con_mas_de_un_motivo", multiples)
    log.info(f"[cancelaciones] filas con motivo: {con_motivo} | con más de un motivo: {multiples}")
    return df.drop(columns=[config.COL_MOTIVO_CLIENTE, config.COL_MOTIVO_CONDUCTOR, config.COL_MOTIVO_INCOMPLETO])


def construir_dim_cancelacion(df: pd.DataFrame, existente=None) -> pd.DataFrame:
    base = pd.DataFrame(config.SENTINELAS_CANCELACION,
                        columns=["Cancellation_SK", "Cancelled_By", "Cancellation_Reason"])
    usa_combo = ~df["Booking_Status"].isin([config.ESTADO_COMPLETADO, config.ESTADO_SIN_CONDUCTOR])
    req = (df.loc[usa_combo & df["Cancellation_Reason"].notna(), ["Cancelled_By", "Cancellation_Reason"]]
             .drop_duplicates().astype(object))
    dim = completar_dim(req, existente, config.CLAVES_NATURALES["cancelacion"], "Cancellation_SK", base=base)
    return dim[config.COLUMNAS["cancelacion"]]


def _es(serie: pd.Series, valor: str) -> np.ndarray:
    return (serie == valor).fillna(False).to_numpy(dtype=bool)


def asignar_cancellation_sk(df: pd.DataFrame, dim: pd.DataFrame) -> pd.DataFrame:
    """Orden condicional (Tabla 14, filas 8 al 10):
    1) Completed -> 0 | 2) No Driver Found -> 1 | 3) hay motivo -> SK de la combinación |
    4) sin motivo -> centinela según estado (Customer=2, Driver=3, Incomplete=4)."""
    df = df.copy()
    nat = config.CLAVES_NATURALES["cancelacion"]
    combo = (df[nat].astype(object)
             .merge(dim[nat + ["Cancellation_SK"]].astype(object), on=nat, how="left")["Cancellation_SK"]
             .to_numpy(dtype=float))
    combo = np.nan_to_num(combo, nan=-1).astype(int)

    st = df["Booking_Status"]
    condiciones = [
        _es(st, config.ESTADO_COMPLETADO),
        _es(st, config.ESTADO_SIN_CONDUCTOR),
        df["Cancellation_Reason"].notna().to_numpy(dtype=bool),
        _es(st, config.ESTADO_CLIENTE),
        _es(st, config.ESTADO_CONDUCTOR),
        _es(st, config.ESTADO_INCOMPLETO),
    ]
    valores = [0, 1, combo, 2, 3, 4]
    df["Cancellation_SK"] = np.select(condiciones, valores, default=-1).astype("int64")

    sin_sk = int((df["Cancellation_SK"] < 0).sum())
    if sin_sk:
        raise ValueError(f"{sin_sk} filas sin Cancellation_SK. Estados: "
                         f"{df.loc[df['Cancellation_SK'] < 0, 'Booking_Status'].unique().tolist()}")
    centinelas = df["Cancellation_SK"].value_counts().reindex(range(5), fill_value=0).to_dict()
    stats.registrar("cancellation_sk_centinelas", {int(k): int(v) for k, v in centinelas.items()})
    log.info(f"[cancelaciones] uso de SK centinela 0-4: {centinelas} | ningún registro con SK nulo")
    return df
