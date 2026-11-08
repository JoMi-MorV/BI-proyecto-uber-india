"""Transform 4: Business_Line, Hora/Franja_Horaria, Time_SK y construcción de dimensiones con SK."""
import pandas as pd

from . import config
from .logger_etl import log, stats


# ------------------------------------------------------------- atributos por fila
def agregar_atributos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    desconocidos = sorted(set(df["Vehicle_Type"]) - set(config.BUSINESS_LINE))
    if desconocidos:
        log.warning(f"[dimensiones] Vehicle_Type sin línea de negocio: {desconocidos}")
    df["Business_Line"] = df["Vehicle_Type"].map(config.BUSINESS_LINE).fillna(config.BUSINESS_LINE_DEFECTO)
    df["Franja_Horaria"] = franja_horaria(df["Hora"])
    df["Time_SK"] = time_sk(df["Fecha"], df["Hora"])
    return df


def franja_horaria(hora: pd.Series) -> pd.Series:
    return pd.cut(hora, bins=config.FRANJAS_BINS, labels=config.FRANJAS_LABELS).astype(str)


def time_sk(fecha: pd.Series, hora: pd.Series) -> pd.Series:
    """YYYYMMDDHH como entero (ej.: 2024-03-15 18:42:10 -> 2024031518)."""
    return (fecha.dt.strftime("%Y%m%d").astype("int64") * 100 + hora).astype("int64")


# ------------------------------------------------------------- SKs
def completar_dim(requeridos: pd.DataFrame, existente, claves: list, col_sk: str, base=None) -> pd.DataFrame:
    """Devuelve la dimensión completa: existente (BD) + base (centinelas) + valores nuevos con SK secuencial."""
    partes = [x for x in (existente, base) if x is not None and len(x)]
    cols = requeridos.columns.tolist() + [col_sk]
    if partes:
        dim = pd.concat([p[[c for c in cols if c in p.columns]] for p in partes], ignore_index=True)
        dim = dim.drop_duplicates(subset=claves, keep="first")
    else:
        dim = pd.DataFrame(columns=cols)

    nuevos = requeridos.merge(dim[claves], on=claves, how="left", indicator=True)
    nuevos = nuevos[nuevos["_merge"] == "left_only"].drop(columns="_merge").sort_values(claves)
    siguiente = int(dim[col_sk].max()) + 1 if len(dim) else 1
    nuevos[col_sk] = range(siguiente, siguiente + len(nuevos))
    out = pd.concat([dim, nuevos], ignore_index=True) if len(nuevos) else dim
    out[col_sk] = out[col_sk].astype("int64")
    return out.sort_values(col_sk).reset_index(drop=True)


def construir_dim_vehiculo(df, existente=None) -> pd.DataFrame:
    req = df[["Vehicle_Type", "Business_Line"]].drop_duplicates()
    dim = completar_dim(req, existente, ["Vehicle_Type"], "Vehicle_SK")
    return dim[config.COLUMNAS["vehiculo"]]


def construir_dim_pago(df, existente=None) -> pd.DataFrame:
    base = pd.DataFrame(config.SENTINELA_PAGO, columns=["Payment_SK", "Payment_Method"])
    req = df[["Payment_Method"]].drop_duplicates()
    dim = completar_dim(req, existente, ["Payment_Method"], "Payment_SK", base=base)
    return dim[config.COLUMNAS["pago"]]


def construir_dim_tiempo(df) -> pd.DataFrame:
    """Una fila por hora, cubriendo todos los días del rango de datos (2024 -> 8.784 filas)."""
    ini = df["Fecha"].min().normalize()
    fin = df["Fecha"].max().normalize() + pd.Timedelta(hours=23)
    ts = pd.Series(pd.date_range(ini, fin, freq="h"))
    dim = pd.DataFrame({
        "Time_SK": ts.dt.strftime("%Y%m%d%H").astype("int64"),
        "Fecha": ts.dt.normalize(),
        "Anio": ts.dt.year, "Mes": ts.dt.month, "Dia": ts.dt.day,
        "Nombre_Mes": (ts.dt.month - 1).map(dict(enumerate(config.MESES))),
        "Dia_Semana": ts.dt.dayofweek.map(dict(enumerate(config.DIAS))),
        "Hora": ts.dt.hour,
    })
    dim["Franja_Horaria"] = franja_horaria(dim["Hora"])
    return dim[config.COLUMNAS["tiempo"]]


def registrar_stats_dims(dims: dict):
    stats.registrar("filas_por_dimension", {k: len(v) for k, v in dims.items()})
    log.info(f"[dimensiones] filas por dimensión: { {k: len(v) for k, v in dims.items()} }")
