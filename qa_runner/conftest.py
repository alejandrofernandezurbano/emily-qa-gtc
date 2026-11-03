"""Configuración de Pytest para ejecutar el plan generado por Emily QA.

Recibe por variables de entorno:
  EMILY_QA_PLAN      ruta del plan.json
  EMILY_QA_SALIDA    carpeta donde guardar evidencias
  EMILY_QA_BASE_URL  (opcional) URL de un servidor real; si no, se usa la app en proceso
"""

import json
import os
from pathlib import Path

import httpx
import pytest

from emily_qa.modelos import PlanPruebas

SALIDA = Path(os.environ.get("EMILY_QA_SALIDA", "evidencias/manual"))
_resultados: dict[str, dict] = {}


@pytest.fixture(scope="session")
def plan() -> PlanPruebas:
    return PlanPruebas.model_validate_json(Path(os.environ["EMILY_QA_PLAN"]).read_text("utf-8"))


@pytest.fixture(scope="session")
def http():
    base_url = os.environ.get("EMILY_QA_BASE_URL")
    if base_url:
        with httpx.Client(base_url=base_url, timeout=10) as cliente:
            yield cliente
    else:
        from fastapi.testclient import TestClient

        from app_simulada.main import crear_app

        with TestClient(crear_app()) as cliente:
            yield cliente


@pytest.fixture(scope="session")
def carpeta_evidencias() -> Path:
    carpeta = SALIDA / "casos"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _motivo(report) -> str:
    """Mensaje corto y legible del resultado (mensaje de la aserción o motivo del skip)."""
    lr = report.longrepr
    if not lr:
        return ""
    if isinstance(lr, tuple):  # skip: (archivo, línea, motivo)
        return str(lr[2]).removeprefix("Skipped: ")
    crash = getattr(lr, "reprcrash", None)
    if crash is not None:
        return crash.message.splitlines()[0].removeprefix("AssertionError: ")[:500]
    return str(lr).strip().splitlines()[-1][:500]


def pytest_runtest_logreport(report):
    """Guarda el resultado de Pytest de cada caso (fuente de verdad del reporte)."""
    props = dict(report.user_properties)
    caso_id = props.get("caso_id")
    if not caso_id:
        return
    if report.when == "call" or report.outcome != "passed":
        _resultados[caso_id] = {
            "criterio_id": props.get("criterio_id"),
            "resultado_pytest": report.outcome,  # passed | failed | skipped
            "fase": report.when,
            "detalle": _motivo(report),
        }


def pytest_sessionfinish(session, exitstatus):
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "resultados_pytest.json").write_text(
        json.dumps(_resultados, indent=2, ensure_ascii=False), encoding="utf-8"
    )
