"""Paso 3: lanzar Pytest sobre el plan y guardar la salida completa como evidencia."""

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def ejecutar_pytest(ruta_plan: Path, salida: Path, base_url: str | None = None) -> int:
    env = os.environ.copy()
    env["EMILY_QA_PLAN"] = str(ruta_plan.resolve())
    env["EMILY_QA_SALIDA"] = str(salida.resolve())
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(RAIZ) + os.pathsep + env.get("PYTHONPATH", "")
    if base_url:
        env["EMILY_QA_BASE_URL"] = base_url
    else:
        env.pop("EMILY_QA_BASE_URL", None)

    comando = [
        sys.executable, "-m", "pytest", str(RAIZ / "qa_runner" / "test_plan.py"),
        "-v", "-rA", "-p", "no:cacheprovider",
        f"--junitxml={salida.resolve() / 'junit.xml'}",
    ]
    proceso = subprocess.run(comando, cwd=RAIZ, env=env, capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=300)
    salida_texto = proceso.stdout + proceso.stderr
    (salida / "pytest.log").write_text(salida_texto, encoding="utf-8")
    return proceso.returncode
