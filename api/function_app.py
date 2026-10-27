import ipaddress
import json
import logging

import azure.functions as func

from contact.config import load_settings
from contact.mailer import MailError, build_message, send
from contact.turnstile import Outcome, verify
from contact.validation import validate

MAX_BODY_BYTES = 10 * 1024

CAPTCHA_MESSAGE = "No pudimos verificar que eres humano. Inténtalo de nuevo."
SEND_MESSAGE = "No pudimos enviar tu mensaje. Inténtalo más tarde."

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
logger = logging.getLogger(__name__)


def json_response(status_code: int, body: dict, headers: dict | None = None) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False),
        status_code=status_code,
        mimetype="application/json",
        charset="utf-8",
        headers=headers,
    )


def bad_request(status_code: int, headers: dict | None = None) -> func.HttpResponse:
    return json_response(status_code, {"ok": False, "code": "bad_request"}, headers)


def unavailable() -> func.HttpResponse:
    return json_response(503, {"ok": False, "code": "unavailable", "message": SEND_MESSAGE})


def client_ip(req: func.HttpRequest) -> str | None:
    """First address in X-Forwarded-For, without port; None if it is not a valid IP."""
    first = (req.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if first.startswith("["):  # [IPv6]:port
        first = first[1:].split("]")[0]
    elif first.count(":") == 1:  # IPv4:port
        first = first.split(":")[0]
    try:
        return str(ipaddress.ip_address(first))
    except ValueError:
        return None


# The route accepts every method so non-POST requests get a 405 instead of the host's 404 (R7).
@app.route(route="contact")
def contact(req: func.HttpRequest) -> func.HttpResponse:
    try:
        return handle(req)
    except Exception as exc:  # never expose internals
        logger.error("Unexpected error in contact function: %s", type(exc).__name__)
        return json_response(500, {"ok": False, "code": "internal", "message": SEND_MESSAGE})


def handle(req: func.HttpRequest) -> func.HttpResponse:
    # method, content type and size.
    if req.method != "POST":
        return bad_request(405, {"Allow": "POST"})
    content_type = (req.headers.get("content-type") or "").split(";")[0].strip().lower()
    if content_type != "application/json":
        return bad_request(415)
    raw = req.get_body()
    if len(raw) > MAX_BODY_BYTES:
        return bad_request(413)
    try:
        data = json.loads(raw.decode("utf-8"))
    except ValueError:  # includes JSONDecodeError and UnicodeDecodeError
        return bad_request(400)
    if not isinstance(data, dict):
        return bad_request(400)

    # a filled honeypot looks like a success, without captcha or email.
    if data.get("website") not in (None, ""):
        logger.info("Contact honeypot triggered")
        return json_response(200, {"ok": True})

    fields = validate(data)
    if fields.errors:
        return json_response(400, {"ok": False, "code": "validation", "fields": fields.errors})

    # Check configuration before spending the visitor's captcha token.
    settings = load_settings()
    missing = settings.missing()
    if missing:
        logger.error("Contact function misconfigured, missing settings: %s", ", ".join(missing))
        return unavailable()

    captcha = verify(data.get("token"), settings.turnstile_secret_key, client_ip(req))
    if captcha.outcome is Outcome.REJECTED:
        logger.info("Contact captcha rejected: %s", ",".join(captcha.error_codes) or "no codes")
        return json_response(400, {"ok": False, "code": "captcha", "message": CAPTCHA_MESSAGE})
    if captcha.outcome is Outcome.UNAVAILABLE:
        return unavailable()

    message = build_message(
        nombre=fields.nombre,
        email=fields.email,
        mensaje=fields.mensaje,
        sender=settings.mail_sender,
        to=settings.mail_to,
    )
    try:
        send(message, settings.acs_connection_string)
    except MailError:
        return unavailable()  # mailer already logged the technical cause

    logger.info("Contact message sent")
    return json_response(200, {"ok": True})
