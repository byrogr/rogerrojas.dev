"""Builds the contact email and hands it to Azure Communication Services (R1, R6, R8)."""

import html
import logging

from azure.communication.email import EmailClient
from azure.core.exceptions import AzureError

logger = logging.getLogger(__name__)


class MailError(Exception):
    """The email could not be handed to ACS. The endpoint answers 503."""


def build_message(*, nombre: str, email: str, mensaje: str, sender: str, to: str) -> dict:
    """Expects fields already validated (R5): nombre and email carry no line breaks."""
    plain_text = f"Nombre: {nombre}\nCorreo: {email}\n\nMensaje:\n{mensaje}\n"

    safe_mensaje = html.escape(mensaje).replace("\n", "<br>")
    html_body = (
        "<html><body>"
        f"<p><strong>Nombre:</strong> {html.escape(nombre)}</p>"
        f"<p><strong>Correo:</strong> {html.escape(email)}</p>"
        f"<p><strong>Mensaje:</strong></p><p>{safe_mensaje}</p>"
        "</body></html>"
    )

    return {
        "senderAddress": sender,
        "recipients": {"to": [{"address": to}]},
        "replyTo": [{"address": email, "displayName": nombre}],
        "content": {
            "subject": f"Nuevo mensaje de contacto de {nombre}",
            "plainText": plain_text,
            "html": html_body,
        },
    }


def send(message: dict, connection_string: str) -> None:
    """Submit the message to ACS. Does not wait for delivery: acceptance is enough (see design.md)."""
    if not connection_string:
        logger.error("ACS connection string is not configured")
        raise MailError("missing connection string")

    try:
        client = EmailClient.from_connection_string(connection_string)
        client.begin_send(message)
    except (AzureError, ValueError) as exc:  # ValueError: malformed connection string
        # Only the error type and status: never the message, the visitor's data or the connection string.
        logger.error("ACS email send failed: %s (status %s)", type(exc).__name__, getattr(exc, "status_code", None))
        raise MailError(type(exc).__name__) from exc
