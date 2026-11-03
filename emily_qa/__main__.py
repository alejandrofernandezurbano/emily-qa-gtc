"""Comando único:  python -m emily_qa

Orquesta el flujo completo:
  1. Leer la HU (YAML)            -> interprete.py
  2. Generar plan de casos        -> generador.py (+ llm.py opcional)
  3. Ejecutar con Pytest          -> ejecutor.py + qa_runner/
  4. Reporte, evidencias, defectos -> reporte.py

Códigos de salida: 0 sin fallos · 1 hay criterios fallidos · 2 error de entrada
· 3 no se pudo ejecutar ningún caso (p. ej. servicio caído).
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .ejecutor import ejecutar_pytest
from .generador import generar_plan
from .interprete import EntradaInvalida, cargar_hu
from .reporte import FALLIDO, ICONO, NO_EJECUTADO, generar_reporte


def main(argv=None) -> int:
    # Consola de Windows: evitar errores al imprimir tildes y emojis
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="emily_qa", description="Emily QA: criterios de aceptación -> pruebas -> evidencia")
    p.add_argument("--hu", default="hu/HU-DEMO-001.yaml", help="archivo YAML de la historia de usuario")
    p.add_argument("--modo", choices=["reglas", "llm"], default="reglas", help="cómo se generan los casos")
    p.add_argument("--base-url", help="URL de un servidor real (si no, se usa la app simulada en proceso)")
    p.add_argument("--salida", default="evidencias", help="carpeta raíz de evidencias")
    p.add_argument("--solo", help="ejecutar solo estos criterios, p. ej. CA-01,CA-03")
    a = p.parse_args(argv)

    try:
        hu = cargar_hu(a.hu)
    except EntradaInvalida as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    ejecucion_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    salida = Path(a.salida) / f"ejecucion-{ejecucion_id}"
    salida.mkdir(parents=True, exist_ok=True)

    solo = {s.strip() for s in a.solo.split(",")} if a.solo else None
    plan = generar_plan(hu, ejecucion_id, modo=a.modo, solo=solo)
    ruta_plan = salida / "plan.json"
    ruta_plan.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    print(f"[1/3] Plan: {len(plan.casos)} casos para {len(hu.criterios)} criterios -> {ruta_plan}")
    for aviso in plan.advertencias:
        print(f"      aviso: {aviso}")

    print("[2/3] Ejecutando Pytest...")
    ejecutar_pytest(ruta_plan, salida, a.base_url)

    resultado = generar_reporte(plan, salida)
    print(f"[3/3] Reporte: {salida / 'reporte.md'}\n")
    for c in resultado["criterios"]:
        print(f"  {ICONO[c['estado']]} {c['id']:6} {c['estado']:13} {c['motivo']}")
    for d in resultado["defectos"]:
        print(f"  -> {d['id']} [{d['criterio_id']}] {d['titulo']}")

    if resultado["resumen"][FALLIDO]:
        return 1
    ejecutados = [k for c in resultado["criterios"] for k in c["casos"] if k["estado"] != NO_EJECUTADO]
    return 0 if ejecutados else 3


if __name__ == "__main__":
    sys.exit(main())
