"""Paso 2: convertir criterios de aceptación en casos de prueba trazables.

Dos modos:
  - "reglas" (por defecto, sin credenciales): plantillas deterministas que
    reconocen patrones del texto del criterio (aceptación, correo inválido,
    edad mínima). Mismo input -> mismo plan, siempre.
  - "llm" (opcional): un LLM PROPONE casos; cada caso se valida contra el
    esquema cerrado de `modelos.Esperado`. Lo que no valide se descarta y ese
    criterio cae al modo reglas. El LLM nunca decide si una prueba pasó.

Si un criterio no encaja en ninguna regla, NO se inventa una prueba: queda
registrado como "sin casos" y el reporte lo muestra como NO EJECUTADO.
"""

import re
import unicodedata

from .modelos import CasoPrueba, Contrato, Criterio, Esperado, HistoriaUsuario, PlanPruebas


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar palabras clave."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


def extraer_edad(texto: str, por_defecto: int = 18) -> int:
    m = re.search(r"\b(\d{1,3})\b", texto)
    return int(m.group(1)) if m else por_defecto


def _datos_validos(caso_n: str, run: str, edad: int) -> dict:
    return {"nombre": "Ana Pérez", "correo": f"ana.{caso_n}.{run}@ejemplo.com", "edad": edad}


# ---------------------------------------------------------------- reglas ---
# Cada regla recibe (texto_normalizado, criterio, contrato, run) y devuelve
# una lista de casos si reconoce el criterio, o None si no aplica.


def regla_aceptacion(t: str, c: Criterio, k: Contrato, run: str):
    if "aceptarse" not in t and "aceptar" not in t:
        return None
    edad_min = extraer_edad(t)
    esperado = Esperado(
        status=k.status_aceptado,
        campo_en_respuesta="id" if "identificador" in t else None,
        persistido=True,
    )
    return [
        (f"Registro válido con edad límite ({edad_min})", _datos_validos("1", run, edad_min), esperado),
        (f"Registro válido con edad típica ({edad_min + 17})", _datos_validos("2", run, edad_min + 17), esperado),
    ]


def regla_correo_invalido(t: str, c: Criterio, k: Contrato, run: str):
    if not ("correo" in t and "rechaz" in t and ("formato" in t or "valido" in t)):
        return None
    esperado = Esperado(
        status=k.status_rechazado,
        mensaje_menciona=["correo"] if "mensaje" in t else None,
    )
    return [
        ("Correo sin @", {"nombre": "Luis Gómez", "correo": f"luis.{run}.ejemplo.com", "edad": 30}, esperado),
        ("Correo sin dominio", {"nombre": "Luis Gómez", "correo": f"luis.{run}@", "edad": 30}, esperado),
    ]


def regla_edad_minima(t: str, c: Criterio, k: Contrato, run: str):
    if not ("edad" in t and "menor" in t and "rechaz" in t):
        return None
    edad_min = extraer_edad(t)
    esperado = Esperado(
        status=k.status_rechazado,
        persistido=False if "persist" in t else None,
    )
    return [
        (f"Edad justo debajo del límite ({edad_min - 1})", _datos_validos("3", run, edad_min - 1), esperado),
        ("Edad claramente menor (10)", _datos_validos("4", run, 10), esperado),
    ]


# Orden importa: la primera regla que reconoce el criterio gana.
REGLAS = [regla_edad_minima, regla_correo_invalido, regla_aceptacion]


def casos_por_reglas(c: Criterio, k: Contrato, run: str) -> list[CasoPrueba]:
    t = normalizar(c.texto)
    for regla in REGLAS:
        propuestas = regla(t, c, k, run)
        if propuestas:
            return [
                CasoPrueba(
                    id=f"TC-{c.id}-{i}",
                    criterio_id=c.id,
                    descripcion=desc,
                    origen="reglas",
                    datos=datos,
                    esperado=esp,
                )
                for i, (desc, datos, esp) in enumerate(propuestas, start=1)
            ]
    return []


# ------------------------------------------------------------------ plan ---


def generar_plan(
    hu: HistoriaUsuario,
    ejecucion_id: str,
    modo: str = "reglas",
    solo: set[str] | None = None,
) -> PlanPruebas:
    casos: list[CasoPrueba] = []
    sin_casos: dict[str, str] = {}
    advertencias: list[str] = []
    run = ejecucion_id.replace("-", "")[-6:]  # sufijo corto para correos únicos

    propuestos_llm: dict[str, list[CasoPrueba]] = {}
    if modo == "llm":
        from .llm import LLMNoDisponible, proponer_casos

        try:
            propuestos_llm, avisos = proponer_casos(hu, run)
            advertencias.extend(avisos)
        except LLMNoDisponible as e:
            advertencias.append(f"Modo LLM no disponible ({e}); se usan reglas deterministas.")

    for c in hu.criterios:
        if solo and c.id not in solo:
            sin_casos[c.id] = "Excluido en esta ejecución (opción --solo)."
            continue
        generados = propuestos_llm.get(c.id) or casos_por_reglas(c, hu.contrato, run)
        if not generados:
            sin_casos[c.id] = "Ninguna regla reconoce este criterio; requiere revisión humana."
        casos.extend(generados)

    return PlanPruebas(
        hu_id=hu.id,
        ejecucion_id=ejecucion_id,
        modo=modo,
        contrato=hu.contrato,
        criterios=hu.criterios,
        casos=casos,
        criterios_sin_casos=sin_casos,
        advertencias=advertencias,
    )
