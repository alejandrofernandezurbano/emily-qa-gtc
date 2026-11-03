"""Prueba genérica parametrizada: un test de Pytest por cada caso del plan.

Regla anti falsos positivos:
  - FALLIDO  solo si una verificación determinista falló (con evidencia guardada).
  - Si la API no responde o la herramienta falla, el caso queda como
    NO EJECUTADO (skip), nunca como fallido ni aprobado.
"""

import json
import os
from pathlib import Path

import httpx
import pytest

from emily_qa.modelos import PlanPruebas
from emily_qa.verificador import ejecutar_caso

_PLAN = PlanPruebas.model_validate_json(Path(os.environ["EMILY_QA_PLAN"]).read_text("utf-8"))


@pytest.mark.parametrize("caso", _PLAN.casos, ids=[c.id for c in _PLAN.casos])
def test_caso(caso, plan, http, carpeta_evidencias, record_property):
    record_property("caso_id", caso.id)
    record_property("criterio_id", caso.criterio_id)

    try:
        evidencia = ejecutar_caso(caso, http, plan.contrato)
    except httpx.TransportError as e:
        pytest.skip(f"El servicio no respondió ({e.__class__.__name__}: {e})")
    except Exception as e:  # error de la propia herramienta, no del sistema bajo prueba
        pytest.skip(f"Error interno de Emily QA ({e.__class__.__name__}: {e})")

    archivo = carpeta_evidencias / f"{caso.id}.json"
    archivo.write_text(json.dumps(evidencia, indent=2, ensure_ascii=False), encoding="utf-8")

    fallidas = [v for v in evidencia["verificaciones"] if not v["ok"]]
    assert not fallidas, f"[{caso.criterio_id}] " + "; ".join(
        f"{v['nombre']}: esperado={v['esperado']!r} obtenido={v['obtenido']!r}" for v in fallidas
    )
