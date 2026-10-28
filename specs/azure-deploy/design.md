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
| Static Web Apps | Free (100 GB/mes de ancho de banda, 250 MB por app, 2 dominios personalizados, 3 entornos de staging, SSL gratis, sin SLA) | 0 |
| Función administrada | incluida en el plan | 0 |
| Communication Services + Email Communication Service | pago por uso (≈ 0,00025 USD por correo + 0,00012 USD por MB) | céntimos |
| Dominio `rogerrojas.dev` | Cloudflare Registrar, comprado en oct-2026 (estimado previo: ≈ 8,20 USD el primer año, 12,20 USD de renovación) | ~12 USD/año |
| Application Insights (opcional) | con tope diario | ≈ 0 |

Un solo grupo de recursos (`rg-web-personal`) para poder borrar todo de una vez.

## CI/CD (GitHub Actions)

Decisión: **construir el frontend en el workflow**, no con el builder de Oryx de SWA. *Verificado (V1):* Oryx elige la versión
de Node según el campo `engines` de `package.json` (hoy no existe), y la acción admite `skip_app_build: true` para
desplegar una carpeta ya construida. Construir nosotros fija Node 22 con `actions/setup-node`, permite correr `pytest` antes
de desplegar (D3) y evita depender de qué versiones trae Oryx. La **API sí la construye Oryx** (no se usa `skip_api_build`):
instala `api/requirements.txt` con el runtime de `apiRuntime`. Además se añade `"engines": { "node": ">=22.23" }` a
`package.json` (T1.4) para documentar el requisito. Flujo:

1. `actions/setup-node` (Node 22) → `npm ci` → `npm run build` (con `PUBLIC_TURNSTILE_SITE_KEY` desde variables de GitHub).
2. `actions/setup-python` (3.11) → `pip install -r api/requirements.txt` → `pytest`.
3. Despliegue con la acción oficial **`Azure/static-web-apps-deploy@v1`** (*verificado, V2*) con `action: "upload"`,
   `skip_app_build: true`, `app_location: "dist"` (con `skip_app_build`, es la carpeta ya construida), `output_location: ""`,
   `api_location: "api"`, `azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}` y
   `repo_token: ${{ secrets.GITHUB_TOKEN }}` (comentarios en el PR). `staticwebapp.config.json` debe estar dentro de `dist/`.
4. En pull requests: el job de despliegue crea/actualiza un entorno de staging y un segundo job con `action: "close"` lo
   elimina al cerrar el PR. El plan Free admite **3** entornos de staging.

Disparadores: `push` a `main`, `pull_request` (abrir/sincronizar/cerrar).

Implementación (`.github/workflows/azure-static-web-apps.yml`):
- Acciones `actions/checkout@v7`, `actions/setup-node@v7` (Node 22, caché de npm), `actions/setup-python@v7` (3.11, caché
  de pip) y `Azure/static-web-apps-deploy@v1`. Permisos mínimos: `contents: read` y `pull-requests: write` (comentario
  con la URL de staging).
- Tras el build, un paso **falla si `dist/index.html` no trae `data-sitekey`**: sin la variable `PUBLIC_TURNSTILE_SITE_KEY`
  el formulario quedaría deshabilitado en producción sin que nadie lo notara.
- `pytest` instala `api/requirements-dev.txt`; el paquete desplegado solo lleva `requirements.txt`, porque `.funcignore`
  excluye pruebas y archivos de desarrollo.
- Configuración en GitHub (sin valores en el repo): **variable** `PUBLIC_TURNSTILE_SITE_KEY` y **secreto**
  `AZURE_STATIC_WEB_APPS_API_TOKEN`.
- Al crear el recurso SWA (T2.1) se elige **origen de despliegue «Other»**: con «GitHub», Azure añade al repositorio su
  propio workflow y un secreto con otro nombre, que duplicarían este. El token de despliegue se copia a mano desde
  *Manage deployment token*.

## Configuración fuera del repositorio

El README es una presentación del sitio; esta tabla es la referencia de todo lo que se configura a mano. Ningún valor
secreto vive en el repositorio (D7).

