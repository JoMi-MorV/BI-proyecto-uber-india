"""Paso 3 - Load: primero las dimensiones (solo filas nuevas) y luego Fact_Bookings (COPY)."""
import csv
import io

import pandas as pd
from sqlalchemy import create_engine, text

from . import config
from .logger_etl import log, stats


def crear_engine():
    return create_engine(config.url_conexion())


def _n(col: str) -> str:
    return col.lower() if config.NOMBRES_EN_MINUSCULAS else col


def _q(ident: str) -> str:
    return f'"{ident}"'


def _tabla_sql(clave: str) -> str:
    return f'{_q(config.DB_SCHEMA)}.{_q(config.TABLAS[clave])}'


# ------------------------------------------------------------- lectura de lo existente
def _leer_tabla(engine, clave: str) -> pd.DataFrame:
    df = pd.read_sql_table(config.TABLAS[clave], engine, schema=config.DB_SCHEMA)
    df = df.rename(columns={_n(c): c for c in config.COLUMNAS[clave]})
    return df[[c for c in config.COLUMNAS[clave] if c in df.columns]]


def leer_dimensiones_existentes(engine) -> dict:
    """Dimensiones ya cargadas (p. ej. por 02_seed.sql) para respetar sus SK."""
    existentes = {}
    for clave in config.ORDEN_CARGA_DIMS:
        try:
            df = _leer_tabla(engine, clave)
            if len(df):
                existentes[clave] = df
            log.info(f"[load] {config.TABLAS[clave]} existente: {len(df)} filas")
        except Exception as e:  # tabla inexistente, sin permisos, etc.
            log.warning(f"[load] no se pudo leer {config.TABLAS[clave]}: {e}")
    return existentes


# ------------------------------------------------------------- escritura
def _preparar(df: pd.DataFrame, clave: str) -> pd.DataFrame:
    out = df[config.COLUMNAS[clave]].copy()
    if "Fecha" in out.columns:
        out["Fecha"] = pd.to_datetime(out["Fecha"]).dt.date
    out = out.astype(object).where(out.notna(), None)
    out.columns = [_n(c) for c in out.columns]
    return out


def _metodo_copy(tabla, conn, claves, filas):
    """Método para DataFrame.to_sql: carga masiva con COPY (psycopg2)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    for fila in filas:
        w.writerow(["" if (x is None or (isinstance(x, float) and x != x)) else x for x in fila])
    buf.seek(0)
    destino = f'{_q(tabla.schema)}.{_q(tabla.name)}' if tabla.schema else _q(tabla.name)
    cols = ", ".join(_q(k) for k in claves)
    with conn.connection.cursor() as cur:
        cur.copy_expert(f"COPY {destino} ({cols}) FROM STDIN WITH CSV", buf)


def cargar_dimension(engine, clave: str, df: pd.DataFrame) -> int:
    nat, sk = config.CLAVES_NATURALES[clave], config.SK_COL[clave]
    try:
        existente = _leer_tabla(engine, clave)
    except Exception:
        existente = pd.DataFrame(columns=config.COLUMNAS[clave])

    nuevos = df
    if len(existente):
        if sk not in nat:  # la misma clave natural no puede tener otra SK en la BD
            cmp = df.merge(existente[nat + [sk]], on=nat, suffixes=("", "_bd"))
            conflictos = cmp[cmp[sk].astype("int64") != cmp[sk + "_bd"].astype("int64")]
            if len(conflictos):
                raise ValueError(f"{config.TABLAS[clave]}: {len(conflictos)} claves con SK distinta a la de la BD")
        marca = df.merge(existente[nat].drop_duplicates(), on=nat, how="left", indicator=True)
        nuevos = df[(marca["_merge"] == "left_only").to_numpy()]
        if nuevos[sk].isin(existente[sk]).any():
            raise ValueError(f"{config.TABLAS[clave]}: SK nuevas chocan con SK existentes")

    if len(nuevos):
        _preparar(nuevos, clave).to_sql(config.TABLAS[clave], engine, schema=config.DB_SCHEMA,
                                        if_exists="append", index=False, method=_metodo_copy)
    log.info(f"[load] {config.TABLAS[clave]}: {len(nuevos)} filas insertadas "
             f"(ya existían {len(df) - len(nuevos)})")
    return len(nuevos)


def cargar_fact(engine, fact: pd.DataFrame) -> int:
    """TRUNCATE + COPY en una sola transacción (re-ejecutable sin duplicar)."""
    datos = _preparar(fact, "fact")
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {_tabla_sql('fact')}"))
        datos.to_sql(config.TABLAS["fact"], conn, schema=config.DB_SCHEMA, if_exists="append",
                     index=False, method=_metodo_copy, chunksize=20_000)
    log.info(f"[load] {config.TABLAS['fact']}: {len(datos)} filas cargadas")
    return len(datos)


def validar_carga(engine, filas_esperadas: int):
    """Conteo y chequeo de integridad referencial (huérfanos) tras la carga."""
    f = _tabla_sql("fact")
    with engine.connect() as conn:
        total = conn.execute(text(f"SELECT COUNT(*) FROM {f}")).scalar()
        huerfanos = {}
        for clave in config.ORDEN_CARGA_DIMS:
            sk = _q(_n(config.SK_COL[clave]))
            q = (f"SELECT COUNT(*) FROM {f} f LEFT JOIN {_tabla_sql(clave)} d "
                 f"ON f.{sk} = d.{sk} WHERE d.{sk} IS NULL")
            huerfanos[config.TABLAS[clave]] = conn.execute(text(q)).scalar()
    stats.registrar("filas_en_fact_bd", total)
    stats.registrar("huerfanos_por_dimension", huerfanos)
    ok = total == filas_esperadas and not any(huerfanos.values())
    (log.info if ok else log.error)(
        f"[load] validación: fact={total} (esperadas {filas_esperadas}) | huérfanos={huerfanos}")
    return ok


def cargar_todo(engine, resultado: dict):
    insertadas = {}
    for clave in config.ORDEN_CARGA_DIMS:                  # 1) dimensiones
        insertadas[config.TABLAS[clave]] = cargar_dimension(engine, clave, resultado[clave])
    n = cargar_fact(engine, resultado["fact"])             # 2) hechos
    stats.registrar("filas_insertadas_dimensiones", insertadas)
    stats.registrar("filas_cargadas_fact", n)
    return validar_carga(engine, n)
