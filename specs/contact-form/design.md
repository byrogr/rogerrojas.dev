# Formulario de contacto — Diseño

## Arquitectura

```mermaid
sequenceDiagram
    participant V as Visitante (navegador)
    participant T as Cloudflare Turnstile
    participant F as /api/contact (Function Python, SWA)
    participant A as Azure Communication Services Email
    V->>T: carga widget (site key pública)
    T-->>V: token (caduca a los 5 min, un solo uso)
    V->>F: POST JSON {nombre, email, mensaje, token, website}
    F->>F: honeypot → validar campos
    F->>T: POST siteverify (secret + token + IP)
    T-->>F: {success, error-codes}
    F->>A: begin_send(mensaje)
    A-->>F: operación aceptada
    F-->>V: 200 {ok:true}
```

Todo vive bajo el mismo dominio (`/api` lo enruta Static Web Apps), así que **no hay CORS**.

## Contrato de la API

`POST /api/contact` · `Content-Type: application/json`

Petición:

```json
{
  "nombre": "Ana Pérez",
  "email": "ana@ejemplo.com",
  "mensaje": "Hola Roger, me gustaría…",
  "token": "<cf-turnstile-response>",
  "website": ""
}
```

Respuestas:

| Código | Cuándo | Cuerpo |
| --- | --- | --- |
| `200` | Enviado, o honeypot activado | `{"ok": true}` |
| `400` | JSON mal formado, no UTF-8 o que no es un objeto | `{"ok": false, "code": "bad_request"}` |
| `400` | Validación fallida | `{"ok": false, "code": "validation", "fields": {"email": "Correo no válido"}}` |
| `400` | Captcha ausente/inválido | `{"ok": false, "code": "captcha", "message": "No pudimos verificar que eres humano. Inténtalo de nuevo."}` |
| `413` / `415` / `405` | Cuerpo grande / tipo / método | `{"ok": false, "code": "bad_request"}` |
| `500` | Error inesperado en la función | `{"ok": false, "code": "internal", "message": "No pudimos enviar tu mensaje. Inténtalo más tarde."}` |
| `503` | Turnstile o ACS no disponible, o falta una variable de entorno | `{"ok": false, "code": "unavailable", "message": "No pudimos enviar tu mensaje. Inténtalo más tarde."}` |

Orden de comprobación en `function_app.py`: método (`405`, con cabecera `Allow: POST`) → `Content-Type` (`415`; se acepta `application/json; charset=…`) → tamaño > 10 240 bytes (`413`) → JSON (`400 bad_request`) → honeypot (`200`) → validación (`400 validation`) → configuración (`503`, **antes** de Turnstile para no gastar el token del visitante) → captcha (`400 captcha` / `503`) → envío (`503` si falla). Cualquier excepción no prevista da `500 internal`. Las respuestas son JSON UTF-8.

La IP enviada a Turnstile (`remoteip`) es la primera de `X-Forwarded-For`, sin puerto, y solo se envía si es una IPv4/IPv6 válida.

Logs: solo eventos («honeypot activado», «captcha rechazado» con sus códigos, «mensaje enviado»), nombres de variables que faltan y tipos de error. Nunca nombre, correo, mensaje, token, IP ni secretos (R8; hay pruebas que lo comprueban).

## Estructura de `api/`

```
api/
  function_app.py          # registro de la función HTTP (modelo v2) y orquestación
  host.json
  requirements.txt         # dependencias de producción: azure-functions, azure-communication-email; cada tarea añade la suya
  requirements-dev.txt     # requirements.txt + pytest (solo local, no se despliega)
  pytest.ini               # pythonpath y carpeta de pruebas
  .funcignore              # excluye .venv, tests y archivos locales del paquete desplegado
  local.settings.sample.json   # plantilla sin secretos (claves de prueba de Turnstile); el real está en .gitignore
  contact/
    validation.py          # parseo y reglas de R5 (funciones puras)
    turnstile.py           # cliente de siteverify con urllib estándar (timeout 5 s, sin reintentos)
    mailer.py              # armado del mensaje (texto + HTML escapado) y envío con EmailClient.begin_send, sin esperar al poller
    config.py              # lectura de variables de entorno (R10)
  tests/
    test_validation.py
    test_turnstile.py
    test_mailer.py
    test_endpoint.py
```

## Decisiones

