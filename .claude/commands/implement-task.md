---
description: Implementa la siguiente tarea pendiente de una spec SDD (usa el ciclo de CLAUDE.md)
argument-hint: "[feature, p. ej. contact-form | azure-deploy]"
---

Feature objetivo: $ARGUMENTS (si está vacío, elige la primera spec en `specs/` que tenga tareas sin marcar).

1. Lee `CLAUDE.md`, `specs/README.md` y, de la feature, `requirements.md`, `design.md` y `tasks.md`.
2. Elige la **primera tarea sin marcar** cuyas dependencias estén completas. Dime cuál es y qué requisitos cubre (en una o dos líneas).
3. Si la tarea es ambigua o contradice la spec, **detente y pregúntame** antes de escribir código.
4. Impleméntala con el cambio mínimo. Si es lógica, escribe primero la prueba.
5. Ejecuta las verificaciones de la DoD (`npm run build` y, si aplica, `cd api && python -m pytest`).
6. Marca la tarea `[x]` en `tasks.md` y actualiza la spec si algo cambió.
7. Resume en 3 líneas qué hiciste y propón la siguiente tarea. No empieces la siguiente sin que lo pida.

Las tareas marcadas **(manual)** las hago yo (compras, portal de Azure, DNS): dame los pasos exactos y espera mi confirmación.
