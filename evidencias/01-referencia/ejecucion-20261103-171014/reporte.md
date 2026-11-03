# Reporte Emily QA · HU-DEMO-001

- Ejecución: `20261103-171014` · modo de generación: `reglas`
- Resultado: 2 aprobados · 1 fallidos · 0 no ejecutados
- Evidencias: `pytest.log`, `junit.xml`, `casos/*.json` (petición, respuesta y verificaciones de cada caso)

## Resultado por criterio

| Criterio | Estado | Casos | Conclusión |
|---|---|---|---|
| CA-01 | ✅ APROBADO | TC-CA-01-1 ✅, TC-CA-01-2 ✅ | Todos los casos cumplen el criterio. |
| CA-02 | ✅ APROBADO | TC-CA-02-1 ✅, TC-CA-02-2 ✅ | Todos los casos cumplen el criterio. |
| CA-03 | ❌ FALLIDO | TC-CA-03-1 ❌, TC-CA-03-2 ❌ | Al menos un caso incumple el criterio. |

## Detalle por criterio

### CA-01 · APROBADO

> Si nombre, correo válido y edad igual o mayor a 18 son correctos, el registro debe aceptarse y devolver un identificador.

- ✅ **TC-CA-01-1** (reglas): Registro válido con edad límite (18) · evidencia: `casos/TC-CA-01-1.json`
- ✅ **TC-CA-01-2** (reglas): Registro válido con edad típica (35) · evidencia: `casos/TC-CA-01-2.json`

### CA-02 · APROBADO

> Si el correo no tiene un formato válido, el registro debe rechazarse con un mensaje de validación comprensible.

- ✅ **TC-CA-02-1** (reglas): Correo sin @ · evidencia: `casos/TC-CA-02-1.json`
- ✅ **TC-CA-02-2** (reglas): Correo sin dominio · evidencia: `casos/TC-CA-02-2.json`

### CA-03 · FALLIDO

> Si la edad es menor a 18 años, el registro debe rechazarse y no debe persistirse el cliente.

- ❌ **TC-CA-03-1** (reglas): Edad justo debajo del límite (17) · evidencia: `casos/TC-CA-03-1.json` — [CA-03] persistencia: esperado=False obtenido=True
- ❌ **TC-CA-03-2** (reglas): Edad claramente menor (10) · evidencia: `casos/TC-CA-03-2.json` — [CA-03] persistencia: esperado=False obtenido=True

## Defectos detectados

### DEF-001 · CA-03 incumplido: Edad justo debajo del límite (17)

- Criterio que sustenta la conclusión: **CA-03** — Si la edad es menor a 18 años, el registro debe rechazarse y no debe persistirse el cliente.
- Pasos para reproducir:
  1. `POST /clientes {"nombre": "Ana Pérez", "correo": "ana.3.171014@ejemplo.com", "edad": 17}`
  2. `GET /clientes {"correo": "ana.3.171014@ejemplo.com"}`
- Respuesta de la API al registro: HTTP 422 `{"error": "validacion", "mensajes": ["El cliente debe ser mayor de edad (mínimo 18 años, recibido 17)."]}`
- Verificación fallida `persistencia`: esperado `False`, obtenido `True`
- Evidencia: `casos/TC-CA-03-1.json`
- Estado: pendiente_revision_humana

### DEF-002 · CA-03 incumplido: Edad claramente menor (10)

- Criterio que sustenta la conclusión: **CA-03** — Si la edad es menor a 18 años, el registro debe rechazarse y no debe persistirse el cliente.
- Pasos para reproducir:
  1. `POST /clientes {"nombre": "Ana Pérez", "correo": "ana.4.171014@ejemplo.com", "edad": 10}`
  2. `GET /clientes {"correo": "ana.4.171014@ejemplo.com"}`
- Respuesta de la API al registro: HTTP 422 `{"error": "validacion", "mensajes": ["El cliente debe ser mayor de edad (mínimo 18 años, recibido 10)."]}`
- Verificación fallida `persistencia`: esperado `False`, obtenido `True`
- Evidencia: `casos/TC-CA-03-2.json`
- Estado: pendiente_revision_humana
