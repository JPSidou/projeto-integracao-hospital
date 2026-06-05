import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("farmacia.viacep_client")

VIACEP_BASE_URL = os.getenv("VIACEP_BASE_URL", "https://viacep.com.br/ws").rstrip("/")
BRASILAPI_CEP_BASE_URL = os.getenv(
    "BRASILAPI_CEP_BASE_URL",
    "https://brasilapi.com.br/api/cep/v1",
).rstrip("/")
VIACEP_TIMEOUT_SECONDS = int(os.getenv("VIACEP_TIMEOUT_SECONDS", "10"))


class AddressLookupUnavailableError(Exception):
    """ViaCEP indisponível ou timeout."""


class AddressLookupError(Exception):
    """CEP inválido ou não encontrado."""


def lookup_address(cep: str) -> dict:
    cep_digits = "".join(ch for ch in cep if ch.isdigit())
    if len(cep_digits) != 8:
        raise AddressLookupError("CEP must contain exactly 8 digits")

    errors = []

    try:
        return _lookup_viacep(cep_digits)
    except AddressLookupError:
        raise
    except AddressLookupUnavailableError as exc:
        errors.append(str(exc))
        logger.warning("ViaCEP falhou para CEP=%s: %s", cep_digits, exc)

    try:
        return _lookup_brasilapi(cep_digits)
    except AddressLookupError:
        raise
    except AddressLookupUnavailableError as exc:
        errors.append(str(exc))
        logger.warning("BrasilAPI falhou para CEP=%s: %s", cep_digits, exc)

    raise AddressLookupUnavailableError("; ".join(errors) or "All CEP providers are unavailable")


def _lookup_viacep(cep_digits: str) -> dict:
    url = f"{VIACEP_BASE_URL}/{cep_digits}/json/"
    logger.info("Consultando ViaCEP | cep=%s", cep_digits)

    try:
        response = requests.get(url, timeout=VIACEP_TIMEOUT_SECONDS)
    except requests.exceptions.ConnectionError as exc:
        raise AddressLookupUnavailableError(f"Cannot reach ViaCEP: {exc}") from exc
    except requests.exceptions.Timeout as exc:
        raise AddressLookupUnavailableError(f"ViaCEP request timed out: {exc}") from exc

    if response.status_code == 400:
        raise AddressLookupError("Invalid CEP format for ViaCEP")
    if response.status_code != 200:
        raise AddressLookupUnavailableError(f"ViaCEP returned status {response.status_code}")

    data = response.json()
    if data.get("erro") is True:
        raise AddressLookupError("CEP not found")

    return {
        "logradouro": data.get("logradouro") or "",
        "bairro": data.get("bairro") or "",
        "localidade": data.get("localidade") or "",
        "uf": data.get("uf") or "",
    }


def _lookup_brasilapi(cep_digits: str) -> dict:
    url = f"{BRASILAPI_CEP_BASE_URL}/{cep_digits}"
    logger.info("Consultando BrasilAPI CEP | cep=%s", cep_digits)

    try:
        response = requests.get(url, timeout=VIACEP_TIMEOUT_SECONDS)
    except requests.exceptions.ConnectionError as exc:
        raise AddressLookupUnavailableError(f"Cannot reach BrasilAPI: {exc}") from exc
    except requests.exceptions.Timeout as exc:
        raise AddressLookupUnavailableError(f"BrasilAPI request timed out: {exc}") from exc

    if response.status_code in (400, 404):
        raise AddressLookupError("CEP not found")
    if response.status_code != 200:
        raise AddressLookupUnavailableError(f"BrasilAPI returned status {response.status_code}")

    data = response.json()
    return {
        "logradouro": data.get("street") or "",
        "bairro": data.get("neighborhood") or "",
        "localidade": data.get("city") or "",
        "uf": data.get("state") or "",
    }