| Nombre | Tipo | Dónde | Secreto | Uso |
| --- | --- | --- | --- | --- |
| `PUBLIC_TURNSTILE_SITE_KEY` | Variable de Actions | GitHub → *Settings → Secrets and variables → Actions → Variables* | No | Site key del widget real; Astro la incrusta en el HTML en el build |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | Secreto de Actions | GitHub → *Settings → Secrets and variables → Actions → Secrets* | Sí | Token de despliegue del recurso SWA (*Manage deployment token*) |
| `TURNSTILE_SECRET_KEY` | Application setting | Azure → recurso SWA → *Settings → Environment variables* | Sí | Verificación del captcha en la función |
| `ACS_CONNECTION_STRING` | Application setting | Azure → recurso SWA → *Settings → Environment variables* | Sí | Envío de correo con ACS |
| `MAIL_SENDER` | Application setting | Azure → recurso SWA → *Settings → Environment variables* | No | Remitente verificado en ACS |
| `MAIL_TO` | Application setting | Azure → recurso SWA → *Settings → Environment variables* | No | Buzón que recibe los mensajes |

`GITHUB_TOKEN` lo crea GitHub en cada ejecución; no hay que configurarlo. En local, los equivalentes son `.env`
(copia de `.env.example`) y `api/local.settings.json` (copia de `api/local.settings.sample.json`), ambos ignorados por git.

## `staticwebapp.config.json` (raíz de la app que se despliega)

- `platform.apiRuntime`: `python:3.11`.
- `responseOverrides.404`: `{ "rewrite": "/404.html" }`. La página (`src/pages/404.astro`) es estática: no puede mostrar la ruta pedida, así que el «comando» de consola es fijo. En el emulador local, las respuestas 404 no llevaban las cabeceras globales; T4.1 comprueba si en Azure sí.
- `globalHeaders`: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
  `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), display-capture=()` (funciones que el
  sitio no usa) y `Content-Security-Policy`.
- Además de la CSP mínima de abajo se añaden `object-src 'none'`, `base-uri 'self'` y `form-action 'self'`: no afectan a
  nada que el sitio use (el formulario envía a `/api/contact`, mismo origen) y cierran vectores habituales.
- **CSP mínima necesaria** (ajustar tras probar): `default-src 'self'`; `script-src 'self' https://challenges.cloudflare.com`
  (sin `'unsafe-inline'`: los scripts se emiten como archivos externos, ver «Frontend» en `specs/contact-form/design.md`);
  `frame-src https://challenges.cloudflare.com`; `connect-src 'self'`;
  `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`; `font-src https://fonts.gstatic.com`; `img-src 'self' data:`;
  `frame-ancestors 'none'`. Nuestro marcado no usa atributos `style=` ni `on*`; `'unsafe-inline'` en `style-src` se mantiene
  porque Shiki colorea los bloques de código del blog con `style=` inline y por las hojas pequeñas que Astro inlinea.
  *Verificado (V5):* Cloudflare solo exige `script-src` y `frame-src` con `https://challenges.cloudflare.com`; `connect-src`
  solo lo necesita el modo *pre-clearance*, que no usamos (el widget hace sus peticiones desde su iframe). Turnstile no
  documenta necesidad de `style-src`. La consola del navegador sin errores de CSP se comprueba en T4.1.
- Descartado `security.csp` de Astro: emite la política en una `<meta>` con hashes, duplicaría la de las cabeceras y una
  `<meta>` no admite `frame-ancestors`.
- Como el archivo debe terminar en `dist/`, colocarlo en `public/staticwebapp.config.json` para que Astro lo copie.

## Dominio y DNS

- Registrado en **Cloudflare** (`rogerrojas.dev`, DNS incluido). Variante canónica: **la raíz** (`https://rogerrojas.dev`, ya
  configurada en `site`); `www` redirige a ella. Usa los 2 dominios personalizados del plan Free. *Verificado (V3):*
  1. **Raíz:** en SWA, *Custom domains → + Add* → `rogerrojas.dev` con validación **TXT** (registro `TXT` en `@` con el código
     que genera el portal). Luego un `CNAME` en `@` hacia `<app>.azurestaticapps.net`: Cloudflare aplica *CNAME flattening*
     en el apex por defecto en todos los planes, Free incluido, que es lo que SWA pide para el apex («ALIAS, ANAME o CNAME
     flattening»; el registro `A` queda descartado porque pierde la distribución global). La propagación del apex puede tardar hasta 72 h.
  2. **`www`:** `CNAME` en `www` hacia `<app>.azurestaticapps.net` y en SWA *Custom domains → + Add* → `www.rogerrojas.dev`
     con validación **CNAME**.
  3. **Redirección:** marcar `rogerrojas.dev` como dominio por defecto (*Custom domains → Set default*): SWA redirige los
     demás dominios a él. La documentación no indica el código de estado; se comprueba con `curl -I` en T4.1.
