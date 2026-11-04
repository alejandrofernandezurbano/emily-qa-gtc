# Emily QA · prototipo de agente de aseguramiento de calidad

Prueba técnica GTC Corporation · HU-DEMO-001 «Validación de registro de clientes».

Emily QA lee los criterios de aceptación de una historia de usuario, los convierte en
casos de prueba trazables, los **ejecuta de verdad con Pytest contra una API**, guarda
la evidencia de cada petición y produce un reporte por criterio (aprobado / fallido /
no ejecutado) y una lista de defectos listos para revisión humana.

> Principio de diseño: **el resultado nunca lo declara un LLM**. Un criterio solo queda
> FALLIDO si una verificación determinista falló y hay evidencia guardada; si algo no se
> pudo ejecutar, queda NO EJECUTADO, nunca aprobado.

## Ejecución rápida

Requisitos: Python 3.10 o superior.

```bash
git clone https://github.com/alejandrofernandezurbano/emily-qa-gtc
cd emily-qa-gtc
python -m venv .venv
# Windows (PowerShell): Set-ExecutionPolicy -Scope Process Bypass ; .venv\Scripts\Activate.ps1
# Windows (cmd):        .venv\Scripts\activate.bat
# Linux/Mac:            source .venv/bin/activate
.venv\Scripts\python.exe -m pip install -r requirements.txt

python -m emily_qa          # comando único: genera, ejecuta y reporta
```

O con doble clic / un solo comando: `ejecutar.bat` (Windows) o `./ejecutar.sh` (Linux/Mac).

Salida esperada (el defecto sembrado se detecta en CA-03):

```
[1/3] Plan: 6 casos para 3 criterios -> evidencias/ejecucion-.../plan.json
[2/3] Ejecutando Pytest...
[3/3] Reporte: evidencias/ejecucion-.../reporte.md

  ✅ CA-01  APROBADO      Todos los casos cumplen el criterio.
  ✅ CA-02  APROBADO      Todos los casos cumplen el criterio.
  ❌ CA-03  FALLIDO       Al menos un caso incumple el criterio.
  -> DEF-001 [CA-03] CA-03 incumplido: Edad justo debajo del límite (17)
  -> DEF-002 [CA-03] CA-03 incumplido: Edad claramente menor (10)
```

Código de salida: `0` sin fallos, `1` hay criterios fallidos, `2` HU inválida,
`3` no se pudo ejecutar ningún caso. Sirve tal cual en un pipeline de CI.

### Otras formas de ejecutar

| Qué | Comando |
|---|---|
| Contra un servidor HTTP real | `uvicorn app_simulada.main:app --port 8000` y en otra terminal `python -m emily_qa --base-url http://127.0.0.1:8000` |
| Solo algunos criterios | `python -m emily_qa --solo CA-01,CA-03` (el resto sale como NO EJECUTADO) |
| Sistema sin el defecto (control de falsos positivos) | `APP_DEFECTO=0 python -m emily_qa` (Windows: `set APP_DEFECTO=0`) → todo APROBADO |
| Generación de casos con LLM (opcional) | `pip install anthropic`, definir `ANTHROPIC_API_KEY` y `python -m emily_qa --modo llm` |
| Pruebas del propio agente | `pytest` (12 pruebas: generador, validación del LLM, verificador y flujo completo) |

Sin credenciales todo funciona en modo `reglas`; si se pide `--modo llm` sin clave, el
agente avisa y usa reglas.

## Qué hay en cada carpeta

