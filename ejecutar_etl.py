"""Orquestador del ETL Uber India 2024.

Ejemplos (desde la raíz del repo):
    python ejecutar_etl.py --paso extract
    python ejecutar_etl.py --paso transform --sin-bd --exportar-csv
    python ejecutar_etl.py --paso load
    python ejecutar_etl.py                      # todo el pipeline
Cada paso guarda su salida en data/staging/, así se puede repetir uno solo mientras se depura.
"""
import argparse
import sys
import time

import pandas as pd

from etl import config, extract, transform
from etl.logger_etl import log, stats

PKL_STAGING = config.DIR_STAGING / "staging.pkl"
PKL_TRANSFORM = config.DIR_STAGING / "transformado.pkl"


def paso_extract(csv=None) -> pd.DataFrame:
    log.info("=" * 15 + " PASO 1: EXTRACT / STAGING " + "=" * 15)
    df = extract.leer_csv(csv)
    extract.validar_unicidad(df)
    config.DIR_STAGING.mkdir(parents=True, exist_ok=True)
    pd.to_pickle(df, PKL_STAGING)
    return df


def paso_transform(df=None, sin_bd=False, exportar_csv=False) -> dict:
    log.info("=" * 15 + " PASO 2: TRANSFORM " + "=" * 15)
    if df is None:
        if not PKL_STAGING.exists():
            sys.exit("No hay staging. Ejecuta primero: python ejecutar_etl.py --paso extract")
        df = pd.read_pickle(PKL_STAGING)

    existentes = {}
    if not sin_bd:
        from etl import load
        try:
            existentes = load.leer_dimensiones_existentes(load.crear_engine())
        except Exception as e:
            log.warning(f"[transform] sin conexión a la BD ({e}); se generan SK desde cero")
    resultado = transform.transformar(df, existentes)

    pd.to_pickle(resultado, PKL_TRANSFORM)
    if exportar_csv:
        config.DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
        for nombre, tabla in resultado.items():
            tabla.to_csv(config.DIR_PROCESSED / f"{config.TABLAS[nombre]}.csv", index=False)
        log.info(f"[transform] CSV de revisión en {config.DIR_PROCESSED}")
    return resultado


def paso_load(resultado=None) -> bool:
    log.info("=" * 15 + " PASO 3: LOAD " + "=" * 15)
    if resultado is None:
        if not PKL_TRANSFORM.exists():
            sys.exit("No hay datos transformados. Ejecuta primero: --paso transform")
        resultado = pd.read_pickle(PKL_TRANSFORM)
    from etl import load
    return load.cargar_todo(load.crear_engine(), resultado)


def main():
    p = argparse.ArgumentParser(description="ETL Uber India 2024")
    p.add_argument("--paso", choices=["extract", "transform", "load", "todo"], default="todo")
    p.add_argument("--csv", help="ruta alternativa del CSV de origen")
    p.add_argument("--sin-bd", action="store_true", help="no consulta ni escribe en PostgreSQL (solo extract+transform)")
    p.add_argument("--exportar-csv", action="store_true", help="guarda dimensiones y fact en data/processed/")
    a = p.parse_args()

    t0 = time.time()
    if a.paso in ("extract", "todo"):
        stats.reiniciar()

    if a.paso == "extract":
        paso_extract(a.csv)
    elif a.paso == "transform":
        paso_transform(sin_bd=a.sin_bd, exportar_csv=a.exportar_csv)
    elif a.paso == "load":
        paso_load()
    else:
        df = paso_extract(a.csv)
        res = paso_transform(df, a.sin_bd, a.exportar_csv)
        if a.sin_bd:
            log.info("--sin-bd: se omite el LOAD")
        else:
            paso_load(res)

    stats.registrar("duracion_ultimo_paso_seg", round(time.time() - t0, 1))
    log.info("RESUMEN ACUMULADO (logs/resumen_etl.json):\n" + stats.texto())


if __name__ == "__main__":
    main()
