"""Pruebas del propio agente (no del sistema bajo prueba).

Ejecutar:  pytest
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app_simulada.main import crear_app
from emily_qa.generador import casos_por_reglas, generar_plan
from emily_qa.interprete import EntradaInvalida, cargar_hu
from emily_qa.llm import validar_propuesta
from emily_qa.modelos import CasoPrueba, Criterio, Esperado
from emily_qa.verificador import ejecutar_caso

RAIZ = Path(__file__).resolve().parent.parent
HU = cargar_hu(RAIZ / "hu" / "HU-DEMO-001.yaml")


# ---------------------------------------------------------------- generador


def test_cada_criterio_tiene_casos_trazables():
    plan = generar_plan(HU, "20260101-000000")
    por_criterio = {c.id: [k for k in plan.casos if k.criterio_id == c.id] for c in HU.criterios}
    assert all(len(casos) >= 1 for casos in por_criterio.values())
    assert not plan.criterios_sin_casos


def test_generacion_determinista():
    a = generar_plan(HU, "20260101-000000")
    b = generar_plan(HU, "20260101-000000")
    assert a.model_dump() == b.model_dump()


def test_ca03_verifica_persistencia():
    plan = generar_plan(HU, "20260101-000000")
    ca03 = [k for k in plan.casos if k.criterio_id == "CA-03"]
    assert all(k.esperado.persistido is False and k.datos["edad"] < 18 for k in ca03)


def test_criterio_desconocido_no_inventa_casos():
    raro = Criterio(id="CA-99", texto="El sistema debe ser agradable a la vista.")
    assert casos_por_reglas(raro, HU.contrato, "x") == []


def test_solo_marca_el_resto_como_excluido():
    plan = generar_plan(HU, "20260101-000000", solo={"CA-01"})
    assert {k.criterio_id for k in plan.casos} == {"CA-01"}
    assert set(plan.criterios_sin_casos) == {"CA-02", "CA-03"}


def test_hu_invalida(tmp_path):
    f = tmp_path / "mala.yaml"
    f.write_text("id: X\ncriterios: []\n")
    with pytest.raises(EntradaInvalida):
        cargar_hu(f)


# ------------------------------------------------------------------- LLM


def test_llm_descarta_propuestas_fuera_de_esquema():
    respuesta = json.dumps([
        {"criterio_id": "CA-01", "descripcion": "ok", "datos": {"nombre": "A", "correo": "a@b.co", "edad": 20},
         "esperado": {"status": 201, "persistido": True}},
        {"criterio_id": "CA-77", "descripcion": "criterio inventado", "datos": {}, "esperado": {"status": 200}},
        {"criterio_id": "CA-02", "descripcion": "verificación inventada", "datos": {"correo": "x"},
         "esperado": {"status": 422, "resultado": "aprobado"}},
        {"criterio_id": "CA-03", "descripcion": "campo extra", "datos": {"rol": "admin"}, "esperado": {"status": 422}},
    ])
    casos, avisos = validar_propuesta(respuesta, HU, "r1")
    assert list(casos) == ["CA-01"]
    assert casos["CA-01"][0].origen == "llm"
    assert len(avisos) == 3


def test_llm_texto_sin_json():
    casos, avisos = validar_propuesta("Todo pasó correctamente.", HU, "r1")
    assert casos == {} and avisos


# ------------------------------------------------------------ verificador


def _caso(edad: int, persistido: bool) -> CasoPrueba:
    return CasoPrueba(
        id="T", criterio_id="CA-03", descripcion="t", origen="reglas",
        datos={"nombre": "Z", "correo": f"z{edad}@ejemplo.com", "edad": edad},
        esperado=Esperado(status=422, persistido=persistido),
    )


def test_verificador_detecta_defecto_sembrado():
    with TestClient(crear_app(defecto_activo=True)) as http:
        ev = ejecutar_caso(_caso(17, False), http, HU.contrato)
    assert ev["peticiones"][0]["status"] == 422  # la respuesta "parece" correcta...
    assert not ev["ok"]  # ...pero el cliente quedó guardado
    assert [v["nombre"] for v in ev["verificaciones"] if not v["ok"]] == ["persistencia"]


def test_verificador_sin_defecto_no_da_falso_positivo():
    with TestClient(crear_app(defecto_activo=False)) as http:
        ev = ejecutar_caso(_caso(17, False), http, HU.contrato)
    assert ev["ok"]


# ------------------------------------------------------ flujo completo (E2E)


def _correr(tmp_path, **env_extra):
    env = {**os.environ, **env_extra, "PYTHONPATH": str(RAIZ)}
    p = subprocess.run([sys.executable, "-m", "emily_qa", "--salida", str(tmp_path)],
                       cwd=RAIZ, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    carpeta = next(tmp_path.glob("ejecucion-*"))
    return p.returncode, json.loads((carpeta / "reporte.json").read_text("utf-8"))


def test_e2e_con_defecto_falla_solo_ca03(tmp_path):
    codigo, rep = _correr(tmp_path, APP_DEFECTO="1")
    estados = {c["id"]: c["estado"] for c in rep["criterios"]}
    assert codigo == 1
    assert estados == {"CA-01": "APROBADO", "CA-02": "APROBADO", "CA-03": "FALLIDO"}


def test_e2e_sin_defecto_todo_aprobado(tmp_path):
    codigo, rep = _correr(tmp_path, APP_DEFECTO="0")
    assert codigo == 0
    assert all(c["estado"] == "APROBADO" for c in rep["criterios"])