- Registros hacia SWA en modo **solo DNS** (nube gris, sin proxy de Cloudflare). *Verificado (V4):* SWA exige que el dominio
  resuelva públicamente **a la app** para validar y para renovar el certificado; con el proxy, el DNS devuelve IPs de
  Cloudflare. Si la validación falla aun así, revisar registros `CAA` del dominio (deben permitir a DigiCert).
- `.dev` está en la lista de precarga HSTS de los navegadores: el sitio solo funciona por HTTPS (D4 se cumple de partida).
- Después: agregar el dominio a la lista de dominios permitidos del widget de Turnstile y actualizar `site` (D10).

## Correo (ACS)

1. Crear *Communication Services* y *Email Communication Service* con un dominio **administrado por Azure**; copiar la
   dirección de remitente a `MAIL_SENDER`.
2. Vincular el dominio al recurso de Communication Services y guardar su cadena de conexión como
   `ACS_CONNECTION_STRING` (application setting de SWA, **no** en el repo).
3. Con el dominio propio listo: configurar dominio personalizado en Email Communication Service con SPF y DKIM
   (los pide el portal) y DMARC; cambiar `MAIL_SENDER`. *VERIFICAR* en el portal (se resuelve en T4.2).

## Costos y observabilidad

- Presupuesto mensual de 5 USD con alertas al 50 %, 90 % y 100 % por correo (Cost Management).
- Los logs de la función solo existen con Application Insights; si se activa, limitar con **tope diario de ingesta** y
  muestreo. Alternativa sin costo: ver el flujo de despliegue en GitHub y usar pruebas locales.
- Revisión trimestral: factura de Azure, uso de ancho de banda de SWA (límite Free: 100 GB/mes).

## Riesgos

- El plan Free no tiene SLA: aceptable para un portafolio.
- Límite de 250 MB por entorno: no subir imágenes pesadas ni videos; optimizar imágenes.
- Cambios de Microsoft en ACS Email o en los runtimes de SWA. SWA no publica fecha de fin de soporte para `python:3.11`
  (verificado en `specs/contact-form/design.md`, V2), pero Python 3.11 deja de recibir parches de seguridad en octubre de 2027:
  planificar el cambio de `apiRuntime` antes de esa fecha y revisar la tabla de runtimes al menos una vez al año.

## Verificaciones (T1.1, 27-oct-2026)

- **V1 — Builder y Node:** `skip_app_build: true` despliega una carpeta ya construida (`app_location` = salida, `output_location: ""`, con `staticwebapp.config.json` dentro). Oryx toma la versión de Node de `engines` en `package.json`. [Configuración del build](https://learn.microsoft.com/azure/static-web-apps/build-configuration)
- **V2 — Acción de despliegue:** `Azure/static-web-apps-deploy@v1`; entradas `azure_static_web_apps_api_token`, `repo_token`, `action` (`upload` / `close`), `app_location`, `api_location`, `output_location`, `skip_app_build`, `skip_api_build`, `build_timeout_in_minutes` (15 por defecto). Disparadores de ejemplo: `push` a `main` y `pull_request` con `types: [opened, synchronize, reopened, closed]`. [Configuración del build](https://learn.microsoft.com/azure/static-web-apps/build-configuration)
- **V3 — Dominio:** raíz con TXT + ALIAS/ANAME/CNAME flattening; `www` con CNAME; dominio por defecto con redirección automática; 2 dominios personalizados en Free. [Apex con DNS externo](https://learn.microsoft.com/azure/static-web-apps/apex-domain-external) · [www con DNS externo](https://learn.microsoft.com/azure/static-web-apps/custom-domain-external) · [Dominio por defecto](https://learn.microsoft.com/azure/static-web-apps/custom-domain-default) · [Planes](https://learn.microsoft.com/azure/static-web-apps/plans) · [CNAME flattening de Cloudflare](https://developers.cloudflare.com/dns/cname-flattening/set-up-cname-flattening/)
- **V4 — Proxy de Cloudflare:** la renovación automática del certificado requiere que el dominio resuelva a la app por internet público ([Dominios personalizados](https://learn.microsoft.com/azure/static-web-apps/custom-domain)), así que solo DNS. Casos reportados de fallos con proxy y con registros `CAA` en Microsoft Q&A ([ejemplo](https://learn.microsoft.com/answers/questions/5610201/custom-domain-for-azure-static-web-app-keeps-faili)).
- **V5 — CSP y Turnstile:** `script-src` y `frame-src` con `https://challenges.cloudflare.com`; `connect-src 'self'` solo para *pre-clearance*. [CSP de Turnstile](https://developers.cloudflare.com/turnstile/reference/content-security-policy/)
