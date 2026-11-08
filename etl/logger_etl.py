"""Logging del ETL: archivo + consola, y un resumen JSON de estadísticas para el informe."""
import json
import logging
import sys

from . import config

RUTA_RESUMEN = config.DIR_LOGS / "resumen_etl.json"


def _configurar_logger() -> logging.Logger:
    config.DIR_LOGS.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("etl_uber")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(config.DIR_LOGS / "etl_uber.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


class Estadisticas:
    """Acumula métricas entre pasos (se persiste en logs/resumen_etl.json)."""

    def __init__(self):
        self.datos = {}
        if RUTA_RESUMEN.exists():
            try:
                self.datos = json.loads(RUTA_RESUMEN.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.datos = {}

    def reiniciar(self):
        self.datos = {}
        self.guardar()

    def registrar(self, clave, valor):
        self.datos[clave] = valor
        self.guardar()

    def guardar(self):
        RUTA_RESUMEN.write_text(
            json.dumps(self.datos, indent=2, ensure_ascii=False,
                       default=lambda o: o.item() if hasattr(o, "item") else str(o)),
            encoding="utf-8")

    def texto(self) -> str:
        return json.dumps(self.datos, indent=2, ensure_ascii=False,
                          default=lambda o: o.item() if hasattr(o, "item") else str(o))


log = _configurar_logger()
stats = Estadisticas()
