import json

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def json_response(status_code: int, body: dict, headers: dict | None = None) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body),
        status_code=status_code,
        mimetype="application/json",
        headers=headers,
    )


# The route accepts every method so non-POST requests get a 405 instead of the host's 404 (R7).
@app.route(route="contact")
def contact(req: func.HttpRequest) -> func.HttpResponse:
    if req.method != "POST":
        return json_response(405, {"ok": False, "code": "bad_request"}, {"Allow": "POST"})

    # Full POST handling (validation, captcha, email) arrives in T1.5.
    return json_response(501, {"ok": False, "code": "internal"})
