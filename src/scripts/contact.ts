// Contact form: renders Turnstile explicitly (reset needs the widget id) and posts JSON to /api/contact (R9).

interface Turnstile {
  render(container: string | HTMLElement, options: Record<string, unknown>): string;
  reset(widgetId: string): void;
  getResponse(widgetId: string): string | undefined;
}

declare global {
  interface Window {
    turnstile?: Turnstile;
    onTurnstileLoad?: () => void;
  }
}

type ApiResponse = {
  ok?: boolean;
  code?: string;
  message?: string;
  fields?: Record<string, string>;
};

const TURNSTILE_SRC = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=onTurnstileLoad';
const GENERIC_ERROR = 'No pudimos enviar tu mensaje. Inténtalo más tarde.';

const form = document.querySelector<HTMLFormElement>('#contact-form');
const container = document.querySelector<HTMLElement>('#turnstile');
const status = document.querySelector<HTMLElement>('#contact-status');
const button = form?.querySelector<HTMLButtonElement>('button[type="submit"]');

let widgetId: string | undefined;

function setStatus(text: string, state?: 'success' | 'error') {
  if (!status) return;
  status.textContent = text;
  if (state) status.dataset.state = state;
  else delete status.dataset.state;
}

function resetCaptcha() {
  if (window.turnstile && widgetId) window.turnstile.reset(widgetId);
}

function markInvalid(fields: Record<string, string> = {}) {
  form?.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>('input, textarea').forEach((field) => {
    if (field.name in fields) field.setAttribute('aria-invalid', 'true');
    else field.removeAttribute('aria-invalid');
  });
}

function loadTurnstile(siteKey: string) {
  window.onTurnstileLoad = () => {
    widgetId = window.turnstile?.render('#turnstile', { sitekey: siteKey, theme: 'dark', language: 'es' });
  };
  const script = document.createElement('script');
  script.src = TURNSTILE_SRC;
  script.async = true;
  script.onerror = () => setStatus('No se pudo cargar la verificación. Recarga la página para intentarlo de nuevo.', 'error');
  document.head.append(script);
}

async function submit(event: SubmitEvent) {
  event.preventDefault();
  if (!form || !button) return;

  const token = widgetId ? window.turnstile?.getResponse(widgetId) : undefined;
  if (!token) {
    setStatus('Completa la verificación antes de enviar.', 'error');
    return;
  }

  const data = new FormData(form);
  const payload = {
    nombre: String(data.get('nombre') ?? ''),
    email: String(data.get('email') ?? ''),
    mensaje: String(data.get('mensaje') ?? ''),
    website: String(data.get('website') ?? ''),
    token,
  };

  button.disabled = true;
  form.setAttribute('aria-busy', 'true');
  setStatus('Enviando…');

  try {
    const response = await fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const body: ApiResponse = await response.json().catch(() => ({}));

    if (response.ok && body.ok) {
      form.reset();
      markInvalid();
      resetCaptcha(); // the token is single-use
      setStatus('¡Gracias! Tu mensaje fue enviado. Te responderé pronto.', 'success');
    } else if (body.code === 'validation' && body.fields) {
      // Validation runs before the captcha check, so the token is still unused.
      markInvalid(body.fields);
      setStatus(`Revisa el formulario: ${Object.values(body.fields).join(' ')}`, 'error');
    } else {
      resetCaptcha();
      setStatus(body.message ?? GENERIC_ERROR, 'error');
    }
  } catch {
    resetCaptcha();
    setStatus(GENERIC_ERROR, 'error');
  } finally {
    button.disabled = false;
    form.removeAttribute('aria-busy');
  }
}

if (form && container && button) {
  const siteKey = container.dataset.sitekey;
  if (siteKey) {
    loadTurnstile(siteKey);
    form.addEventListener('submit', submit);
  } else {
    button.disabled = true;
    setStatus('El formulario no está disponible en este momento. Escríbeme por LinkedIn.', 'error');
  }
}

export {};
