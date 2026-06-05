import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SUBSCRIPTION_SERVICE_URL: str = os.getenv("SUBSCRIPTION_SERVICE_URL", "http://localhost:8000").rstrip("/")

    # URL da Farmácia
    PHARMACY_URL: str = os.getenv("PHARMACY_URL", "http://localhost:3001").rstrip("/")
    PHARMACY_TIMEOUT_SECONDS: int = int(os.getenv("PHARMACY_TIMEOUT_SECONDS", "10"))

    # Desconto aplicado a pedidos do plano PREMIUM (configurável via .env)
    PREMIUM_DISCOUNT_PERCENT: float = float(os.getenv("PREMIUM_DISCOUNT_PERCENT", "10"))

    SUBSCRIPTION_TIMEOUT_SECONDS: int = int(os.getenv("SUBSCRIPTION_TIMEOUT_SECONDS", "10"))


settings = Settings()
