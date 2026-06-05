import logging
import os
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import engine, get_db, Base
from models import User, Plan, Subscription, Payment, SubscriptionStatus
from schemas import (
    LoginRequest, LoginResponse,
    UserCreate, UserResponse,
    PlanCreate, PlanResponse,
    SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse,
    PaymentCreate, PaymentResponse,
    ErrorResponse,
)
from auth import hash_password, verify_password, create_access_token
from seed import run_seed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("subscription")

load_dotenv()

app = FastAPI(
    title="Subscription Service",
    description="Serviço de assinaturas para o projeto de integração hospitalar.",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        run_seed(db)
    finally:
        db.close()
    logger.info("Subscription Service iniciado na porta %s.", os.getenv("PORT", "8000"))


def http_error(status_code: int, detail: str):
    raise HTTPException(status_code=status_code, detail=detail)


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    logger.info("Tentativa de login: username='%s'", payload.username)

    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        logger.warning("Login inválido: username='%s'", payload.username)
        http_error(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    # Retorna plano e status da assinatura no login para evitar chamadas extras do Middleware
    subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.started_at.desc())
        .first()
    )

    plan_name = None
    sub_status = None
    if subscription:
        plan_name = subscription.plan.name.value if subscription.plan else None
        sub_status = subscription.status.value

    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "plan": plan_name,
        "subscription_status": sub_status,
    }
    token = create_access_token(token_data)

    logger.info(
        "Login bem-sucedido: username='%s' | plano=%s | status=%s",
        payload.username, plan_name, sub_status,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        plan=plan_name,
        subscription_status=sub_status,
    )


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Username already exists")
    if db.query(User).filter(User.email == payload.email).first():
        http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Email already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Usuário criado: id=%d username='%s'", user.id, user.username)
    return user


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        http_error(status.HTTP_404_NOT_FOUND, f"User {user_id} not found")
    return user


@app.get("/plans", response_model=List[PlanResponse])
def list_plans(db: Session = Depends(get_db)):
    return db.query(Plan).all()


@app.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)):
    if db.query(Plan).filter(Plan.name == payload.name).first():
        http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Plan '{payload.name}' already exists")
    plan = Plan(**payload.dict())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    logger.info("Plano criado: %s | R$%.2f/mês", plan.name, plan.monthly_price)
    return plan


@app.get("/subscriptions/{user_id}", response_model=SubscriptionResponse)
def get_subscription(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        http_error(status.HTTP_404_NOT_FOUND, f"User {user_id} not found")

    subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .order_by(Subscription.started_at.desc())
        .first()
    )
    if not subscription:
        http_error(status.HTTP_404_NOT_FOUND, f"No subscription found for user {user_id}")
    return subscription


@app.post("/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db)):
    if not db.query(User).filter(User.id == payload.user_id).first():
        http_error(status.HTTP_404_NOT_FOUND, f"User {payload.user_id} not found")
    if not db.query(Plan).filter(Plan.id == payload.plan_id).first():
        http_error(status.HTTP_404_NOT_FOUND, f"Plan {payload.plan_id} not found")

    sub = Subscription(**payload.dict())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    logger.info("Assinatura criada: id=%d user_id=%d plan_id=%d", sub.id, sub.user_id, sub.plan_id)
    return sub


@app.put("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(
    subscription_id: int,
    payload: SubscriptionUpdate,
    db: Session = Depends(get_db),
):
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        http_error(status.HTTP_404_NOT_FOUND, f"Subscription {subscription_id} not found")

    sub.status = payload.status
    if payload.expires_at is not None:
        sub.expires_at = payload.expires_at

    db.commit()
    db.refresh(sub)
    logger.info("Assinatura %d atualizada: status=%s", subscription_id, sub.status)
    return sub


@app.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db)):
    if not db.query(Subscription).filter(Subscription.id == payload.subscription_id).first():
        http_error(status.HTTP_404_NOT_FOUND, f"Subscription {payload.subscription_id} not found")

    payment = Payment(**payload.dict())
    db.add(payment)
    db.commit()
    db.refresh(payment)
    logger.info(
        "Pagamento registrado: id=%d subscription_id=%d valor=%.2f status=%s",
        payment.id, payment.subscription_id, payment.amount, payment.status,
    )
    return payment


@app.get("/payments/{user_id}", response_model=List[PaymentResponse])
def get_payments(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        http_error(status.HTTP_404_NOT_FOUND, f"User {user_id} not found")

    payments = (
        db.query(Payment)
        .join(Subscription)
        .filter(Subscription.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    return payments


@app.get("/health")
def health():
    return {"status": "ok", "service": "subscription"}