```
hu/HU-DEMO-001.yaml        Entrada: HU, criterios CA-01..03 y contrato de la API (supuestos explícitos)
app_simulada/main.py       Sistema bajo prueba: API FastAPI de clientes con un DEFECTO SEMBRADO
emily_qa/
  interprete.py            1. Lee y valida la HU
  generador.py             2. Criterios -> casos (reglas deterministas; LLM opcional)
  llm.py                      Propuesta de casos por LLM + validación estricta de su salida
  modelos.py                  Esquemas Pydantic (lista cerrada de verificaciones permitidas)
  verificador.py           3. Ejecuta un caso: peticiones HTTP + aserciones + evidencia
  ejecutor.py                 Lanza Pytest y guarda su salida
  reporte.py               4. Estado por criterio, reporte.md/json y defectos.json
  __main__.py                 Comando único que orquesta los pasos
qa_runner/                 Test de Pytest parametrizado: un test por caso del plan
tests/                     Pruebas unitarias y end-to-end del propio agente
docs/ARQUITECTURA.md       Diagrama y explicación de la arquitectura
docs/REFLEXION.md          Reflexión técnica (falsos positivos, costos, permisos, integración, v2)
evidencias/                Ejecuciones reales incluidas como entregable (ver abajo)
```

## El defecto sembrado

En `app_simulada/main.py` el cliente se **guarda antes de validar la edad**. La API
responde correctamente `422` con un mensaje claro, así que mirando solo la respuesta
parece que CA-03 se cumple. Emily QA lo detecta porque, además del status, **consulta
la persistencia** (`GET /clientes?correo=...`) y encuentra al menor de edad guardado.
Es un defecto que un agente que «lee la respuesta y opina» daría por bueno.

## Evidencias incluidas (ejecuciones reales)

| Carpeta | Escenario | Resultado |
|---|---|---|
| `evidencias/01-referencia/` | Ejecución estándar (`python -m emily_qa`) | CA-01 ✅, CA-02 ✅, CA-03 ❌ (DEF-001, DEF-002) |
| `evidencias/02-servidor-real-solo-CA02-CA03/` | Contra `uvicorn` por HTTP real, con `--solo CA-02,CA-03` | CA-01 ⚪ no ejecutado, CA-02 ✅, CA-03 ❌ |
| `evidencias/03-servicio-caido/` | `--base-url` apuntando a un puerto sin servicio | Los tres ⚪ NO EJECUTADO (nunca falso aprobado/fallido) |

Cada ejecución contiene: `plan.json` (casos generados), `pytest.log` y `junit.xml`
(salida de Pytest), `casos/*.json` (petición, respuesta y verificaciones de cada caso),
`reporte.md` / `reporte.json` (estado por criterio) y `defectos.json` (para Emily Dev).

## Supuestos

- «Aceptar» = HTTP 201 con `id`; «rechazar» = HTTP 422. Están declarados en el bloque
  `contrato` del YAML para que el agente no los invente.
- «Mensaje comprensible» se verifica de forma determinista como: existe un mensaje y
  menciona el campo con problema («correo»). Es una aproximación; un juicio de
  redacción más fino podría pedirse a un LLM, pero solo como observación, no como veredicto.
- Cada caso usa un correo único por ejecución, así se puede repetir contra un servidor
  con datos previos sin interferencias.
- La API simulada guarda en memoria; no hay base de datos real.

## Limitaciones (qué no hace todavía)

- Las reglas reconocen los patrones de esta HU (aceptación, correo inválido, edad mínima).
  Un criterio que no encaja no se inventa: queda NO EJECUTADO con «requiere revisión humana».
- El modo LLM está implementado y su validación tiene pruebas, pero en esta entrega se
  ejecutó con reglas (sin credenciales); no hay corrida real con LLM incluida.
- Solo pruebas de API por HTTP; no hay pruebas de interfaz (Playwright) ni capturas de pantalla.
- La integración con Emily Dev y la herramienta de gestión de trabajo está diseñada
  (`defectos.json` + estado `pendiente_revision_humana`), no implementada.

## Herramientas de IA utilizadas

- **Claude (Anthropic)** generó la mayor parte del código y la documentación a partir del
  enunciado.
- Mi trabajo: revisar y comparar dos propuestas de solución, elegir este diseño (detección
  por persistencia, veredicto determinista y modo sin LLM), ejecutar y validar la solución
  en mi equipo Windows, y estudiar cada módulo para poder explicarlo y modificarlo.
- Librerías: FastAPI (API simulada), Pytest (ejecución), httpx (cliente HTTP), Pydantic
  (validación de esquemas), PyYAML. Opcional: SDK de Anthropic para `--modo llm`.
