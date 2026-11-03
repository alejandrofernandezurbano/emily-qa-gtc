# Reflexión técnica

**¿Cómo evitar falsos positivos o resultados inventados por el LLM?**
El LLM nunca emite el veredicto. Solo propone casos dentro de un esquema cerrado
(Pydantic con `extra="forbid"`), y lo que no valide se descarta. El resultado lo decide
código determinista comparando lo esperado con la respuesta real, y cada conclusión
exige evidencia guardada (petición, respuesta y verificación). Si no se pudo ejecutar,
el criterio queda NO EJECUTADO, nunca aprobado. Además se verifican efectos (la
persistencia) y no solo la respuesta. El control de falsos positivos se prueba
ejecutando contra el sistema sin defecto (`APP_DEFECTO=0`): todo debe salir aprobado,
y hay una prueba automática que lo comprueba. En una versión siguiente añadiría
re-ejecución automática de los fallos para descartar fallos intermitentes.

**¿Cómo limitar iteraciones y costos?**
El modo por defecto no usa LLM (costo cero, determinista). En modo LLM: una sola llamada
por HU, máximo 3 casos por criterio, `max_tokens` acotado, timeout de 30 s y 1 reintento.
En producción: caché del plan por hash de la HU (si los criterios no cambian, no se
vuelve a llamar al modelo), presupuesto de tokens por ejecución y por proyecto, modelo
pequeño para tareas simples, y un número máximo de ciclos agente↔Emily Dev por HU
(por ejemplo 3) antes de escalar a una persona.

**¿Qué permisos y controles aplicaría?**
Mínimo privilegio: Emily QA solo lee la HU y llama a la API de un ambiente de pruebas
(lista blanca de URLs, nunca producción), con credenciales de solo prueba en un gestor
de secretos. No escribe en el repositorio ni despliega. Requieren aprobación humana:
crear o reabrir tickets, enviar defectos a Emily Dev, ejecutar contra ambientes
compartidos y cualquier acción con datos reales. Todo queda auditado (plan, evidencias,
quién aprobó). Datos de prueba sintéticos; nada de datos personales reales en prompts.

**¿Cómo conectarlo con Emily Dev y una herramienta de gestión de trabajo?**
Emily Dev publica la HU y la URL del ambiente al terminar una implementación (webhook o
cola). Emily QA ejecuta, adjunta `reporte.md` y evidencias a la HU en la herramienta
(Jira, Azure DevOps, etc.) y genera los defectos de `defectos.json` como tickets
vinculados al criterio, tras aprobación humana. Emily Dev recibe el defecto estructurado
(criterio, pasos de reproducción, esperado vs. obtenido), corrige y dispara una
re-ejecución solo de los criterios afectados (`--solo CA-03`). El ciclo termina cuando
todo está APROBADO o se alcanza el límite de iteraciones.

**¿Qué haría en una segunda versión?**
- Pruebas de interfaz con Playwright (formulario real) y capturas como evidencia.
- Modo LLM probado con corridas reales y evaluado contra un conjunto de HU de referencia
  (cobertura de criterios, casos inválidos descartados).
- Más tipos de verificación: esquema de respuesta, tiempos, seguridad básica (inyección
  en campos).
- Ejecución en Docker y en CI (GitHub Actions o Cloud Build), con el código de salida
  como compuerta de calidad.
- Integración real con la herramienta de gestión de trabajo y con Emily Dev.
- Panel con el historial de ejecuciones por HU.
