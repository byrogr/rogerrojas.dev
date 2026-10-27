# Despliegue en Azure — Requisitos

## Contexto

Publicar la web (Astro estático + API en Python) en Azure con **costo cercano a cero**, dominio propio, HTTPS y
despliegue automático desde GitHub. Depende de `specs/contact-form/` para la API.

## Requisitos (EARS)

**D1 — Hosting.** El sistema deberá servirse desde **Azure Static Web Apps, plan Free**, con la API como función
administrada en `/api`.

**D2 — Despliegue continuo.** Cuando se haga push a `main`, el sistema deberá construirse y desplegarse
automáticamente con GitHub Actions; cuando se abra un pull request, deberá crearse un entorno de prueba (staging) temporal.

**D3 — Build reproducible.** El build deberá usar la versión de Node requerida por el proyecto (22.23+) y Python 3.11 para
la API, y fallar si `npm run build` o `pytest` fallan.

**D4 — Dominio y HTTPS.** El sitio deberá responder en el dominio propio con certificado gratuito renovado
automáticamente; el acceso por HTTP deberá redirigir a HTTPS, y una variante (`www` o raíz) deberá redirigir a la otra.

**D5 — Cabeceras de seguridad.** El sitio deberá enviar cabeceras de seguridad (CSP, `X-Content-Type-Options`,
`Referrer-Policy`, `Permissions-Policy`) configuradas en `staticwebapp.config.json`, sin romper el widget de Turnstile
ni las fuentes de Google.

**D6 — Página 404.** Una ruta inexistente deberá mostrar una página 404 con la paleta del sitio y enlace de regreso.

**D7 — Secretos.** Los secretos deberán estar solo en la configuración de la aplicación (Static Web Apps) y en secretos/variables
de GitHub; nunca en el repositorio. El repositorio deberá estar en la **cuenta personal de GitHub**.

**D8 — Correo saliente.** El recurso de Azure Communication Services Email deberá tener un remitente verificado.
Inicialmente se usará el dominio administrado de Azure; cuando el dominio propio esté activo, se migrará a él con
SPF, DKIM y DMARC.

**D9 — Control de costos.** Deberá existir una alerta de presupuesto (umbral inicial: 5 USD/mes) con aviso por correo,
y no deberá crearse ningún recurso con costo fijo mensual sin actualizar esta spec. Si se activa Application Insights,
deberá tener un tope diario de ingesta.

**D10 — Metadatos de producción.** `site` en `astro.config.mjs` deberá apuntar al dominio real para que el sitemap, el
RSS y las URLs canónicas sean correctos.

## Criterios de aceptación globales

- [ ] `https://<dominio>` carga con candado válido y `www`/raíz redirigen entre sí.
- [ ] Un push a `main` publica en menos de ~10 minutos sin pasos manuales.
- [ ] Enviar el formulario en producción entrega un correo.
- [ ] Existe la alerta de presupuesto y el costo mensual proyectado es ≈ 0 (aparte del dominio, ~12 USD/año).
- [ ] Las cabeceras de seguridad aparecen en la respuesta y la consola del navegador no muestra errores de CSP.
