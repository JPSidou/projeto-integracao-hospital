"""
Adaptador da Farmácia — ponto único de integração com o serviço de Farmácia.

Contrato esperado da Farmácia
------------------------------
Endpoint : POST /pedidos
Base URL : variável PHARMACY_URL (padrão: http://localhost:3001)

Request body:
    {
        "paciente_nome": "string",
        "paciente_cep":  "string (8 dígitos, sem hífen)",
        "medicamento":   "string",
        "plano_medico":  "BASIC" | "PREMIUM",
        "user_id":       "int (opcional)"
    }

Response (HTTP 200 ou 201):
    {
        "status":           "Pedido processado",
        "plano_medico":     "BASIC" | "PREMIUM",
        "endereco_entrega": {
            "logradouro": "string",
            "bairro":     "string",
            "localidade": "string",
            "uf":         "string"
        }
    }

Erros esperados:
    422 — Payload inválido
    500 — Erro interno da Farmácia
    503 — Farmácia indisponível
"""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("middleware.pharmacy_adapter")

PHARMACY_URL = os.getenv("PHARMACY_URL", "http://localhost:3001").rstrip("/")
PHARMACY_TIMEOUT = int(os.getenv("PHARMACY_TIMEOUT_SECONDS", "10"))


class PharmacyUnavailableError(Exception):
    """Farmácia inacessível ou timeout."""


class PharmacyError(Exception):
    """Farmácia retornou erro inesperado."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def send_order(
    paciente_nome: str,
    paciente_cep: str,
    medicamento: str,
    plano_medico: str,
    user_id: int | None = None,
) -> dict:
    """Encaminha o pedido de prescrição para a Farmácia."""
    payload = {
        "paciente_nome": paciente_nome,
        "paciente_cep": paciente_cep,
        "medicamento": medicamento,
        "plano_medico": plano_medico,
        "user_id": user_id,
    }

    url = f"{PHARMACY_URL}/pedidos"
    logger.info(
        "Encaminhando pedido para Farmácia | url=%s | paciente=%s | medicamento=%s | plano=%s",
        url, paciente_nome, medicamento, plano_medico,
    )

    try:
        response = requests.post(url, json=payload, timeout=PHARMACY_TIMEOUT)
    except requests.exceptions.ConnectionError as exc:
        logger.error("Farmácia inacessível em %s: %s", url, exc)
        raise PharmacyUnavailableError(f"Cannot reach Pharmacy at {url}") from exc
    except requests.exceptions.Timeout as exc:
        logger.error("Timeout ao chamar Farmácia após %ds", PHARMACY_TIMEOUT)
        raise PharmacyUnavailableError("Pharmacy request timed out") from exc

    if response.status_code in (200, 201):
        logger.info("Farmácia respondeu com sucesso | status=%d", response.status_code)
        return response.json()

    logger.error(
        "Erro retornado pela Farmácia | status=%d | body=%s",
        response.status_code, response.text[:500],
    )
    raise PharmacyError(
        status_code=response.status_code,
        detail=f"Pharmacy error: {response.text[:200]}",
    )
