import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("farmacia.subscription_client")

SUBSCRIPTION_SERVICE_URL = os.getenv("SUBSCRIPTION_SERVICE_URL", "http://localhost:8000").rstrip("/")
SUBSCRIPTION_TIMEOUT_SECONDS = int(os.getenv("SUBSCRIPTION_TIMEOUT_SECONDS", "10"))


class SubscriptionUnavailableError(Exception):
    """Subscription inacessível ou timeout."""


class SubscriptionServiceError(Exception):
    """Subscription retornou erro inesperado."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def fetch_subscription(user_id: int) -> dict:
    url = f"{SUBSCRIPTION_SERVICE_URL}/subscriptions/{user_id}"
    logger.info("Consultando assinatura no Subscription | user_id=%s", user_id)

    try:
        response = requests.get(url, timeout=SUBSCRIPTION_TIMEOUT_SECONDS)
    except requests.exceptions.ConnectionError as exc:
        raise SubscriptionUnavailableError(
            f"Cannot reach Subscription Service at {SUBSCRIPTION_SERVICE_URL}"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise SubscriptionUnavailableError("Subscription Service timed out") from exc

    if response.status_code == 200:
        data = response.json()
        plan_name = (data.get("plan") or {}).get("name")
        return {
            "id": data.get("id"),
            "user_id": data.get("user_id"),
            "status": data.get("status"),
            "plan_name": plan_name,
            "started_at": data.get("started_at"),
            "expires_at": data.get("expires_at"),
        }

    raise SubscriptionServiceError(
        status_code=response.status_code,
        detail=f"Subscription Service error: {response.text[:200]}",
    )
