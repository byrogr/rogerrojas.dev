# Specs (SDD)

Cada feature vive en `specs/<feature>/` con tres documentos, en este orden:

| Documento | Responde | Cambia cuando… |
| --- | --- | --- |
| `requirements.md` | **Qué** debe hacer y cómo se acepta (formato EARS: *Cuando… el sistema deberá…*) | cambia el comportamiento esperado |
| `design.md` | **Cómo**: arquitectura, contratos, decisiones y alternativas | cambia la solución técnica |
| `tasks.md` | **Pasos** pequeños y verificables, trazados a los requisitos | avanza la implementación |

## Reglas

- Cada requisito tiene un ID (`R1`, `R2`…) y cada tarea cita los requisitos que cubre.
- Una tarea es terminable en una sesión corta y tiene **criterios de aceptación** comprobables.
- Las tareas **(manual)** requieren acción humana (compras, portal de Azure, DNS).
- Lo marcado **VERIFICAR** son supuestos tomados de documentación que debe confirmarse contra la fuente oficial antes de implementar.

## Features

1. [`contact-form`](./contact-form/) — formulario de contacto con captcha (Turnstile), Function en Python y correo con ACS.
2. [`azure-deploy`](./azure-deploy/) — dominio, Static Web Apps Free, CI/CD y control de costos.

Orden recomendado: `contact-form` primero (se prueba en local) y `azure-deploy` después.
