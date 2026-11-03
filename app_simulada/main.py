"""API simulada de registro de clientes (sistema bajo prueba de HU-DEMO-001).

Contiene un DEFECTO SEMBRADO a propósito (ver comentario en `registrar`):
el cliente se guarda ANTES de validar la edad. La respuesta HTTP parece
correcta (422), pero el cliente menor de edad queda persistido, lo que
incumple CA-03. Solo se detecta consultando la persistencia, no leyendo
la respuesta.

El defecto se puede apagar con la variable de entorno APP_DEFECTO=0.

Ejecutar como servidor real:  uvicorn app_simulada.main:app --port 8000
"""

import os
import re
import uuid

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
EDAD_MINIMA = 18


def crear_app(defecto_activo: bool | None = None) -> FastAPI:
    """Crea una instancia nueva de la API con su propio almacenamiento en memoria."""
    if defecto_activo is None:
        defecto_activo = os.getenv("APP_DEFECTO", "1") != "0"

    app = FastAPI(title="API simulada de clientes (HU-DEMO-001)")
    app.state.defecto_activo = defecto_activo
    clientes: dict[str, dict] = {}  # "base de datos" en memoria: id -> cliente

    def rechazar(mensajes: list[str]) -> JSONResponse:
        return JSONResponse(status_code=422, content={"error": "validacion", "mensajes": mensajes})

    @app.get("/salud")
    def salud():
        return {"estado": "ok", "defecto_activo": app.state.defecto_activo}

    @app.post("/clientes", status_code=201)
    def registrar(datos: dict = Body(...)):
        nombre = str(datos.get("nombre") or "").strip()
        correo = str(datos.get("correo") or "").strip()
        edad = datos.get("edad")

        # 1) Validaciones de formato (nombre, correo, tipo de edad)
        mensajes = []
        if not nombre:
            mensajes.append("El nombre es obligatorio.")
        if not PATRON_CORREO.match(correo):
            mensajes.append(
                f"El correo '{correo}' no tiene un formato válido. Ejemplo: nombre@dominio.com"
            )
        if not isinstance(edad, int) or isinstance(edad, bool):
            mensajes.append("La edad es obligatoria y debe ser un número entero.")
        if mensajes:
            return rechazar(mensajes)

        cliente = {"id": str(uuid.uuid4()), "nombre": nombre, "correo": correo, "edad": edad}

        if app.state.defecto_activo:
            # >>> DEFECTO SEMBRADO (incumple CA-03) <<<
            # Se persiste el cliente antes de validar la edad mínima.
            clientes[cliente["id"]] = cliente

        # 2) Regla de negocio: edad mínima
        if edad < EDAD_MINIMA:
            return rechazar(
                [f"El cliente debe ser mayor de edad (mínimo {EDAD_MINIMA} años, recibido {edad})."]
            )

        # 3) Persistencia correcta: solo si pasó todas las validaciones
        clientes[cliente["id"]] = cliente
        return cliente

    @app.get("/clientes")
    def listar(correo: str | None = None):
        resultado = list(clientes.values())
        if correo is not None:
            resultado = [c for c in resultado if c["correo"] == correo]
        return resultado

    return app


app = crear_app()