1. **Cloudflare Turnstile** sobre reCAPTCHA/hCaptcha: gratuito, sin acertijos en la mayoría de casos y más respetuoso con la privacidad. *Verificado (V1):* el plan Free sigue vigente (hasta 20 widgets, 10 hostnames por widget, desafíos ilimitados).
2. **Función administrada de SWA** (plan Free) en lugar de una Function app propia: costo cero. Limitaciones aceptadas: solo triggers HTTP, sin Key Vault ni managed identity → los secretos van como *application settings* del recurso de Static Web Apps.
3. **Python 3.11** (`"platform": {"apiRuntime": "python:3.11"}` en `public/staticwebapp.config.json`, que Astro copia a `dist/`; SWA lo lee de la carpeta desplegada, no de `api/`). *Verificado (V2):* `python:3.11` es un valor admitido para funciones administradas (Functions 4.x, Linux, sin fecha de fin de soporte publicada). Se usa el **modelo v2** (`function_app.py`), que Microsoft recomienda para apps nuevas; la documentación de SWA no lo menciona de forma explícita, pero hay apps v2 funcionando en SWA administrada (V2). Por eso toda la lógica vive en `contact/` y `function_app.py` solo registra la ruta: si el primer despliegue (`azure-deploy`) no registra la función, se cambia al modelo v1 (`contact/function.json` + `__init__.py`) sin tocar la lógica.
4. **ACS Email**: cobra por correo y por MB (céntimos con este volumen). Arrancar con el *dominio administrado de Azure* (remitente `DoNotReply@<id>.azurecomm.net`) y migrar a un dominio propio con SPF/DKIM cuando exista el dominio. *Verificado (V3):* aprovisionar el dominio es gratis y ACS configura la autenticación del remitente; el dominio y el usuario del remitente no se pueden personalizar, y el límite es **5 correos/minuto y 10/hora por suscripción, sin ampliación** (solo los dominios propios verificados pueden pedir más). Suficiente para un formulario de contacto; si se supera, ACS responde `429` y la función devuelve `503` (R8). Alternativa descartada por ahora: servicio externo de correo con plan gratuito.
5. **Sin almacenamiento ni rate limit persistente** (evita costo): defensa por Turnstile + honeypot + límites de tamaño. Si aparece abuso, evaluar limitar por IP con un contador en memoria (mejor esfuerzo) antes de añadir recursos de pago.
6. **Reply-To:** incluir el correo del visitante en el cuerpo siempre y, además, como `replyTo`. *Verificado (V4):* el SDK `azure-communication-email` (1.1.0, Python ≥ 3.9) acepta en el mensaje de `begin_send` un campo de primer nivel `"replyTo": [{"address": "...", "displayName": "..."}]`. El correo del visitante ya llega validado y sin saltos de línea (R5).

7. **Cliente HTTP de siteverify con `urllib.request`** (biblioteca estándar) en lugar de `httpx` o `requests`: es una sola petición POST JSON con timeout y así no se suma ninguna dependencia de producción. Detalles:
   - Timeout de 5 s y sin reintentos, así que no hace falta `idempotency_key`.
   - El token vacío o de más de 2048 caracteres se rechaza sin llamar a Cloudflare, y una secret key vacía da `503` sin llamar.
   - Si Cloudflare responde un 4xx con JSON (pasa con una secret inválida), se clasifica por sus `error-codes`.
   - Los logs solo registran el tipo de error o los códigos, nunca el token, la secret ni la IP.

8. **Envío sin esperar la entrega:** `mailer.send` llama a `begin_send` y no espera al poller (`poller.result()`). ACS ya rechaza en esa llamada los errores que importan (credenciales, `429` por el límite del dominio administrado, red), y esperar la entrega añadiría segundos a cada envío. Esos errores, y una cadena de conexión vacía o mal formada, se convierten en `MailError` → `503` (R8). Un fallo de entrega posterior no llega al visitante; se vería en los logs de ACS. Dependencia: `azure-communication-email>=1.1,<2`.

## Frontend (Astro)

