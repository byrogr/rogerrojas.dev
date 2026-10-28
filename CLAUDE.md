# CLAUDE.md — Web personal de Roger Rojas

Sitio estático en **Astro** (español) con blog en Markdown, desplegado en **Azure Static Web Apps (plan Free)**.
La API del formulario de contacto es una **Azure Function administrada en Python**, con captcha **Cloudflare Turnstile**
y envío de correo con **Azure Communication Services Email**.

## Cómo trabajamos: Spec-Driven Development (SDD)

1. **La especificación manda.** Antes de escribir código, lee `specs/README.md` y la carpeta de la feature (`requirements.md`, `design.md`, `tasks.md`).
2. **Una tarea a la vez.** Toma la primera tarea sin marcar de `tasks.md`, impleméntala y márcala `[x]` solo cuando cumpla sus criterios de aceptación.
3. **Si el código y la spec discrepan, para y pregunta.** No inventes comportamiento: propón el cambio en la spec primero y espera confirmación.
4. **Cambios de alcance = cambios de spec.** Actualiza `requirements.md` / `design.md` en el mismo commit que el código.
5. Atajo: el comando `/implement-task` (en `.claude/commands/`) ejecuta este ciclo.

## Comandos

```bash
npm install
npm run dev        # http://localhost:4321
npm run build      # debe pasar siempre antes de dar una tarea por terminada
cd api && python -m pytest   # cuando exista la carpeta api/
```

Requiere Node 22.23.4+ y Python 3.11 (el runtime administrado de Static Web Apps).

## Estructura

```
src/content/blog/    artículos .md (schema en src/content.config.ts)
src/layouts/Base.astro
src/pages/           index, blog/, rss.xml.js
src/styles/global.css  tokens de la paleta (no hardcodear colores fuera de aquí)
src/utils/           helpers compartidos (formato de fechas en UTC, tiempo de lectura)
api/                 Azure Function en Python (la crea la spec contact-form)
specs/               especificaciones SDD
```

## Convenciones

- **Idioma:** todo el texto visible y el contenido del blog en español (es-PE). Código, commits y nombres de archivo en inglés.
- **Paleta:** ámbar `#F5A524` (Java), turquesa `#4FD1C5` (Python), lavanda `#A99CFF` (.NET), cian `#67E8F9`, fondo `#060A0F`. Usa las variables CSS de `global.css`.
- **Sin JavaScript de más:** el sitio es estático; solo se permite JS donde la spec lo pida (widget del captcha y envío del formulario) y para cerrar el menú móvil tras elegir un enlace (`src/scripts/menu.ts`; el menú en sí es un `<details>` que funciona sin JS).
- **Dependencias:** no añadas ninguna sin justificarla en la spec. Mantén el costo de Azure en ~0 (ver `specs/azure-deploy/`).
- **Accesibilidad:** HTML semántico, `label` en cada campo, contraste AA, foco visible.

## Seguridad (innegociable)

- **Nunca** commitear secretos: claves de Turnstile, cadena de conexión de ACS, tokens. Van en la configuración de la app de Azure y en `api/local.settings.json` (ignorado por git).
- Solo la *site key* de Turnstile es pública (`PUBLIC_TURNSTILE_SITE_KEY`).
- No registrar en logs el contenido de los mensajes ni datos personales innecesarios.
- Este repositorio vive en la **cuenta personal de GitHub** (no en la de trabajo).

## Definición de terminado (DoD)

- [ ] Cumple los criterios de aceptación de la tarea y los requisitos que referencia.
- [ ] `npm run build` pasa; `pytest` pasa si se tocó `api/`.
- [ ] La spec y `tasks.md` reflejan lo que se hizo.
- [ ] Sin secretos ni TODOs sin dueño en el diff.
