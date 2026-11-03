"""Paso 4: consolidar resultados por criterio y escribir reporte + defectos.

Estados por criterio:
  APROBADO      todos sus casos pasaron (con evidencia).
  FALLIDO       al menos un caso falló una verificación determinista (con evidencia).
  NO EJECUTADO  sin casos, excluido, o algún caso no pudo ejecutarse.
"""

import json
from pathlib import Path

from .modelos import PlanPruebas

APROBADO, FALLIDO, NO_EJECUTADO = "APROBADO", "FALLIDO", "NO EJECUTADO"


def estado_caso(caso_id: str, resultados: dict, carpeta_casos: Path) -> tuple[str, str]:
    r = resultados.get(caso_id)
    evidencia = carpeta_casos / f"{caso_id}.json"
    if r is None:
        return NO_EJECUTADO, "Pytest no reportó este caso."
    if r["resultado_pytest"] == "passed" and evidencia.exists():
        return APROBADO, ""
    if r["resultado_pytest"] == "failed" and evidencia.exists():
        return FALLIDO, r["detalle"]
    # skipped, error de setup o fallo sin evidencia: no se puede afirmar nada
    return NO_EJECUTADO, r["detalle"] or "Sin evidencia."


def consolidar(plan: PlanPruebas, salida: Path) -> dict:
    archivo = salida / "resultados_pytest.json"
    resultados = json.loads(archivo.read_text("utf-8")) if archivo.exists() else {}
    carpeta_casos = salida / "casos"

    criterios = []
    for c in plan.criterios:
        casos = [k for k in plan.casos if k.criterio_id == c.id]
        detalle_casos = []
        for k in casos:
            estado, motivo = estado_caso(k.id, resultados, carpeta_casos)
            detalle_casos.append({
                "caso_id": k.id, "descripcion": k.descripcion, "origen": k.origen,
                "estado": estado, "motivo": motivo,
                "evidencia": f"casos/{k.id}.json" if (carpeta_casos / f"{k.id}.json").exists() else None,
            })
        estados = {d["estado"] for d in detalle_casos}
        if not casos:
            estado, motivo = NO_EJECUTADO, plan.criterios_sin_casos.get(c.id, "Sin casos.")
        elif FALLIDO in estados:
            estado, motivo = FALLIDO, "Al menos un caso incumple el criterio."
        elif estados == {APROBADO}:
            estado, motivo = APROBADO, "Todos los casos cumplen el criterio."
        elif APROBADO not in estados:
            primero = next((d["motivo"] for d in detalle_casos if d["motivo"]), "sin detalle")
            estado, motivo = NO_EJECUTADO, f"Ningún caso pudo ejecutarse: {primero}"
        else:
            estado, motivo = NO_EJECUTADO, "Cobertura incompleta: hay casos sin ejecutar."
        criterios.append({"id": c.id, "texto": " ".join(c.texto.split()), "estado": estado,
                          "motivo": motivo, "casos": detalle_casos})

    resumen = {e: sum(1 for c in criterios if c["estado"] == e) for e in (APROBADO, FALLIDO, NO_EJECUTADO)}
    return {"hu_id": plan.hu_id, "ejecucion_id": plan.ejecucion_id, "modo": plan.modo,
            "resumen": resumen, "criterios": criterios, "advertencias": plan.advertencias}


def generar_defectos(consolidado: dict, salida: Path) -> list[dict]:
    """Defectos listos para Emily Dev / gestor de trabajo. Requieren revisión humana antes de enviarse."""
    defectos = []
    for c in consolidado["criterios"]:
        for k in c["casos"]:
            if k["estado"] != FALLIDO:
                continue
            ev = json.loads((salida / k["evidencia"]).read_text("utf-8"))
            defectos.append({
                "id": f"DEF-{len(defectos) + 1:03d}",
                "hu_id": consolidado["hu_id"],
                "criterio_id": c["id"],
                "criterio": c["texto"],
                "caso_id": k["caso_id"],
                "titulo": f"{c['id']} incumplido: {k['descripcion']}",
                "pasos_reproduccion": [f"{p['metodo']} {p['ruta']} {json.dumps(p['cuerpo_enviado'], ensure_ascii=False)}"
                                       for p in ev["peticiones"]],
                "respuesta_api": {"status": ev["peticiones"][0]["status"], "cuerpo": ev["peticiones"][0]["respuesta"]},
                "verificaciones_fallidas": [v for v in ev["verificaciones"] if not v["ok"]],
                "evidencia": k["evidencia"],
                "estado": "pendiente_revision_humana",
            })
    return defectos


