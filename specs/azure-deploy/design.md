# Despliegue en Azure — Diseño

## Recursos

```
Cloudflare Registrar (dominio .dev) ── DNS ──┐
                                             ▼
GitHub (repo personal) ──Actions──► Azure Static Web Apps (Free)
                                      ├─ sitio estático (dist/)
                                      └─ /api  (función administrada, Python 3.11)
                                              ├─► Cloudflare Turnstile (siteverify)
                                              └─► Azure Communication Services Email
Azure Cost Management ── alerta de presupuesto (5 USD/mes)
```

| Recurso | Plan | Costo esperado |
| --- | --- | --- |
| Static Web Apps | Free (100 GB/mes de ancho de banda, 250 MB por entorno, 2 dominios personalizados, SSL gratis) | 0 |
| Función administrada | incluida en el plan | 0 |
| Communication Services + Email Communication Service | pago por uso (≈ 0,00025 USD por correo + 0,00012 USD por MB) | céntimos |
| Dominio `.dev` | Cloudflare Registrar (≈ 8,20 USD el primer año, 12,20 USD de renovación; **VERIFICAR** al comprar) | ~12 USD/año |
| Application Insights (opcional) | con tope diario | ≈ 0 |

Un solo grupo de recursos (`rg-web-personal`) para poder borrar todo de una vez.

## CI/CD (GitHub Actions)

Decisión: **construir en el workflow**, no con el builder de Oryx de SWA, porque Astro requiere Node 22.23+ y el
builder podría traer una versión anterior (*VERIFICAR*). Flujo:

1. `actions/setup-node` (Node 22) → `npm ci` → `npm run build` (con `PUBLIC_TURNSTILE_SITE_KEY` desde variables de GitHub).
2. `actions/setup-python` (3.11) → `pip install -r api/requirements.txt` → `pytest`.
3. Despliegue con la acción oficial `Azure/static-web-apps-deploy` con `skip_app_build: true`,
   `app_location: "/dist"`, `api_location: "api"` y el token `AZURE_STATIC_WEB_APPS_API_TOKEN` (secreto de GitHub generado al
   vincular el recurso). *VERIFICAR* nombre de la acción, versión y parámetros en su documentación.
4. En pull requests: crea/actualiza un entorno de staging y lo elimina al cerrar el PR (comportamiento de la acción).

Disparadores: `push` a `main`, `pull_request` (abrir/sincronizar/cerrar).

## `staticwebapp.config.json` (raíz de la app que se despliega)

- `platform.apiRuntime`: `python:3.11`.
- `responseOverrides.404`: `{ "rewrite": "/404.html" }`.
- `globalHeaders`: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
  `Permissions-Policy` restrictiva y `Content-Security-Policy`.
- **CSP mínima necesaria** (ajustar tras probar): `default-src 'self'`; `script-src 'self' https://challenges.cloudflare.com`
  (sin `'unsafe-inline'`: los scripts se emiten como archivos externos, ver «Frontend» en `specs/contact-form/design.md`);
  `frame-src https://challenges.cloudflare.com`; `connect-src 'self' https://challenges.cloudflare.com`;
  `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`; `font-src https://fonts.gstatic.com`; `img-src 'self' data:`;
  `frame-ancestors 'none'`. Nuestro marcado no usa atributos `style=` ni `on*`; `'unsafe-inline'` en `style-src` se mantiene
  porque Shiki colorea los bloques de código del blog con `style=` inline, por las hojas pequeñas que Astro inlinea y por el
  widget (*VERIFICAR* si Turnstile lo necesita).
- Descartado `security.csp` de Astro: emite la política en una `<meta>` con hashes, duplicaría la de las cabeceras y una
  `<meta>` no admite `frame-ancestors`.
- Como el archivo debe terminar en `dist/`, colocarlo en `public/staticwebapp.config.json` para que Astro lo copie.

## Dominio y DNS

- Registrar en **Cloudflare** (DNS incluido). Añadir el dominio personalizado en el recurso de SWA y crear los registros
  que pida la validación (*VERIFICAR* TXT/CNAME y el caso del dominio raíz con *CNAME flattening*).
- Mantener los registros hacia SWA en modo **solo DNS** (sin proxy de Cloudflare) para que SWA emita su certificado
  (*VERIFICAR*).
- Elegir una variante canónica (raíz **o** `www`) y redirigir la otra.
- Después: agregar el dominio a la lista de dominios permitidos del widget de Turnstile y actualizar `site` (D10).

## Correo (ACS)

1. Crear *Communication Services* y *Email Communication Service* con un dominio **administrado por Azure**; copiar la
   dirección de remitente a `MAIL_SENDER`.
2. Vincular el dominio al recurso de Communication Services y guardar su cadena de conexión como
   `ACS_CONNECTION_STRING` (application setting de SWA, **no** en el repo).
3. Con el dominio propio listo: configurar dominio personalizado en Email Communication Service con SPF y DKIM
   (los pide el portal) y DMARC; cambiar `MAIL_SENDER`. *VERIFICAR* en el portal.

## Costos y observabilidad

- Presupuesto mensual de 5 USD con alertas al 50 %, 90 % y 100 % por correo (Cost Management).
- Los logs de la función solo existen con Application Insights; si se activa, limitar con **tope diario de ingesta** y
  muestreo. Alternativa sin costo: ver el flujo de despliegue en GitHub y usar pruebas locales.
- Revisión trimestral: factura de Azure, uso de ancho de banda de SWA (límite Free: 100 GB/mes).

## Riesgos

- El plan Free no tiene SLA: aceptable para un portafolio.
- Límite de 250 MB por entorno: no subir imágenes pesadas ni videos; optimizar imágenes.
- Cambios de Microsoft en ACS Email o en los runtimes de SWA (Python 3.11 tiene fecha de fin de soporte; revisar al menos una vez al año).
