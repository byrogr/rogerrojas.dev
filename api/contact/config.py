"""Settings read from environment variables (R10). Values are never logged."""

import os
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Settings:
    turnstile_secret_key: str
    acs_connection_string: str
    mail_sender: str
    mail_to: str

    def missing(self) -> list[str]:
        """Names of the environment variables that are empty or unset."""
        return [f.name.upper() for f in fields(self) if not getattr(self, f.name)]


def load_settings() -> Settings:
    return Settings(
        turnstile_secret_key=os.environ.get("TURNSTILE_SECRET_KEY", "").strip(),
        acs_connection_string=os.environ.get("ACS_CONNECTION_STRING", "").strip(),
        mail_sender=os.environ.get("MAIL_SENDER", "").strip(),
        mail_to=os.environ.get("MAIL_TO", "").strip(),
    )