- Widget con **renderizado explícito** (*verificado, V5*): `turnstile.reset()` y `turnstile.getResponse()` exigen el `widgetId` que devuelve `turnstile.render()`, así que el renderizado implícito (`class="cf-turnstile"`) no sirve para R9. En el formulario va un contenedor `<div id="turnstile" data-sitekey={import.meta.env.PUBLIC_TURNSTILE_SITE_KEY}>` (sin la clase `cf-turnstile`). `contact.ts` define el callback de carga y después inserta `<script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=onTurnstileLoad">`; ese callback llama a `turnstile.render('#turnstile', { sitekey })` y guarda el `widgetId`.
- Envío: pequeño script (sin librerías) en `src/scripts/contact.ts`, cargado con un `<script>` procesado por Astro, que toma el token con `turnstile.getResponse(widgetId)` (no depende del campo oculto `cf-turnstile-response`), hace `fetch('/api/contact', { method: 'POST', body: JSON.stringify(...) })`, gestiona el estado y llama a `turnstile.reset(widgetId)` si hay error de captcha. El token caduca a los 300 s y es de un solo uso (V5).
- **Compatibilidad con la CSP** (`script-src 'self'` sin `'unsafe-inline'`): Astro inlinea en el HTML los scripts procesados menores que `assetsInlineLimit` (4 KB por defecto; comprobado en `astro/dist/core/build/plugins/plugin-scripts.js`, Astro 7.4). Por eso se fija `vite.build.assetsInlineLimit: 0` para emitirlos siempre como archivo. Nada de `is:inline`, `define:vars` ni atributos `on*`; la site key llega al widget por `data-sitekey`.
- Campo `website`: oculto con CSS (no `display:none` si molesta a lectores; usar posición fuera de pantalla), `tabindex="-1"`, `autocomplete="off"`, `aria-hidden="true"`.
- Mensajes de estado en una región `role="status"` / `aria-live="polite"` (`#contact-status`); su color lo da `data-state="success" | "error"` (turquesa / ámbar de la paleta).
- Comportamiento de `contact.ts`:
  - Widget con `theme: 'dark'` y `language: 'es'`. Si el build no recibió site key, el botón queda deshabilitado con un aviso.
  - Antes de enviar exige un token; si no lo hay, pide completar la verificación sin llamar a la API.
  - El widget se reinicia tras **cualquier respuesta que pudo gastar el token**: éxito, captcha rechazado, `5xx`/`413`/`415` y error de red. No se reinicia tras `400 validation`, porque la validación ocurre antes de verificar el captcha y el token sigue sin usar.
  - Los campos que la API marca como inválidos reciben `aria-invalid="true"`.
- Los campos repiten en HTML los límites de R5 (`maxlength` 100/254/2000, `minlength` 10 en el mensaje) para avisar antes de enviar; la validación que manda sigue siendo la del servidor.
- Sin JS: el formulario muestra un aviso `<noscript>` con el enlace de LinkedIn como alternativa.

## Variables de entorno

| Variable | Dónde | Secreta |
| --- | --- | --- |
| `TURNSTILE_SECRET_KEY` | App settings de SWA / `local.settings.json` | Sí |
| `ACS_CONNECTION_STRING` | App settings de SWA / `local.settings.json` | Sí |
| `MAIL_SENDER` | App settings (remitente verificado en ACS) | No |
| `MAIL_TO` | App settings (buzón destino) | No |
| `PUBLIC_TURNSTILE_SITE_KEY` | Variable de build de Astro (`.env`, GitHub Actions) | No |

Para pruebas locales se usan las **claves de prueba** de Turnstile (*verificado, V6*), que funcionan en cualquier dominio, `localhost` incluido. Cloudflare recomienda que la site key de producción **no** permita dominios locales, así que `localhost` se quitará del widget real cuando exista el dominio (`azure-deploy`).

| Uso | Site key (`PUBLIC_TURNSTILE_SITE_KEY`) | Secret key (`TURNSTILE_SECRET_KEY`) |
| --- | --- | --- |
| Siempre pasa | `1x00000000000000000000AA` | `1x0000000000000000000000000000000AA` |
| Siempre falla | `2x00000000000000000000AB` | `2x0000000000000000000000000000000AA` |
| Token ya usado (`timeout-or-duplicate`) | — | `3x0000000000000000000000000000000AA` |

Son valores públicos de la documentación de Cloudflare, no secretos.

## Verificaciones (T0.2, 27-oct-2026)

Conclusiones contrastadas con la documentación oficial para los puntos que estaban marcados como VERIFICAR:

