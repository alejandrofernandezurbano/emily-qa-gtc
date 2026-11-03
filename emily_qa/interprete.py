"""Paso 1: leer y validar la historia de usuario (YAML) de entrada."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from .modelos import HistoriaUsuario


class EntradaInvalida(Exception):
    pass


def cargar_hu(ruta: str | Path) -> HistoriaUsuario:
    ruta = Path(ruta)
    if not ruta.exists():
        raise EntradaInvalida(f"No existe el archivo de la HU: {ruta}")
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        hu = HistoriaUsuario.model_validate(datos)
    except (yaml.YAMLError, ValidationError) as e:
        raise EntradaInvalida(f"La HU {ruta} no es válida:\n{e}") from e

    ids = [c.id for c in hu.criterios]
    if len(ids) != len(set(ids)):
        raise EntradaInvalida(f"Hay criterios con ID repetido: {ids}")
    return hu
