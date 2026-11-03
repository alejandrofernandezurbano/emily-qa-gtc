# Reporte Emily QA · HU-DEMO-001

- Ejecución: `20261103-171018` · modo de generación: `reglas`
- Resultado: 0 aprobados · 0 fallidos · 3 no ejecutados
- Evidencias: `pytest.log`, `junit.xml`, `casos/*.json` (petición, respuesta y verificaciones de cada caso)

## Resultado por criterio

| Criterio | Estado | Casos | Conclusión |
|---|---|---|---|
| CA-01 | ⚪ NO EJECUTADO | TC-CA-01-1 ⚪, TC-CA-01-2 ⚪ | Ningún caso pudo ejecutarse: El servicio no respondió (ConnectError: [Errno 111] Connection refused) |
| CA-02 | ⚪ NO EJECUTADO | TC-CA-02-1 ⚪, TC-CA-02-2 ⚪ | Ningún caso pudo ejecutarse: El servicio no respondió (ConnectError: [Errno 111] Connection refused) |
| CA-03 | ⚪ NO EJECUTADO | TC-CA-03-1 ⚪, TC-CA-03-2 ⚪ | Ningún caso pudo ejecutarse: El servicio no respondió (ConnectError: [Errno 111] Connection refused) |

## Detalle por criterio

### CA-01 · NO EJECUTADO

> Si nombre, correo válido y edad igual o mayor a 18 son correctos, el registro debe aceptarse y devolver un identificador.

- ⚪ **TC-CA-01-1** (reglas): Registro válido con edad límite (18) — El servicio no respondió (ConnectError: [Errno 111] Connection refused)
- ⚪ **TC-CA-01-2** (reglas): Registro válido con edad típica (35) — El servicio no respondió (ConnectError: [Errno 111] Connection refused)

### CA-02 · NO EJECUTADO

> Si el correo no tiene un formato válido, el registro debe rechazarse con un mensaje de validación comprensible.

- ⚪ **TC-CA-02-1** (reglas): Correo sin @ — El servicio no respondió (ConnectError: [Errno 111] Connection refused)
- ⚪ **TC-CA-02-2** (reglas): Correo sin dominio — El servicio no respondió (ConnectError: [Errno 111] Connection refused)

### CA-03 · NO EJECUTADO

> Si la edad es menor a 18 años, el registro debe rechazarse y no debe persistirse el cliente.

- ⚪ **TC-CA-03-1** (reglas): Edad justo debajo del límite (17) — El servicio no respondió (ConnectError: [Errno 111] Connection refused)
- ⚪ **TC-CA-03-2** (reglas): Edad claramente menor (10) — El servicio no respondió (ConnectError: [Errno 111] Connection refused)

## Defectos detectados

Ninguno.