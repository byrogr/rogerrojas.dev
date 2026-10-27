import io
import json
import socket
from urllib.error import HTTPError, URLError

import pytest

from contact import turnstile
from contact.turnstile import SITEVERIFY_URL, Outcome, verify

SECRET = "1x0000000000000000000000000000000AA"


class FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def fake_urlopen(monkeypatch):
    """Replace urlopen; records the requests and returns the configured reply or raises it."""
    calls = []
    reply = {"value": {"success": True}}

    def _urlopen(request, timeout=None):
        calls.append({"request": request, "timeout": timeout})
        value = reply["value"]
        if isinstance(value, BaseException):
            raise value
        if isinstance(value, bytes):
            return FakeResponse(value)
        return FakeResponse(json.dumps(value).encode())

    monkeypatch.setattr(turnstile, "urlopen", _urlopen)

    def configure(value):
        reply["value"] = value

    _urlopen.calls = calls
    _urlopen.reply = configure
    return _urlopen


# --- éxito y petición ---

def test_success(fake_urlopen):
    result = verify("token-ok", SECRET, "203.0.113.7")

    assert result.outcome is Outcome.OK
    assert result.error_codes == []


def test_sends_json_post_with_secret_token_and_ip(fake_urlopen):
    verify("token-ok", SECRET, "203.0.113.7")

    call = fake_urlopen.calls[0]
    request = call["request"]
    assert request.full_url == SITEVERIFY_URL
    assert request.get_method() == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == {"secret": SECRET, "response": "token-ok", "remoteip": "203.0.113.7"}
    assert call["timeout"] == turnstile.TIMEOUT_SECONDS


def test_omits_ip_when_unknown(fake_urlopen):
    verify("token-ok", SECRET, None)

    assert "remoteip" not in json.loads(fake_urlopen.calls[0]["request"].data)


# --- token rechazado (R2) ---

@pytest.mark.parametrize("token", ["", None, 123])
def test_missing_token_is_rejected_without_network(fake_urlopen, token):
    result = verify(token, SECRET, None)

    assert result.outcome is Outcome.REJECTED
    assert result.error_codes == ["missing-input-response"]
    assert fake_urlopen.calls == []


def test_oversized_token_is_rejected_without_network(fake_urlopen):
    result = verify("a" * 2049, SECRET, None)

    assert result.outcome is Outcome.REJECTED
    assert result.error_codes == ["invalid-input-response"]
    assert fake_urlopen.calls == []


def test_token_at_max_length_is_sent(fake_urlopen):
    assert verify("a" * 2048, SECRET, None).outcome is Outcome.OK


@pytest.mark.parametrize(
    "codes",
    [["invalid-input-response"], ["timeout-or-duplicate"], ["missing-input-response"], [], ["some-new-code"]],
)
def test_token_errors_are_rejected(fake_urlopen, codes):
    fake_urlopen.reply({"success": False, "error-codes": codes})

    result = verify("token", SECRET, None)

    assert result.outcome is Outcome.REJECTED
    assert result.error_codes == codes


# --- Turnstile o configuración no disponibles (R8) ---

@pytest.mark.parametrize(
    "codes",
    [["missing-input-secret"], ["invalid-input-secret"], ["internal-error"], ["bad-request"],
     ["timeout-or-duplicate", "internal-error"]],
)
def test_server_side_errors_are_unavailable(fake_urlopen, codes):
    fake_urlopen.reply({"success": False, "error-codes": codes})

    assert verify("token", SECRET, None).outcome is Outcome.UNAVAILABLE


def test_missing_secret_is_unavailable_without_network(fake_urlopen):
    result = verify("token", "", None)

    assert result.outcome is Outcome.UNAVAILABLE
    assert result.error_codes == ["missing-input-secret"]
    assert fake_urlopen.calls == []


@pytest.mark.parametrize(
    "error",
    [
        URLError("connection refused"),
        HTTPError(SITEVERIFY_URL, 502, "Bad Gateway", None, None),
        TimeoutError(),
        socket.timeout(),
        ConnectionResetError(),
    ],
)
def test_network_failures_are_unavailable(fake_urlopen, error):
    fake_urlopen.reply(error)

    result = verify("token", SECRET, None)

    assert result.outcome is Outcome.UNAVAILABLE
    assert result.error_codes == []


def test_http_error_with_json_body_is_classified_by_its_codes(fake_urlopen):
    body = io.BytesIO(json.dumps({"success": False, "error-codes": ["invalid-input-secret"]}).encode())
    fake_urlopen.reply(HTTPError(SITEVERIFY_URL, 400, "Bad Request", None, body))

    result = verify("token", SECRET, None)

    assert result.outcome is Outcome.UNAVAILABLE
    assert result.error_codes == ["invalid-input-secret"]


def test_http_error_with_token_codes_is_rejected(fake_urlopen):
    body = io.BytesIO(json.dumps({"success": False, "error-codes": ["invalid-input-response"]}).encode())
    fake_urlopen.reply(HTTPError(SITEVERIFY_URL, 400, "Bad Request", None, body))

    assert verify("token", SECRET, None).outcome is Outcome.REJECTED


@pytest.mark.parametrize("body", [b"not json", b"[]", b'{"error-codes": []}'])
def test_unexpected_body_is_unavailable(fake_urlopen, body):
    fake_urlopen.reply(body)

    assert verify("token", SECRET, None).outcome is Outcome.UNAVAILABLE


def test_logs_do_not_contain_token_secret_or_ip(fake_urlopen, caplog):
    fake_urlopen.reply(URLError("down"))

    verify("very-secret-token", SECRET, "203.0.113.7")

    assert caplog.records, "a technical error should be logged"
    for text in ("very-secret-token", SECRET, "203.0.113.7"):
        assert text not in caplog.text
