# Despliegue en Azure — Tareas

Las tareas **(manual)** las haces tú en un portal o registrador; Claude Code te da los pasos exactos y espera tu confirmación.
Depende de `specs/contact-form/` (al menos hasta T1.5 para desplegar la API).

## Fase 0 — Cuentas y repositorio

- [x] **T0.1 (manual)** Crear el repositorio en tu **cuenta personal de GitHub**, subir el proyecto y proteger `main`
  (PR obligatorio opcional). Usar la llave SSH personal. *Cubre: D7.*
- [x] **T0.2 (manual)** Comprar el dominio `.dev` en Cloudflare Registrar (comparar el precio del momento con Porkbun/Dynadot). *Cubre: D4.*
- [x] **T0.3 (manual)** Crear la **alerta de presupuesto** (5 USD/mes) en Azure Cost Management antes de crear recursos de pago. *Cubre: D9.*

## Fase 1 — Configuración en el repositorio

- [x] **T1.1** Resolver los **VERIFICAR** de `design.md` (builder y versión de Node, acción de despliegue y parámetros,
  validación de dominio en SWA, proxy de Cloudflare) y anotar conclusiones. *Cubre: D2, D3, D4.*
- [x] **T1.2** Completar `public/staticwebapp.config.json` (lo crea `contact-form` T1.1 con `apiRuntime`) con la 404 y las cabeceras (CSP según `design.md`). *Cubre: D5, D6.*
  *Aceptación:* tras `npm run build`, el archivo está en `dist/`.
- [x] **T1.3** Crear `src/pages/404.astro` con el layout y la paleta del sitio. *Cubre: D6.*
- [x] **T1.4** Crear `.github/workflows/azure-static-web-apps.yml` según `design.md` (build Node 22, pruebas Python, despliegue,
  staging en PR). Sin secretos en el archivo. *Cubre: D2, D3, D7.*
- [x] **T1.5** Documentar la variable de GitHub (`PUBLIC_TURNSTILE_SITE_KEY`), el secreto de GitHub y los application settings
  de SWA en `design.md` («Configuración fuera del repositorio») y en los comentarios de `.env.example` (creado por
  `contact-form` T2.3). El README queda como presentación del sitio. *Cubre: D7.*

## Fase 2 — Recursos de Azure

- [x] **T2.1 (manual)** Crear el grupo de recursos y el recurso **Static Web Apps (Free)** vinculado al repositorio;
  guardar el token en los secretos de GitHub. *Cubre: D1, D2.*
- [x] **T2.2 (manual)** Crear **Communication Services** + **Email Communication Service** con dominio administrado por Azure;
  copiar remitente y cadena de conexión. *Cubre: D8.*
- [x] **T2.3 (manual)** Cargar en *Application settings* de SWA: `TURNSTILE_SECRET_KEY`, `ACS_CONNECTION_STRING`,
  `MAIL_SENDER`, `MAIL_TO`. *Cubre: D7, D8.*
- [ ] **T2.4 (manual, opcional)** Activar Application Insights con tope diario de ingesta. *Cubre: D9.*

## Fase 3 — Primera publicación

- [ ] **T3.1** Push a `main` y comprobar el workflow; abrir la URL por defecto de SWA y probar el formulario. *Cubre: D1, D2.*
- [ ] **T3.2 (manual)** Añadir el dominio personalizado en SWA, crear los registros DNS en Cloudflare (solo DNS), esperar el
  certificado y fijar la variante canónica con su redirección. *Cubre: D4.*
- [ ] **T3.3 (manual)** Añadir el dominio a los dominios permitidos del widget de Turnstile. *Cubre: D4.*
- [ ] **T3.4** Cambiar `site` en `astro.config.mjs` al dominio real y volver a desplegar. *Cubre: D10.*

## Fase 4 — Verificación y cierre

- [ ] **T4.1** Revisar cabeceras (herramienta como `curl -I` o el inspector del navegador), consola sin errores de CSP, RSS y sitemap con el dominio correcto. *Cubre: D5, D10.*
- [ ] **T4.2 (manual)** Correo propio: verificar el dominio de envío (SPF/DKIM/DMARC) y cambiar `MAIL_SENDER`. *Cubre: D8.*
- [ ] **T4.3 (manual)** Confirmar que la alerta de presupuesto llega y anotar el costo proyectado. *Cubre: D9.*
- [ ] **T4.4** Marcar todos los criterios de aceptación de `requirements.md`.
