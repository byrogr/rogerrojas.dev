"""Server-side Turnstile token verification (R2, R3, R8)."""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
TIMEOUT_SECONDS = 5
TOKEN_MAX_LENGTH = 2048

# Codes caused by our configuration or by Cloudflare, not by the visitor's token.
SERVER_SIDE_CODES = {"missing-input-secret", "invalid-input-secret", "internal-error", "bad-request"}

logger = logging.getLogger(__name__)


class Outcome(Enum):
    OK = "ok"
    REJECTED = "rejected"  # captcha error for the visitor -> 400
    UNAVAILABLE = "unavailable"  # Turnstile or config failure -> 503


@dataclass
class VerifyResult:
    outcome: Outcome
    error_codes: list[str] = field(default_factory=list)


def verify(token: object, secret: str, remote_ip: str | None) -> VerifyResult:
    """Check a widget token against siteverify. Never logs the token, the secret or the IP."""
    if not secret:
        logger.error("Turnstile secret key is not configured")
        return VerifyResult(Outcome.UNAVAILABLE, ["missing-input-secret"])
    if not isinstance(token, str) or not token:
        return VerifyResult(Outcome.REJECTED, ["missing-input-response"])
    if len(token) > TOKEN_MAX_LENGTH:
        return VerifyResult(Outcome.REJECTED, ["invalid-input-response"])

    payload = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip
    request = Request(
        SITEVERIFY_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        body = _post(request)
    except (OSError, ValueError) as exc:  # URLError and timeouts are OSError; bad JSON is ValueError
        logger.warning("Turnstile siteverify failed: %s", type(exc).__name__)
        return VerifyResult(Outcome.UNAVAILABLE)

    if not isinstance(body, dict) or not isinstance(body.get("success"), bool):
        logger.warning("Turnstile siteverify returned an unexpected body")
        return VerifyResult(Outcome.UNAVAILABLE)

    codes = [code for code in body.get("error-codes", []) if isinstance(code, str)]
    if body["success"]:
        return VerifyResult(Outcome.OK)
    if SERVER_SIDE_CODES.intersection(codes):
        logger.error("Turnstile siteverify server-side error: %s", ",".join(codes))
        return VerifyResult(Outcome.UNAVAILABLE, codes)
    return VerifyResult(Outcome.REJECTED, codes)


def _post(request: Request) -> object:
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        # Cloudflare answers some errors (e.g. a bad secret) with a 4xx that still carries JSON error codes.
        if exc.fp is None:
            raise
        return json.loads(exc.read())
