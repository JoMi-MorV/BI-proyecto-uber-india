"""Transform 1: limpieza de comillas/espacios, normalización de nulos y tipos (.strip())."""
import pandas as pd

from . import config
from .logger_etl import log, stats

TOKENS_NULOS = {"", "null", "nan", "none", "n/a"}


def limpiar_texto(serie: pd.Series) -> pd.Series:
    """Quita espacios y comillas; los tokens tipo 'null' pasan a NA."""
    s = serie.astype("string").str.strip().str.strip("\"'").str.strip()
    return s.mask(s.str.lower().isin(TOKENS_NULOS), pd.NA)


def limpiar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    log.info("[limpieza] strip de comillas/espacios y normalización de nulos")
    df = df.copy()
    for col in df.columns:
        df[col] = limpiar_texto(df[col])

    nulos_orig = {c: int(df[c].isna().sum()) for c in df.columns}
    stats.registrar("nulos_originales_por_columna", nulos_orig)

    # Tipos numéricos (lo no convertible queda NaN)
    for col in config.METRICAS:
        antes = df[col].notna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
        perdidos = int(antes - df[col].notna().sum())
        if perdidos:
            log.warning(f"[limpieza] {col}: {perdidos} valores no numéricos pasaron a NaN")

    # Fecha y hora (necesarias para Time_SK: no se admiten inválidas)
    df["Fecha"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="coerce")
    df["Hora"] = pd.to_datetime(df["Time"], format="%H:%M:%S", errors="coerce").dt.hour
    invalidas = int(df["Fecha"].isna().sum() + df["Hora"].isna().sum())
    if invalidas:
        raise ValueError(f"{invalidas} fechas/horas inválidas: no se puede construir Time_SK")
    df["Hora"] = df["Hora"].astype("int64")

    # Atributos categóricos requeridos por las dimensiones
    n_veh = int(df["Vehicle_Type"].isna().sum())
    n_pago = int(df["Payment_Method"].isna().sum())
    df["Vehicle_Type"] = df["Vehicle_Type"].fillna(config.VEHICULO_DEFECTO)
    df["Payment_Method"] = df["Payment_Method"].fillna(config.PAGO_NA)
    stats.registrar("vehicle_type_nulos_a_defecto", n_veh)
    stats.registrar("payment_method_nulos_a_NA", n_pago)
    log.info(f"[limpieza] Payment_Method nulos -> '{config.PAGO_NA}': {n_pago}")
    return df
