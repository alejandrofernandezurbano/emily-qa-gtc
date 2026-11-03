"""Paso 3 (núcleo): ejecutar UN caso contra la API y comprobar resultados.

Todo aquí es determinista: se compara lo esperado con lo que la API respondió
de verdad, y se guarda cada petición/respuesta como evidencia. No hay IA.
"""

import time

from .generador import normalizar
from .modelos import CasoPrueba, Contrato


def _json_o_texto(resp):
    try:
        return resp.json()
    except ValueError:
        return resp.text


def _peticion(metodo: str, ruta: str, cuerpo, resp) -> dict:
    return {
        "metodo": metodo,
        "ruta": ruta,
        "cuerpo_enviado": cuerpo,
        "status": resp.status_code,
        "respuesta": _json_o_texto(resp),
    }


def _verif(nombre: str, esperado, obtenido, ok: bool) -> dict:
    return {"nombre": nombre, "esperado": esperado, "obtenido": obtenido, "ok": ok}


def ejecutar_caso(caso: CasoPrueba, http, contrato: Contrato) -> dict:
    """Ejecuta el caso con el cliente HTTP dado y devuelve la evidencia completa."""
    esp = caso.esperado
    peticiones, verificaciones = [], []
    inicio = time.perf_counter()

    # 1) Petición principal: intentar registrar el cliente
    resp = http.post(contrato.ruta_registro, json=caso.datos)
    cuerpo = _json_o_texto(resp)
    peticiones.append(_peticion("POST", contrato.ruta_registro, caso.datos, resp))

    # 2) Código de estado
    verificaciones.append(
        _verif("status_http", esp.status, resp.status_code, resp.status_code == esp.status)
    )

    # 3) Campo obligatorio en la respuesta (p. ej. el identificador)
    if esp.campo_en_respuesta:
        valor = cuerpo.get(esp.campo_en_respuesta) if isinstance(cuerpo, dict) else None
        verificaciones.append(
            _verif(f"respuesta_tiene_{esp.campo_en_respuesta}", "valor no vacío", valor, bool(valor))
        )

    # 4) Mensaje de validación comprensible (heurística determinista:
    #    existe un mensaje y menciona el campo con problema)
    if esp.mensaje_menciona:
        mensajes = cuerpo.get("mensajes", []) if isinstance(cuerpo, dict) else []
        texto = normalizar(" ".join(map(str, mensajes)))
        ok = bool(texto) and any(normalizar(p) in texto for p in esp.mensaje_menciona)
        verificaciones.append(
            _verif("mensaje_comprensible", f"menciona alguno de {esp.mensaje_menciona}", mensajes, ok)
        )

    # 5) Persistencia: se consulta la API, no se confía en la respuesta anterior
    if esp.persistido is not None:
        params = {"correo": caso.datos.get("correo")}
        r2 = http.get(contrato.ruta_consulta, params=params)
        encontrados = _json_o_texto(r2)
        peticiones.append(_peticion("GET", contrato.ruta_consulta, params, r2))
        persistido = isinstance(encontrados, list) and len(encontrados) > 0
        verificaciones.append(
            _verif("persistencia", esp.persistido, persistido, persistido == esp.persistido)
        )

    return {
        "caso_id": caso.id,
        "criterio_id": caso.criterio_id,
        "descripcion": caso.descripcion,
        "origen": caso.origen,
        "duracion_ms": round((time.perf_counter() - inicio) * 1000, 1),
        "peticiones": peticiones,
        "verificaciones": verificaciones,
        "ok": all(v["ok"] for v in verificaciones),
    }
