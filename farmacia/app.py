"""
Serviço de Farmácia.
Run: uvicorn app:app --host 0.0.0.0 --port 3001 --reload
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from subscription_client import (
    fetch_subscription,
    SubscriptionServiceError,
    SubscriptionUnavailableError,
)
from viacep_client import AddressLookupError, AddressLookupUnavailableError, lookup_address

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("farmacia")

app = FastAPI(
    title="Farmácia Service",
    description="Processa pedidos de prescrição e integra com Subscription + ViaCEP.",
    version="1.0.0",
)

_orders: dict[str, dict] = {}


class OrderRequest(BaseModel):
    paciente_nome: str = Field(..., min_length=1)
    paciente_cep: str = Field(..., min_length=8, max_length=8, pattern=r"^\d{8}$")
    medicamento: str = Field(..., min_length=1)
    plano_medico: str = Field(..., min_length=3, max_length=20)
    user_id: Optional[int] = None


class DeliveryAddress(BaseModel):
    logradouro: str
    bairro: str
    localidade: str
    uf: str


class PharmacyOrderResponse(BaseModel):
    status: str
    plano_medico: str
    endereco_entrega: DeliveryAddress


def _normalize_plan(plan: Optional[str]) -> str:
    if not plan:
        return "BASIC"
    plan_upper = plan.upper().strip()
    if plan_upper in ("BASIC", "PREMIUM"):
        return plan_upper
    return "BASIC"


def _validate_subscription(user_id: Optional[int], fallback_plan: str) -> tuple[str, Optional[dict]]:
    if user_id is None:
        return fallback_plan, None

    try:
        subscription = fetch_subscription(user_id=user_id)
    except SubscriptionUnavailableError as exc:
        logger.error("Subscription indisponível para user_id=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Subscription Service is currently unavailable",
        ) from exc
    except SubscriptionServiceError as exc:
        logger.error("Erro no Subscription para user_id=%s: %s", user_id, exc.detail)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Subscription Service returned an unexpected error",
        ) from exc

    sub_status = (subscription.get("status") or "").upper()
    if sub_status in ("EXPIRED", "CANCELED"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: subscription is {sub_status.lower()}",
        )
    if sub_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: subscription is not active",
        )

    authoritative_plan = subscription.get("plan_name")
    return _normalize_plan(authoritative_plan or fallback_plan), subscription


@app.post("/pedidos", response_model=PharmacyOrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderRequest):
    plano_pedido = _normalize_plan(payload.plano_medico)
    plano_final, subscription_snapshot = _validate_subscription(
        user_id=payload.user_id,
        fallback_plan=plano_pedido,
    )

    try:
        endereco = lookup_address(payload.paciente_cep)
    except AddressLookupUnavailableError as exc:
        logger.error("ViaCEP indisponível para CEP=%s: %s", payload.paciente_cep, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Address lookup service is currently unavailable",
        ) from exc
    except AddressLookupError as exc:
        logger.warning("Falha de CEP para pedido: %s", exc)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    order_id = str(uuid.uuid4())
    processed_at = datetime.utcnow().isoformat()

    record = {
        "order_id": order_id,
        "status": "Pedido processado",
        "plano_medico": plano_final,
        "paciente_nome": payload.paciente_nome,
        "paciente_cep": payload.paciente_cep,
        "medicamento": payload.medicamento,
        "endereco_entrega": endereco,
        "user_id": payload.user_id,
        "subscription_snapshot": subscription_snapshot,
        "processed_at": processed_at,
    }
    _orders[order_id] = record

    logger.info(
        "Pedido processado | order_id=%s | user_id=%s | plano=%s | cep=%s",
        order_id, payload.user_id, plano_final, payload.paciente_cep,
    )

    return {
        "status": record["status"],
        "plano_medico": record["plano_medico"],
        "endereco_entrega": record["endereco_entrega"],
    }


@app.get("/pedidos/{order_id}")
def get_order(order_id: str):
    order = _orders.get(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@app.get("/health")
def health():
    return {"status": "ok", "service": "farmacia"}
