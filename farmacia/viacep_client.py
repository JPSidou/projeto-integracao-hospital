import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("farmacia.viacep_client")

VIACEP_BASE_URL = os.getenv("VIACEP_BASE_URL", "https://viacep.com.br/ws").rstrip("/")
VIACEP_TIMEOUT_SECONDS = int(os.getenv("VIACEP_TIMEOUT_SECONDS", "10"))


class AddressLookupUnavailableError(Exception):
    """ViaCEP indisponível ou timeout."""


class AddressLookupError(Exception):
    """CEP inválido ou não encontrado."""


def lookup_address(cep: str) -> dict:
    cep_digits = "".join(ch for ch in cep if ch.isdigit())
    if len(cep_digits) != 8:
        raise AddressLookupError("CEP must contain exactly 8 digits")

    url = f"{VIACEP_BASE_URL}/{cep_digits}/json/"
    logger.info("Consultando ViaCEP | cep=%s", cep_digits)

    try:
        response = requests.get(url, timeout=VIACEP_TIMEOUT_SECONDS)
    except requests.exceptions.ConnectionError as exc:
        raise AddressLookupUnavailableError("Cannot reach ViaCEP") from exc
    except requests.exceptions.Timeout as exc:
        raise AddressLookupUnavailableError("ViaCEP request timed out") from exc

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