ICONO = {APROBADO: "✅", FALLIDO: "❌", NO_EJECUTADO: "⚪"}


def escribir_markdown(consolidado: dict, defectos: list[dict], salida: Path) -> Path:
    r = consolidado["resumen"]
    L = [
        f"# Reporte Emily QA · {consolidado['hu_id']}",
        "",
        f"- Ejecución: `{consolidado['ejecucion_id']}` · modo de generación: `{consolidado['modo']}`",
        f"- Resultado: {r[APROBADO]} aprobados · {r[FALLIDO]} fallidos · {r[NO_EJECUTADO]} no ejecutados",
        "- Evidencias: `pytest.log`, `junit.xml`, `casos/*.json` (petición, respuesta y verificaciones de cada caso)",
        "",
        "## Resultado por criterio",
        "",
        "| Criterio | Estado | Casos | Conclusión |",
        "|---|---|---|---|",
    ]
    for c in consolidado["criterios"]:
        casos = ", ".join(f"{k['caso_id']} {ICONO[k['estado']]}" for k in c["casos"]) or "—"
        L.append(f"| {c['id']} | {ICONO[c['estado']]} {c['estado']} | {casos} | {c['motivo']} |")

    L += ["", "## Detalle por criterio", ""]
    for c in consolidado["criterios"]:
        L += [f"### {c['id']} · {c['estado']}", "", f"> {c['texto']}", ""]
        for k in c["casos"]:
            ev = f" · evidencia: `{k['evidencia']}`" if k["evidencia"] else ""
            mot = f" — {k['motivo']}" if k["motivo"] else ""
            L.append(f"- {ICONO[k['estado']]} **{k['caso_id']}** ({k['origen']}): {k['descripcion']}{ev}{mot}")
        if not c["casos"]:
            L.append(f"- ⚪ {c['motivo']}")
        L.append("")

    L += ["## Defectos detectados", ""]
    if not defectos:
        L.append("Ninguno.")
    for d in defectos:
        L += [f"### {d['id']} · {d['titulo']}", "", f"- Criterio que sustenta la conclusión: **{d['criterio_id']}** — {d['criterio']}",
              "- Pasos para reproducir:"]
        L += [f"  {i}. `{p}`" for i, p in enumerate(d["pasos_reproduccion"], 1)]
        resp = d["respuesta_api"]
        L.append(f"- Respuesta de la API al registro: HTTP {resp['status']} `{json.dumps(resp['cuerpo'], ensure_ascii=False)}`")
        for v in d["verificaciones_fallidas"]:
            L.append(f"- Verificación fallida `{v['nombre']}`: esperado `{v['esperado']}`, obtenido `{v['obtenido']}`")
        L += [f"- Evidencia: `{d['evidencia']}`", f"- Estado: {d['estado']}", ""]

    if consolidado["advertencias"]:
        L += ["## Advertencias", ""] + [f"- {a}" for a in consolidado["advertencias"]] + [""]

    ruta = salida / "reporte.md"
    ruta.write_text("\n".join(L), encoding="utf-8")
    return ruta


def generar_reporte(plan: PlanPruebas, salida: Path) -> dict:
    consolidado = consolidar(plan, salida)
    defectos = generar_defectos(consolidado, salida)
    (salida / "reporte.json").write_text(json.dumps(consolidado, indent=2, ensure_ascii=False), "utf-8")
    (salida / "defectos.json").write_text(json.dumps(defectos, indent=2, ensure_ascii=False), "utf-8")
    escribir_markdown(consolidado, defectos, salida)
    consolidado["defectos"] = defectos
    return consolidado
