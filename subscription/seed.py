import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models import User, Plan, Subscription, Payment, PlanName, SubscriptionStatus, PaymentStatus
from auth import hash_password

logger = logging.getLogger(__name__)


def run_seed(db: Session) -> None:
    """Idempotente: verifica dados existentes antes de inserir para evitar duplicatas no restart."""
    _seed_plans(db)
    _seed_users(db)
    _seed_subscriptions(db)
    _seed_payments(db)
    logger.info("Seed carregado com sucesso.")


def _seed_plans(db: Session) -> None:
    if db.query(Plan).count() > 0:
        return

    plans = [
        Plan(
            name=PlanName.BASIC,
            description="Plano básico com acesso padrão ao sistema de prescrições.",
            monthly_price=29.90,
        ),
        Plan(
            name=PlanName.PREMIUM,
            description="Plano premium com desconto em pedidos e prioridade de atendimento.",
            monthly_price=79.90,
        ),
    ]
    db.add_all(plans)
    db.commit()
    logger.info("Planos criados: BASIC, PREMIUM")


def _seed_users(db: Session) -> None:
    usernames = ["doctor_basic", "doctor_premium"]
    for username in usernames:
        if db.query(User).filter(User.username == username).first():
            continue
        user = User(
            username=username,
            email=f"{username}@hospital.com",
            password_hash=hash_password("senha123"),
        )
        db.add(user)
    db.commit()
    logger.info("Usuários criados: doctor_basic, doctor_premium")


def _seed_subscriptions(db: Session) -> None:
    basic_plan = db.query(Plan).filter(Plan.name == PlanName.BASIC).first()
    premium_plan = db.query(Plan).filter(Plan.name == PlanName.PREMIUM).first()
    doctor_basic = db.query(User).filter(User.username == "doctor_basic").first()
    doctor_premium = db.query(User).filter(User.username == "doctor_premium").first()

    now = datetime.utcnow()
    one_year = now + timedelta(days=365)

    pairs = [
        (doctor_basic, basic_plan),
        (doctor_premium, premium_plan),
    ]

    for user, plan in pairs:
        if not user or not plan:
            continue
        if db.query(Subscription).filter(Subscription.user_id == user.id).first():
            continue
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            started_at=now,
            expires_at=one_year,
        )
        db.add(sub)

    db.commit()
    logger.info("Assinaturas criadas: doctor_basic -> BASIC/ACTIVE, doctor_premium -> PREMIUM/ACTIVE")


def _seed_payments(db: Session) -> None:
    for username in ["doctor_basic", "doctor_premium"]:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            continue
        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if not sub:
            continue

        if db.query(Payment).filter(Payment.subscription_id == sub.id).count() > 0:
            continue

        # Gera 3 meses de histórico de pagamentos retroativos
        for month_offset in range(3, 0, -1):
            payment = Payment(
                subscription_id=sub.id,
                amount=sub.plan.monthly_price,
                status=PaymentStatus.PAID,
                created_at=datetime.utcnow() - timedelta(days=30 * month_offset),
            )
            db.add(payment)

    db.commit()
    logger.info("Histórico de pagamentos criado para doctor_basic e doctor_premium")
