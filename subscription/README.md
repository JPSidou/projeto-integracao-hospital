# Subscription Service

Serviço de gerenciamento de assinaturas inspirado no Stripe.  
Responsável por autenticação de usuários, gerenciamento de planos, ciclo de vida de assinaturas e histórico de pagamentos.

## Portas e URLs

- **Porta:** 8000
- **Docs:** http://localhost:8000/docs

## Como Rodar

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Dados de Seed (criados automaticamente)

| Usuário          | Senha     | Plano   | Status  |
|------------------|-----------|---------|---------|
| `doctor_basic`   | `senha123`| BASIC   | ACTIVE  |
| `doctor_premium` | `senha123`| PREMIUM | ACTIVE  |

## Endpoints

| Método | Endpoint                          | Descrição                        |
|--------|-----------------------------------|----------------------------------|
| POST   | `/auth/login`                     | Login — retorna JWT + plano      |
| POST   | `/users`                          | Criar usuário                    |
| GET    | `/users/{id}`                     | Buscar usuário                   |
| GET    | `/plans`                          | Listar planos                    |
| POST   | `/plans`                          | Criar plano                      |
| GET    | `/subscriptions/{user_id}`        | Buscar assinatura                |
| POST   | `/subscriptions`                  | Criar assinatura                 |
| PUT    | `/subscriptions/{subscription_id}`| Atualizar assinatura             |
| POST   | `/payments`                       | Registrar pagamento              |
| GET    | `/payments/{user_id}`             | Listar pagamentos                |
| GET    | `/health`                         | Health check                     |
