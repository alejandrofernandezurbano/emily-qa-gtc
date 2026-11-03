"""Modo opcional: un LLM propone casos de prueba (requiere ANTHROPIC_API_KEY).

Controles aplicados:
  - Solo PROPONE datos de entrada y expectativas; no ejecuta ni juzga.
  - Salida obligatoria en JSON, validada contra el esquema cerrado (Pydantic).
  - Se descartan casos de criterios inexistentes o con campos no permitidos.
  - Máximo MAX_CASOS_POR_CRITERIO casos por criterio, 1 sola llamada,
    timeout y 1 reintento: costo acotado y predecible.
"""

import json
import os
import re

from pydantic import ValidationError

from .modelos import CasoPrueba, HistoriaUsuario

MAX_CASOS_POR_CRITERIO = 3
MODELO_POR_DEFECTO = "claude-sonnet-5-5"


class LLMNoDisponible(Exception):
    pass


INSTRUCCIONES = """Eres un analista QA. A partir de criterios de aceptación propones casos de
prueba para una API HTTP. Responde SOLO con un arreglo JSON. Cada elemento:
{"criterio_id": "CA-XX", "descripcion": str,
 "datos": {"nombre": str, "correo": str, "edad": int},
 "esperado": {"status": int, "campo_en_respuesta": str|null,
              "mensaje_menciona": [str]|null, "persistido": bool|null}}
Usa status {aceptado} para aceptación y {rechazado} para rechazo.
Máximo {maximo} casos por criterio. No incluyas resultados ni conclusiones."""


def proponer_casos(hu: HistoriaUsuario, run: str) -> tuple[dict[str, list[CasoPrueba]], list[str]]:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise LLMNoDisponible("falta ANTHROPIC_API_KEY")
    try:
        import anthropic
    except ImportError as e:
        raise LLMNoDisponible("paquete 'anthropic' no instalado") from e

    k = hu.contrato
    sistema = (
        INSTRUCCIONES.replace("{aceptado}", str(k.status_aceptado))
        .replace("{rechazado}", str(k.status_rechazado))
        .replace("{maximo}", str(MAX_CASOS_POR_CRITERIO))
    )
    criterios = "\n".join(f"{c.id}: {c.texto.strip()}" for c in hu.criterios)

    try:
        cliente = anthropic.Anthropic(timeout=30, max_retries=1)
        respuesta = cliente.messages.create(
            model=os.getenv("EMILY_QA_MODELO", MODELO_POR_DEFECTO),
            max_tokens=2000,
            system=sistema,
            messages=[{"role": "user", "content": f"HU {hu.id}: {hu.descripcion}\n{criterios}"}],
        )
        texto = "".join(b.text for b in respuesta.content if getattr(b, "type", "") == "text")
    except Exception as e:  # red, credenciales, cuota...
        raise LLMNoDisponible(f"error llamando al LLM: {e}") from e

    return validar_propuesta(texto, hu, run)


def validar_propuesta(texto: str, hu: HistoriaUsuario, run: str):
    """Convierte la respuesta del LLM en casos válidos. Separada para poder probarla sin red."""
    avisos: list[str] = []
    m = re.search(r"\[.*\]", texto, re.DOTALL)
    if not m:
        return {}, ["El LLM no devolvió un arreglo JSON; se ignora su propuesta."]
    try:
        items = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}, ["El LLM devolvió JSON inválido; se ignora su propuesta."]

    ids_validos = {c.id for c in hu.criterios}
    campos = set(hu.contrato.campos)
    por_criterio: dict[str, list[CasoPrueba]] = {}
    for item in items if isinstance(items, list) else []:
        cid = item.get("criterio_id") if isinstance(item, dict) else None
        if cid not in ids_validos:
            avisos.append(f"Caso descartado: criterio inexistente {cid!r}.")
            continue
        if not set(item.get("datos", {})) <= campos:
            avisos.append(f"Caso descartado para {cid}: campos no permitidos.")
            continue
        lista = por_criterio.get(cid, [])
        if len(lista) >= MAX_CASOS_POR_CRITERIO:
            continue
        try:
            caso = CasoPrueba(
                id=f"TC-{cid}-L{len(lista) + 1}",
                criterio_id=cid,
                descripcion=str(item.get("descripcion", "")),
                origen="llm",
                datos=item["datos"],
                esperado=item["esperado"],
            )
        except (ValidationError, KeyError) as e:
            avisos.append(f"Caso descartado para {cid}: no cumple el esquema ({e.__class__.__name__}).")
            continue
        # Correos únicos por ejecución para no chocar con datos previos.
        correo = str(caso.datos.get("correo", ""))
        if "@" in correo and "." in correo.split("@")[-1]:
            usuario, dominio = correo.split("@", 1)
            caso.datos["correo"] = f"{usuario}.{run}{len(lista)}@{dominio}"
        por_criterio[cid] = lista + [caso]
    return por_criterio, avisos
