"""Contact form field rules (R5). Pure functions: no I/O, no logging."""

import re
from dataclasses import dataclass, field

NOMBRE_MAX = 100
EMAIL_MAX = 254
MENSAJE_MIN = 10
MENSAJE_MAX = 2000

# Pragmatic check: one "@", no whitespace, and a dot in the domain. Full RFC 5322 is not the goal.
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
LINE_BREAK_RE = re.compile(r"[\r\n]")


@dataclass
class ValidationResult:
    nombre: str
    email: str
    mensaje: str
    errors: dict[str, str] = field(default_factory=dict)


def _clean(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _nombre_error(nombre: str) -> str | None:
    if not nombre:
        return "Ingresa tu nombre."
    if LINE_BREAK_RE.search(nombre):
        return "El nombre no puede contener saltos de línea."
    if len(nombre) > NOMBRE_MAX:
        return f"El nombre no puede superar los {NOMBRE_MAX} caracteres."
    return None


def _email_error(email: str) -> str | None:
    # Line breaks fail the pattern, which blocks header injection.
    if not EMAIL_RE.fullmatch(email):
        return "Correo no válido."
    if len(email) > EMAIL_MAX:
        return f"El correo no puede superar los {EMAIL_MAX} caracteres."
    return None


def _mensaje_error(mensaje: str) -> str | None:
    if len(mensaje) < MENSAJE_MIN:
        return f"El mensaje debe tener al menos {MENSAJE_MIN} caracteres."
    if len(mensaje) > MENSAJE_MAX:
        return f"El mensaje no puede superar los {MENSAJE_MAX} caracteres."
    return None


def validate(data: dict) -> ValidationResult:
    """Trim the visitor's fields and collect one error message per invalid field."""
    nombre = _clean(data.get("nombre"))
    email = _clean(data.get("email"))
    mensaje = _clean(data.get("mensaje"))

    checks = {
        "nombre": _nombre_error(nombre),
        "email": _email_error(email),
        "mensaje": _mensaje_error(mensaje),
    }
    errors = {name: message for name, message in checks.items() if message}
    return ValidationResult(nombre=nombre, email=email, mensaje=mensaje, errors=errors)
