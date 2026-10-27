import azure.functions as func
import pytest

from function_app import contact

handler = contact.build().get_user_function()


def make_request(method: str) -> func.HttpRequest:
    return func.HttpRequest(method=method, url="/api/contact", body=b"")


@pytest.mark.parametrize("method", ["GET", "PUT", "PATCH", "DELETE"])
def test_non_post_returns_405(method):
    resp = handler(make_request(method))

    assert resp.status_code == 405
    assert resp.headers["Allow"] == "POST"
    assert resp.get_body() == b'{"ok": false, "code": "bad_request"}'
