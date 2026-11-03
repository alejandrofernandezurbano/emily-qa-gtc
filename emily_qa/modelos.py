"""Modelos de datos (Pydantic). Todo lo que entra o sale de Emily QA se valida aquí.

La idea clave: un caso de prueba solo puede expresar verificaciones de una
lista CERRADA (status, campo en respuesta, mensaje, persistencia). Ni las
reglas ni el LLM pueden inventar otro tipo de verificación ni declarar un
resultado; el resultado lo decide la ejecución.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Criterio(BaseModel):
    id: str = Field(pattern=r"^CA-\d{2}$")
    texto: str


class Contrato(BaseModel):
    """Supuestos explícitos sobre la API bajo prueba (vienen del YAML de la HU)."""

    ruta_registro: str
    ruta_consulta: str
    status_aceptado: int
    status_rechazado: int
    campos: list[str]


class HistoriaUsuario(BaseModel):
    id: str
    titulo: str
    descripcion: str
    contrato: Contrato
    criterios: list[Criterio] = Field(min_length=1)


class Esperado(BaseModel):
    """Lista cerrada de verificaciones deterministas permitidas."""

    model_config = ConfigDict(extra="forbid")

    status: int
    campo_en_respuesta: str | None = None  # p. ej. "id"
    mensaje_menciona: list[str] | None = None  # alguna de estas palabras en el mensaje
    persistido: bool | None = None  # True/False: consultar GET /clientes?correo=


class CasoPrueba(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    criterio_id: str = Field(pattern=r"^CA-\d{2}$")
    descripcion: str
    origen: Literal["reglas", "llm"]
    datos: dict
    esperado: Esperado


class PlanPruebas(BaseModel):
    hu_id: str
    ejecucion_id: str
    modo: str
    contrato: Contrato
    criterios: list[Criterio]
    casos: list[CasoPrueba]
    criterios_sin_casos: dict[str, str] = {}  # criterio_id -> motivo
    advertencias: list[str] = []