- **V1 — Turnstile Free:** gratis; 20 widgets, 10 hostnames por widget, desafíos ilimitados. [Planes de Turnstile](https://developers.cloudflare.com/turnstile/plans/)
- **V2 — Python en SWA administrada:** `python:3.11` admitido (Functions 4.x). Solo triggers HTTP; sin managed identity ni referencias a Key Vault; prefijos de app settings reservados (`FUNCTIONS_`, `WEBSITE_`, `AZURE_FUNCTION_`, etc.), que nuestras variables no usan. El modelo v2 es el recomendado por Functions; SWA no lo documenta de forma explícita, pero hay apps v2 en SWA administrada ([issue #1478](https://github.com/Azure/static-web-apps/issues/1478)). [Lenguajes y runtimes de SWA](https://learn.microsoft.com/azure/static-web-apps/languages-runtimes) · [Funciones en SWA](https://learn.microsoft.com/azure/static-web-apps/apis-functions) · [Referencia de Python](https://learn.microsoft.com/azure/azure-functions/functions-reference-python)
- **V3 — Dominio administrado de ACS:** gratis; remitente no personalizable; 5 correos/min y 10/hora por suscripción, sin ampliación; tamaño máximo de la petición 10 MB. [Dominios administrados](https://learn.microsoft.com/azure/communication-services/quickstarts/email/add-azure-managed-domains) · [Límites](https://learn.microsoft.com/azure/communication-services/concepts/service-limits)
- **V4 — SDK de correo:** `azure-communication-email` 1.1.0 (17-oct-2025, Python ≥ 3.9). `EmailClient.from_connection_string(...)`, `begin_send(message)` devuelve un poller; mensaje con `senderAddress`, `recipients.to[]`, `content.{subject, plainText, html}` y `replyTo[]` (`{address, displayName}`). Errores como `azure.core.exceptions.HttpResponseError`. [README del SDK](https://learn.microsoft.com/python/api/overview/azure/communication-email-readme) · [PyPI](https://pypi.org/project/azure-communication-email/)
- **V5 — Widget y siteverify:** script `https://challenges.cloudflare.com/turnstile/v0/api.js` (`?render=explicit` para renderizado explícito); `reset`, `getResponse`, `remove` e `isExpired` reciben el `widgetId`. Token válido 300 s, un solo uso, máximo 2048 caracteres. Siteverify: `POST https://challenges.cloudflare.com/turnstile/v0/siteverify`, acepta JSON o form-urlencoded con `secret`, `response`, `remoteip` (opcional) e `idempotency_key` (opcional); responde `success`, `error-codes`, `hostname`, `challenge_ts`. Códigos: `missing-input-secret`, `invalid-input-secret`, `missing-input-response`, `invalid-input-response`, `bad-request`, `timeout-or-duplicate`, `internal-error`. Mapeo: errores del token → `400 captcha` (R2); errores de secreto, `internal-error`, timeout o fallo de red → `503 unavailable` (R8). [Renderizado en cliente](https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/) · [Validación en servidor](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)
- **V6 — Claves de prueba:** ver la tabla de «Variables de entorno». [Testing](https://developers.cloudflare.com/turnstile/troubleshooting/testing/)

## Desarrollo local

El README es una presentación del sitio; la guía técnica vive aquí y en los comentarios de `.env.example`.

1. **Frontend:** `cp .env.example .env`. Trae la site key de prueba que siempre pasa (`1x00000000000000000000AA`).
2. **API:**
   ```bash
   cd api
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -r requirements-dev.txt
   cp local.settings.sample.json local.settings.json   # ignorado por git
   python -m pytest
   func start                                         # http://localhost:7071/api/contact
   ```
   `local.settings.sample.json` trae la secret de prueba que siempre pasa. Para enviar correos de verdad hay que completar `ACS_CONNECTION_STRING`, `MAIL_SENDER` y `MAIL_TO` en `local.settings.json`; sin ellas la API responde `503`. Requiere Azure Functions Core Tools 4 (`brew tap azure/functions && brew install azure-functions-core-tools@4`).
3. **Juntos:** `npm run dev` no redirige `/api` a la función. Para probar el formulario completo se usa el emulador de Static Web Apps (T3.1).

El aviso «Unable to create client for AzureWebJobsStorage» de `func start` es inofensivo: una función solo HTTP no necesita almacenamiento.

## Riesgos

- Token de Turnstile caduca o se reutiliza → el frontend reinicia el widget tras cada error (R9).
- Cold start de la función → el usuario ve «Enviando…» unos segundos; aceptable.
- Cambios en ACS Email (Microsoft advierte de cambios incompatibles en algunos servicios) → aislar el envío en `mailer.py`.
