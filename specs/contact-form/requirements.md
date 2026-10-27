# Formulario de contacto — Requisitos

## Contexto

La portada tiene un formulario (`#contacto`) que hoy apunta a un servicio externo placeholder (`formspree.io/f/TU_ID`).
Se reemplaza por una API propia en Azure Functions (Python) que valida un captcha de Cloudflare Turnstile y envía
el mensaje al correo del propietario con Azure Communication Services Email, a costo casi nulo.

## Alcance

**Dentro:** formulario, widget de captcha, endpoint `POST /api/contact`, validación, envío de correo, pruebas.
**Fuera:** guardar mensajes en base de datos, panel de administración, respuestas automáticas al visitante, newsletter.

## Requisitos (EARS)

**R1 — Envío correcto.** Cuando un visitante envíe el formulario con datos válidos y un token de captcha válido, el
sistema deberá enviar un correo al propietario con nombre, correo y mensaje del visitante, y mostrar una confirmación en español.

**R2 — Captcha obligatorio.** Si falta el token de captcha, o Cloudflare lo rechaza (inválido, caducado o ya usado),
el sistema no deberá enviar ningún correo y deberá responder con un error de captcha comprensible para el usuario.

**R3 — Verificación en el servidor.** El sistema deberá validar el token contra el endpoint de verificación de
Turnstile **solo desde la Function**; la clave secreta nunca deberá llegar al navegador ni al repositorio.

**R4 — Campo trampa (honeypot).** Si el campo oculto `website` llega con contenido, el sistema deberá responder como
si el envío hubiera sido exitoso, sin enviar correo y sin llamar a Turnstile.

**R5 — Validación de datos.** El sistema deberá rechazar con `400` y mensaje por campo cuando:
`nombre` esté vacío o supere 100 caracteres; `email` no tenga formato válido o supere 254 caracteres; `mensaje` tenga
menos de 10 o más de 2000 caracteres. Deberá recortar espacios y rechazar saltos de línea en `nombre` y `email`
(evita inyección de cabeceras).

**R6 — Contenido seguro.** El sistema deberá escapar todo texto del visitante antes de incluirlo en el cuerpo HTML
del correo, y enviar siempre también una versión en texto plano.

**R7 — Solo lo necesario.** El endpoint deberá aceptar únicamente `POST` con `application/json` y un cuerpo de
máximo 10 KB; cualquier otro método o tipo deberá responder `405` / `415` / `413`.

**R8 — Errores controlados.** Si falla el servicio de correo o Turnstile no responde, el sistema deberá responder `500`/`503`
con un mensaje genérico en español, sin exponer detalles internos, y registrar el error técnico sin incluir el contenido
del mensaje ni el correo del visitante.

**R9 — Experiencia del formulario.** Mientras se envía, el sistema deberá deshabilitar el botón y anunciar el estado en
una región `aria-live`. Tras un éxito deberá limpiar el formulario; tras un error de captcha deberá reiniciar el widget
para obtener un token nuevo.

**R10 — Configuración sin secretos en el código.** Los valores sensibles deberán leerse de variables de entorno
(`TURNSTILE_SECRET_KEY`, `ACS_CONNECTION_STRING`, `MAIL_SENDER`, `MAIL_TO`). Solo la *site key* es pública
(`PUBLIC_TURNSTILE_SITE_KEY`, inyectada en el build de Astro).

**R11 — Costo.** La solución deberá funcionar solo con Static Web Apps Free (función administrada), Turnstile y
ACS Email; no deberá introducir recursos de Azure con costo fijo mensual.

**R12 — Pruebas.** La lógica de validación, el cliente de Turnstile y el armado del correo deberán tener pruebas
automáticas con `pytest` que **no** hagan llamadas de red reales.

## Criterios de aceptación globales

- [ ] Enviar el formulario en local (con claves de prueba) entrega un correo al buzón configurado.
- [ ] Un token inválido o repetido no entrega correo y muestra el error de captcha.
- [ ] Con el honeypot lleno, la respuesta es `200` y no hay correo ni llamada a Turnstile.
- [ ] `npm run build` y `cd api && python -m pytest` pasan.
- [ ] Ningún secreto aparece en el repositorio (`git grep` limpio).
