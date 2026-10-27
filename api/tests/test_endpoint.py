import json

import azure.functions as func
import pytest

import function_app
from contact.mailer import MailError
from contact.turnstile import Outcome, VerifyResult

handler = function_app.contact.build().get_user_function()

VALID = {
    "nombre": "Ana Pérez",
    "email": "ana@ejemplo.com",
    "mensaje": "Hola Roger, me gustaría conversar.",
    "token": "token-ok",
    "website": "",
}
SETTINGS = {
    "TURNSTILE_SECRET_KEY": "1x0000000000000000000000000000000AA",
    "ACS_CONNECTION_STRING": "endpoint=https://acs-test.communication.azure.com/;accesskey=ZmFrZQ==",
    "MAIL_SENDER": "DoNotReply@abc123.azurecomm.net",
    "MAIL_TO": "roger@ejemplo.com",
}
CAPTCHA_MESSAGE = "No pudimos verificar que eres humano. Inténtalo de nuevo."
SEND_MESSAGE = "No pudimos enviar tu mensaje. Inténtalo más tarde."


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    for name, value in SETTINGS.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def turnstile(monkeypatch):
    state = {"result": VerifyResult(Outcome.OK), "calls": []}

    def fake_verify(token, secret, remote_ip):
        state["calls"].append({"token": token, "secret": secret, "remote_ip": remote_ip})
        return state["result"]

    monkeypatch.setattr(function_app, "verify", fake_verify)
    return state


@pytest.fixture
def mail(monkeypatch):
    state = {"error": None, "sent": []}

    def fake_send(message, connection_string):
        if state["error"]:
            raise state["error"]
        state["sent"].append({"message": message, "connection_string": connection_string})

    monkeypatch.setattr(function_app, "send", fake_send)
    return state


def request(body=None, *, method="POST", content_type="application/json", raw=None, headers=None):
    all_headers = {"Content-Type": content_type} if content_type else {}
    all_headers.update(headers or {})
    data = raw if raw is not None else json.dumps(VALID if body is None else body).encode()
    return func.HttpRequest(method=method, url="/api/contact", headers=all_headers, body=data)


def call(req):
    resp = handler(req)
    return resp.status_code, json.loads(resp.get_body())


# --- R7: método, tipo y tamaño ---

@pytest.mark.parametrize("method", ["GET", "PUT", "PATCH", "DELETE"])
def test_non_post_returns_405(method, turnstile, mail):
    resp = handler(request(method=method))

    assert resp.status_code == 405
    assert resp.headers["Allow"] == "POST"
    assert json.loads(resp.get_body()) == {"ok": False, "code": "bad_request"}
    assert turnstile["calls"] == [] and mail["sent"] == []


@pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data", None])
def test_non_json_returns_415(content_type, turnstile, mail):
    assert call(request(content_type=content_type)) == (415, {"ok": False, "code": "bad_request"})
    assert turnstile["calls"] == [] and mail["sent"] == []


def test_json_with_charset_is_accepted(turnstile, mail):
    assert call(request(content_type="application/json; charset=utf-8"))[0] == 200


def test_body_over_10kb_returns_413(turnstile, mail):
    big = {**VALID, "mensaje": "a" * 10_240}

    assert call(request(big)) == (413, {"ok": False, "code": "bad_request"})
    assert turnstile["calls"] == [] and mail["sent"] == []


def test_body_of_exactly_10kb_is_not_rejected_for_size(turnstile, mail):
    raw = json.dumps(VALID).encode()
    raw = raw[:-1] + b" " * (10_240 - len(raw)) + b"}"
    assert len(raw) == 10_240

    assert call(request(raw=raw))[0] == 200


@pytest.mark.parametrize("raw", [b"not json", b"[1, 2]", b'"texto"', b"", "{\"nombre\": \"\xff\"}".encode("latin-1")])
def test_malformed_json_returns_400_bad_request(raw, turnstile, mail):
    assert call(request(raw=raw)) == (400, {"ok": False, "code": "bad_request"})
    assert turnstile["calls"] == [] and mail["sent"] == []


# --- R4: honeypot ---

@pytest.mark.parametrize("website", ["https://spam.example", "x", 1])
def test_honeypot_fakes_success_without_captcha_or_mail(website, turnstile, mail):
    body = {**VALID, "website": website, "token": "", "email": "no-es-correo"}

    assert call(request(body)) == (200, {"ok": True})
    assert turnstile["calls"] == [] and mail["sent"] == []


@pytest.mark.parametrize("website", ["", None])
def test_empty_honeypot_continues(website, turnstile, mail):
    body = {**VALID, "website": website}

    assert call(request(body)) == (200, {"ok": True})
    assert len(mail["sent"]) == 1


# --- R5: validación ---

