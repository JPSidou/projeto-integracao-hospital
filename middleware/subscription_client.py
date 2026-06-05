import logging
import requests
from config import settings

logger = logging.getLogger("middleware.subscription_client")

BASE_URL = settings.SUBSCRIPTION_SERVICE_URL.rstrip("/")
TIMEOUT = settings.SUBSCRIPTION_TIMEOUT_SECONDS


class SubscriptionAuthError(Exception):
    """Credenciais rejeitadas pelo Subscription Service."""


class SubscriptionServiceError(Exception):
    """Resposta inesperada do Subscription Service."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class SubscriptionServiceUnavailableError(Exception):
    """Subscription Service inacessível."""


def authenticate(username: str, password: str) -> dict:
    """Autentica o usuário e retorna plano e status da assinatura em uma única chamada."""
    url = f"{BASE_URL}/auth/login"
    logger.info("Autenticando username='%s' no Subscription Service", username)

    try:
        response = requests.post(
            url,
            json={"username": username, "password": password},
            timeout=TIMEOUT,
        )
    except requests.exceptions.ConnectionError as exc:
        logger.error("Subscription Service inacessível em %s: %s", url, exc)
        raise SubscriptionServiceUnavailableError(
            f"Cannot reach Subscription Service at {BASE_URL}"
        ) from exc
    except requests.exceptions.Timeout as exc:
        logger.error("Timeout ao chamar Subscription Service")
        raise SubscriptionServiceUnavailableError("Subscription Service timed out") from exc

    if response.status_code == 200:
        data = response.json()
        logger.info(
            "Autenticação OK: username='%s' | plano=%s | status=%s",
            username, data.get("plan"), data.get("subscription_status"),
        )
        return data

    if response.status_code == 401:
        logger.warning("Autenticação falhou para username='%s'", username)
        raise SubscriptionAuthError("Invalid credentials")

    logger.error(
        "Erro no Subscription Service | status=%d | body=%s",
        response.status_code, response.text[:500],
    )
    raise SubscriptionServiceError(
        status_code=response.status_code,
        detail=f"Subscription Service error: {response.text[:200]}",
    )
