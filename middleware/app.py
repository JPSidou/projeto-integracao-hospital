"""
Middleware Service — orquestrador central da integração hospitalar.
Run: uvicorn app:app --host 0.0.0.0 --port ${PORT:-3000}
"""

import base64
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import settings
from subscription_client import (
    authenticate,
    SubscriptionAuthError,
    SubscriptionServiceError,
    SubscriptionServiceUnavailableError,
)
from adapters.pharmacy_adapter import (
    send_order,
    PharmacyUnavailableError,
    PharmacyError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("middleware")

# Pedidos armazenados em memória para satisfazer GET /orders/{id}.
# Em produção, substituir por tabela no banco de dados.
_orders: dict = {}

app = FastAPI(
    title="Middleware Service",
    description="Orquestrador central do projeto de integração hospitalar.",
    version="1.0.0",
)


class OrderRequest(BaseModel):
    paciente_nome: str = Field(..., min_length=1)
    paciente_cep: str = Field(..., min_length=8, max_length=8, pattern=r"^\d{8}$")
    medicamento: str = Field(..., min_length=1)


class OrderResponse(BaseModel):
    order_id: str
    status: str
    plano_medico: str
    discount_applied: bool
    discount_percent: Optional[float]
    pharmacy_response: Optional[dict]
    processed_at: str


class ErrorResponse(BaseModel):
    detail: str


def _extract_basic_auth(request: Request) -> tuple[str, str]:
    """Extrai usuário e senha do header Authorization: Basic."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        raise ValueError("Missing or invalid Authorization header")

    try:
        encoded = auth_header[len("Basic "):]
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
        return username, password
    except Exception as exc:
        raise ValueError("Malformed Basic Auth header") from exc


def _apply_business_rules(plan: str, medicamento: str) -> dict:
    """Aplica desconto para plano PREMIUM; plano BASIC segue fluxo padrão."""
    plan_upper = (plan or "").upper()

    if plan_upper == "PREMIUM":
        discount = settings.PREMIUM_DISCOUNT_PERCENT
        logger.info("Regra PREMIUM aplicada | desconto=%.1f%%", discount)
        return {
            "discount_applied": True,
            "discount_percent": discount,
            "final_note": f"Desconto PREMIUM de {discount}% aplicado.",
        }

    logger.info("Regra BASIC aplicada | sem desconto")
    return {
        "discount_applied": False,
        "discount_percent": None,
        "final_note": "Plano BASIC — fluxo padrão.",
    }


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Exceção não tratada: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.post(
    "/pedidos",
    response_model=OrderResponse,
    responses={
        200: {"description": "Pedido processado com sucesso"},
        401: {"model": ErrorResponse, "description": "Credenciais inválidas"},
        403: {"model": ErrorResponse, "description": "Assinatura expirada ou cancelada"},
        422: {"model": ErrorResponse, "description": "Erro de validação"},
        503: {"model": ErrorResponse, "description": "Serviço indisponível"},
    },
)
async def receive_order(request: Request, body: OrderRequest):
    order_id = str(uuid.uuid4())
    received_at = datetime.utcnow().isoformat()

    logger.info(
        "Pedido recebido | order_id=%s | paciente=%s | medicamento=%s",
        order_id, body.paciente_nome, body.medicamento,
    )

    try:
        username, password = _extract_basic_auth(request)
    except ValueError as exc:
        logger.warning("Falha ao extrair credenciais: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authorization header is missing or malformed"},
        )

    try:
        auth_data = authenticate(username, password)
    except SubscriptionAuthError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid credentials"},
        )
    except SubscriptionServiceUnavailableError as exc:
        logger.error("Subscription Service indisponível: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Subscription Service is currently unavailable"},
        )
    except SubscriptionServiceError as exc:
        logger.error("Erro no Subscription Service: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Subscription Service returned an unexpected error"},
        )

    plan = auth_data.get("plan") or "BASIC"
    sub_status = auth_data.get("subscription_status") or "UNKNOWN"
    user_id = auth_data.get("user_id")

    logger.info(
        "Autenticação validada | user_id=%s | plano=%s | status_assinatura=%s",
        user_id, plan, sub_status,
    )

    # Bloqueia acesso para assinaturas inativas
    if sub_status in ("EXPIRED", "CANCELED"):
        logger.warning("Pedido negado | user_id=%s | status=%s", user_id, sub_status)
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": f"Access denied: subscription is {sub_status.lower()}",
                "subscription_status": sub_status,
            },
        )

    if sub_status != "ACTIVE":
        logger.warning("Pedido negado | user_id=%s | status desconhecido=%s", user_id, sub_status)
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Access denied: subscription is not active"},
        )

    rules = _apply_business_rules(plan, body.medicamento)

    pharmacy_response = None
    pharmacy_available = True

    try:
        pharmacy_response = send_order(
            paciente_nome=body.paciente_nome,
            paciente_cep=body.paciente_cep,
            medicamento=body.medicamento,
            plano_medico=plan,
            user_id=user_id,
        )
        logger.info("Farmácia respondeu | order_id=%s", order_id)

    except PharmacyUnavailableError as exc:
        logger.warning("Farmácia indisponível | order_id=%s | motivo=%s", order_id, exc)
        pharmacy_available = False
        # Retorno parcial: assinatura válida, pedido registrado para reprocessamento
        pharmacy_response = {
            "status": "Farmácia indisponível — pedido registrado para reprocessamento",
            "plano_medico": plan,
            "endereco_entrega": None,
        }

    except PharmacyError as exc:
        logger.error(
            "Erro na Farmácia | order_id=%s | status=%d | detalhe=%s",
            order_id, exc.status_code, exc.detail,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": exc.detail},
        )

    order_record = {
        "order_id": order_id,
        "user_id": user_id,
        "username": username,
        "plan": plan,
        "subscription_status": sub_status,
        "paciente_nome": body.paciente_nome,
        "paciente_cep": body.paciente_cep,
        "medicamento": body.medicamento,
        "discount_applied": rules["discount_applied"],
        "discount_percent": rules["discount_percent"],
        "pharmacy_available": pharmacy_available,
        "pharmacy_response": pharmacy_response,
        "processed_at": received_at,
    }
    _orders[order_id] = order_record
    logger.info("Pedido armazenado | order_id=%s", order_id)

    response_status_code = status.HTTP_200_OK if pharmacy_available else status.HTTP_202_ACCEPTED

    return JSONResponse(
        status_code=response_status_code,
        content={
            "order_id": order_id,
            "status": pharmacy_response.get("status", "Pedido processado"),
            "plano_medico": plan,
            "discount_applied": rules["discount_applied"],
            "discount_percent": rules["discount_percent"],
            "pharmacy_response": pharmacy_response,
            "processed_at": received_at,
        },
    )


@app.get(
    "/orders/{order_id}",
    responses={
        200: {"description": "Pedido encontrado"},
        404: {"model": ErrorResponse, "description": "Pedido não encontrado"},
    },
)
async def get_order(order_id: str):
    order = _orders.get(order_id)
    if not order:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Order '{order_id}' not found"},
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content=order)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "middleware"}


@app.get("/")
async def root():
    return {"status": "ok", "service": "middleware", "docs": "/docs", "health": "/health"}


@app.on_event("startup")
async def on_startup():
    logger.info("Middleware iniciado na porta %s.", os.getenv("PORT", "3000"))
    logger.info(
        "Config | SUBSCRIPTION_SERVICE_URL=%s | PHARMACY_URL=%s | PREMIUM_DISCOUNT=%.1f%%",
        settings.SUBSCRIPTION_SERVICE_URL,
        settings.PHARMACY_URL,
        settings.PREMIUM_DISCOUNT_PERCENT,
    )
