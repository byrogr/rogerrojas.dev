import pytest
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError, ServiceRequestError

from contact import mailer
from contact.mailer import MailError, build_message, send

SENDER = "DoNotReply@abc123.azurecomm.net"
TO = "roger@ejemplo.com"
CONN = "endpoint=https://acs-test.communication.azure.com/;accesskey=ZmFrZQ=="


def message(**overrides):
    fields = {"nombre": "Ana Pérez", "email": "ana@ejemplo.com", "mensaje": "Hola Roger,\nme gustaría conversar."}
    fields.update(overrides)
    return build_message(**fields, sender=SENDER, to=TO)


# --- armado del mensaje (R1, R6) ---

def test_addresses_and_reply_to():
    msg = message()

    assert msg["senderAddress"] == SENDER
    assert msg["recipients"] == {"to": [{"address": TO}]}
    assert msg["replyTo"] == [{"address": "ana@ejemplo.com", "displayName": "Ana Pérez"}]


def test_subject_names_the_visitor():
    assert message()["content"]["subject"] == "Nuevo mensaje de contacto de Ana Pérez"


def test_plain_text_contains_every_field():
    text = message()["content"]["plainText"]

    assert "Ana Pérez" in text
    assert "ana@ejemplo.com" in text
    assert "Hola Roger,\nme gustaría conversar." in text


def test_html_contains_every_field_and_keeps_line_breaks():
    html = message()["content"]["html"]

    assert "Ana Pérez" in html
    assert "ana@ejemplo.com" in html
    assert "Hola Roger,<br>me gustaría conversar." in html


def test_html_escapes_visitor_content():
    html = message(
        nombre='<img src=x onerror="alert(1)">',
        email="ana@ejemplo.com",
        mensaje="<script>alert('xss')</script> & más",
    )["content"]["html"]

    assert "<script>" not in html
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt; &amp; más" in html
    assert "<img" not in html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html


def test_plain_text_is_not_html_escaped():
    text = message(mensaje="Precio < 100 & envío gratis")["content"]["plainText"]

    assert "Precio < 100 & envío gratis" in text


# --- envío (R1, R8) ---

class FakeClient:
    def __init__(self, error=None):
        self.error = error
        self.sent = []

    def begin_send(self, msg):
        if self.error:
            raise self.error
        self.sent.append(msg)
        return object()  # poller; the function does not wait for it


@pytest.fixture
def fake_client(monkeypatch):
    holder = {"client": FakeClient(), "conn": None}

    def from_connection_string(conn_str):
        holder["conn"] = conn_str
        return holder["client"]

    monkeypatch.setattr(mailer.EmailClient, "from_connection_string", staticmethod(from_connection_string))
    return holder


def test_send_uses_connection_string_and_sends_message(fake_client):
    msg = message()

    send(msg, CONN)

    assert fake_client["conn"] == CONN
    assert fake_client["client"].sent == [msg]


@pytest.mark.parametrize(
    "error",
    [
        HttpResponseError(message="429 Too Many Requests"),
        ClientAuthenticationError(message="bad key"),
        ServiceRequestError(message="connection refused"),
    ],
)
def test_send_wraps_azure_errors(fake_client, error):
    fake_client["client"] = FakeClient(error)

    with pytest.raises(MailError):
        send(message(), CONN)


def test_send_without_connection_string_fails_without_client(fake_client):
    with pytest.raises(MailError):
        send(message(), "")

    assert fake_client["conn"] is None


def test_malformed_connection_string_raises_mail_error(monkeypatch):
    def broken(conn_str):
        raise ValueError("Invalid connection string")

    monkeypatch.setattr(mailer.EmailClient, "from_connection_string", staticmethod(broken))

    with pytest.raises(MailError):
        send(message(), "not-a-connection-string")


def test_failure_logs_do_not_contain_visitor_data(fake_client, caplog):
    fake_client["client"] = FakeClient(HttpResponseError(message="boom"))

    with pytest.raises(MailError):
        send(message(), CONN)

    assert caplog.records, "a technical error should be logged"
    for text in ("Ana Pérez", "ana@ejemplo.com", "me gustaría conversar", "accesskey"):
        assert text not in caplog.text
