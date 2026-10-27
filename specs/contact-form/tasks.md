# Formulario de contacto — Tareas

Marca `[x]` al terminar. «Cubre» indica los requisitos de `requirements.md`.

## Fase 0 — Preparación

- [x] **T0.1 (manual)** Crear el sitio en Cloudflare Turnstile (modo gestionado) y anotar *site key* y *secret key*. Dominios permitidos: `localhost` y, más adelante, el dominio real. *Cubre: R3, R10.*
- [x] **T0.2** Resolver los puntos **VERIFICAR** de `design.md` (Turnstile gratis, modelo v2 de Python en SWA, `replyTo` del SDK, claves de prueba) leyendo la documentación oficial; anotar la conclusión en `design.md`.
  *Aceptación:* ningún **VERIFICAR** queda sin resolver.

## Fase 1 — API en Python

- [x] **T1.1** Crear `api/` con `host.json`, `requirements.txt`, `local.settings.sample.json` y un `function_app.py` mínimo que responda `405` a no-POST. Crear `public/staticwebapp.config.json` mínimo con `platform.apiRuntime: python:3.11` (SWA lo lee de la carpeta desplegada `dist/`, no de `api/`; `azure-deploy` T1.2 le añade la 404 y las cabeceras). Añadir `api/local.settings.json` al `.gitignore`. *Cubre: R7, R10.*
  *Aceptación:* `func start` (o el emulador de SWA) sirve `/api/contact`.
- [x] **T1.2** `contact/validation.py` + `tests/test_validation.py`: reglas de R5 como funciones puras (recorte, longitudes, formato de email, rechazo de saltos de línea). *Cubre: R5.*
  *Aceptación:* casos válidos, límites exactos (9/10 y 2000/2001 caracteres) y cabeceras inyectadas cubiertos.
- [x] **T1.3** `contact/turnstile.py` + `tests/test_turnstile.py`: cliente de siteverify con timeout, interpretación de `success` y `error-codes` (incluido `timeout-or-duplicate`), envío de IP opcional. HTTP mockeado. *Cubre: R2, R3, R8, R12.*
- [x] **T1.4** `contact/mailer.py` + `tests/test_mailer.py`: construir mensaje (texto + HTML con escape) y enviar con `EmailClient.begin_send`; `EmailClient` mockeado. *Cubre: R1, R6, R8, R12.*
  *Aceptación:* un `<script>` en el mensaje aparece escapado en el HTML.
- [x] **T1.5** `function_app.py` + `tests/test_endpoint.py`: orquestación completa — método/tipo/tamaño (R7), honeypot (R4), validación (R5), captcha (R2/R3), envío (R1), errores (R8). Logs sin contenido del mensaje. *Cubre: R1–R8.*
  *Aceptación:* tabla de respuestas de `design.md` cumplida por pruebas.

## Fase 2 — Frontend

- [x] **T2.1** En `src/pages/index.astro`: quitar `formspree`, apuntar el formulario a `/api/contact`, añadir widget Turnstile, campo `website` (honeypot), región de estado y `<noscript>`. Estilos solo con variables de `global.css`. *Cubre: R4, R9, R10.*
- [x] **T2.2** Script de envío en `src/scripts/contact.ts` (`fetch`, estados, `turnstile.reset()` en error, limpiar al éxito, botón deshabilitado). Sin dependencias. Fijar `vite.build.assetsInlineLimit: 0` en `astro.config.mjs` (ver «Frontend» en `design.md`). *Cubre: R9.*
  *Aceptación:* tras `npm run build`, ningún HTML de `dist/` contiene `<script>` inline ni atributos `on*`.
- [x] **T2.3** Documentar `.env.example` con `PUBLIC_TURNSTILE_SITE_KEY` (comentado, con la clave de prueba de Turnstile) y los pasos de desarrollo local en `design.md` («Desarrollo local»). El README queda como presentación del sitio, sin instrucciones técnicas. *Cubre: R10.*
  *Aceptación:* `npm run build` pasa.

## Fase 3 — Prueba de extremo a extremo

- [x] **T3.1** Probar en local con el emulador de Static Web Apps (`swa start`) y claves de prueba/reales de Turnstile y un recurso ACS de pruebas: éxito, captcha inválido, honeypot, validación. *Cubre: todos.*
- [ ] **T3.2** Revisión final: `git grep` de secretos, `pytest`, `npm run build`, lista de requisitos R1–R12 marcada.

> El despliegue y la configuración en Azure están en `specs/azure-deploy/`.
