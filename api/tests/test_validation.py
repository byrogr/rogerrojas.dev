import pytest

from contact.validation import validate

VALID = {"nombre": "Ana Pérez", "email": "ana@ejemplo.com", "mensaje": "Hola Roger, me gustaría conversar."}


def with_(**overrides):
    return {**VALID, **overrides}


def test_valid_data_returns_cleaned_values_and_no_errors():
    result = validate(VALID)

    assert result.errors == {}
    assert result.nombre == "Ana Pérez"
    assert result.email == "ana@ejemplo.com"
    assert result.mensaje == "Hola Roger, me gustaría conversar."


def test_trims_surrounding_whitespace():
    result = validate(with_(nombre="  Ana  ", email=" ana@ejemplo.com\n", mensaje="\n  Hola Roger, ¿cómo estás?  "))

    assert result.errors == {}
    assert result.nombre == "Ana"
    assert result.email == "ana@ejemplo.com"
    assert result.mensaje == "Hola Roger, ¿cómo estás?"


# --- nombre ---

@pytest.mark.parametrize("nombre", ["", "   ", None])
def test_nombre_required(nombre):
    assert validate(with_(nombre=nombre)).errors == {"nombre": "Ingresa tu nombre."}


def test_nombre_length_limit():
    assert "nombre" not in validate(with_(nombre="a" * 100)).errors
    assert validate(with_(nombre="a" * 101)).errors == {"nombre": "El nombre no puede superar los 100 caracteres."}


@pytest.mark.parametrize("nombre", ["Ana\nBcc: spam@x.com", "Ana\rPérez", "Ana\r\nPérez"])
def test_nombre_rejects_line_breaks(nombre):
    assert validate(with_(nombre=nombre)).errors == {"nombre": "El nombre no puede contener saltos de línea."}


# --- email ---

@pytest.mark.parametrize(
    "email",
    ["", "ana", "ana@", "@ejemplo.com", "ana@ejemplo", "ana @ejemplo.com", "ana@@ejemplo.com", None, 123],
)
def test_email_invalid_format(email):
    assert validate(with_(email=email)).errors == {"email": "Correo no válido."}


@pytest.mark.parametrize("email", ["ana@ejemplo.com\nBcc: spam@x.com", "ana@ejemplo.com\r\nCc: x@y.com"])
def test_email_rejects_header_injection(email):
    assert validate(with_(email=email)).errors == {"email": "Correo no válido."}


def test_email_length_limit():
    local = "a" * 64
    domain_254 = "b" * (254 - len(local) - 1 - 4) + ".com"
    domain_255 = "b" * (255 - len(local) - 1 - 4) + ".com"

    assert "email" not in validate(with_(email=f"{local}@{domain_254}")).errors
    assert validate(with_(email=f"{local}@{domain_255}")).errors == {
        "email": "El correo no puede superar los 254 caracteres."
    }


# --- mensaje ---

def test_mensaje_min_length():
    assert validate(with_(mensaje="a" * 9)).errors == {"mensaje": "El mensaje debe tener al menos 10 caracteres."}
    assert "mensaje" not in validate(with_(mensaje="a" * 10)).errors


def test_mensaje_min_length_counts_after_trim():
    assert "mensaje" in validate(with_(mensaje="   " + "a" * 9 + "   ")).errors


def test_mensaje_max_length():
    assert "mensaje" not in validate(with_(mensaje="a" * 2000)).errors
    assert validate(with_(mensaje="a" * 2001)).errors == {"mensaje": "El mensaje no puede superar los 2000 caracteres."}


def test_mensaje_allows_line_breaks():
    assert validate(with_(mensaje="Hola Roger,\n\nme gustaría conversar.")).errors == {}


@pytest.mark.parametrize("mensaje", [None, 42, ["a" * 20]])
def test_mensaje_non_string_is_too_short(mensaje):
    assert validate(with_(mensaje=mensaje)).errors == {"mensaje": "El mensaje debe tener al menos 10 caracteres."}


# --- combinado ---

def test_reports_every_invalid_field():
    errors = validate({"nombre": "", "email": "x", "mensaje": "corto"}).errors

    assert set(errors) == {"nombre", "email", "mensaje"}


def test_missing_fields_are_reported():
    assert set(validate({}).errors) == {"nombre", "email", "mensaje"}