def test_invalid_fields_return_400_with_messages_and_skip_captcha(turnstile, mail):
    body = {**VALID, "nombre": "", "email": "no-es-correo"}

    assert call(request(body)) == (
        400,
        {"ok": False, "code": "validation", "fields": {"nombre": "Ingresa tu nombre.", "email": "Correo no válido."}},
    )
    assert turnstile["calls"] == [] and mail["sent"] == []


# --- R2/R3: captcha ---

def test_captcha_rejected_returns_400(turnstile, mail):
    turnstile["result"] = VerifyResult(Outcome.REJECTED, ["timeout-or-duplicate"])

    assert call(request()) == (400, {"ok": False, "code": "captcha", "message": CAPTCHA_MESSAGE})
    assert mail["sent"] == []


def test_captcha_unavailable_returns_503(turnstile, mail):
    turnstile["result"] = VerifyResult(Outcome.UNAVAILABLE)

    assert call(request()) == (503, {"ok": False, "code": "unavailable", "message": SEND_MESSAGE})
    assert mail["sent"] == []


def test_captcha_uses_token_and_secret_from_settings(turnstile, mail):
    call(request())

    assert turnstile["calls"][0]["token"] == "token-ok"
    assert turnstile["calls"][0]["secret"] == SETTINGS["TURNSTILE_SECRET_KEY"]


@pytest.mark.parametrize(
    ("forwarded", "expected"),
    [
        ("203.0.113.7", "203.0.113.7"),
        ("203.0.113.7, 10.0.0.1", "203.0.113.7"),
        ("203.0.113.7:51234", "203.0.113.7"),
        ("2001:db8::1", "2001:db8::1"),
        ("[2001:db8::1]:51234", "2001:db8::1"),
        ("no-es-ip", None),
        (None, None),
    ],
)
def test_client_ip_from_forwarded_header(forwarded, expected, turnstile, mail):
    headers = {"X-Forwarded-For": forwarded} if forwarded else {}

    call(request(headers=headers))

    assert turnstile["calls"][0]["remote_ip"] == expected


# --- R1: envío ---

def test_valid_request_sends_mail_and_returns_200(turnstile, mail):
    body = {**VALID, "nombre": "  Ana Pérez  "}

    assert call(request(body)) == (200, {"ok": True})

    sent = mail["sent"][0]
    assert sent["connection_string"] == SETTINGS["ACS_CONNECTION_STRING"]
    assert sent["message"]["senderAddress"] == SETTINGS["MAIL_SENDER"]
    assert sent["message"]["recipients"] == {"to": [{"address": SETTINGS["MAIL_TO"]}]}
    assert sent["message"]["replyTo"] == [{"address": "ana@ejemplo.com", "displayName": "Ana Pérez"}]
    assert "Hola Roger, me gustaría conversar." in sent["message"]["content"]["plainText"]


def test_response_is_utf8_json(turnstile, mail):
    turnstile["result"] = VerifyResult(Outcome.REJECTED)

    resp = handler(request())

    assert resp.mimetype == "application/json"
    assert "Inténtalo".encode() in resp.get_body()


# --- R8: errores controlados ---

def test_mail_failure_returns_503(turnstile, mail):
    mail["error"] = MailError("HttpResponseError")

    assert call(request()) == (503, {"ok": False, "code": "unavailable", "message": SEND_MESSAGE})


@pytest.mark.parametrize("missing", ["TURNSTILE_SECRET_KEY", "ACS_CONNECTION_STRING", "MAIL_SENDER", "MAIL_TO"])
def test_missing_setting_returns_503_before_captcha(missing, monkeypatch, turnstile, mail):
    monkeypatch.delenv(missing)

    assert call(request()) == (503, {"ok": False, "code": "unavailable", "message": SEND_MESSAGE})
    assert turnstile["calls"] == [] and mail["sent"] == []


def test_unexpected_error_returns_500(monkeypatch, turnstile, mail):
    def boom(*args):
        raise RuntimeError("Ana Pérez ana@ejemplo.com")

    monkeypatch.setattr(function_app, "verify", boom)

    assert call(request()) == (500, {"ok": False, "code": "internal", "message": SEND_MESSAGE})


def test_logs_never_contain_visitor_data(monkeypatch, caplog, turnstile, mail):
    caplog.set_level("DEBUG")
    sensitive = ("Ana Pérez", "ana@ejemplo.com", "me gustaría conversar", "token-ok", "203.0.113.7")
    headers = {"X-Forwarded-For": "203.0.113.7"}

    call(request(headers=headers))  # success
    mail["error"] = MailError("HttpResponseError")
    call(request(headers=headers))  # mail failure
    monkeypatch.setattr(function_app, "verify", lambda *a: (_ for _ in ()).throw(RuntimeError("Ana Pérez ana@ejemplo.com")))
    call(request(headers=headers))  # unexpected error

    assert caplog.records
    for text in sensitive:
        assert text not in caplog.text
