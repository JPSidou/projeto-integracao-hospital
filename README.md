# Projeto Integração AV3 — Hospital + Middleware + Subscription Service

Sistema de integração para a disciplina de Integração de Sistemas.  
Simula o fluxo completo de prescrição médica, desde a interface do médico até o processamento pela farmácia, passando por autenticação e validação de plano de assinatura.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        Hospital (porta 8501)                    │
│                   Interface Streamlit do médico                 │
│         POST /pedidos  →  Authorization: Basic <creds>          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Middleware (porta 3000)                       │
│                   Orquestrador central                          │
│                                                                 │
│  1. Extrai credenciais do Basic Auth                            │
│  2. Autentica no Subscription Service                           │
│  3. Valida status da assinatura                                 │
│  4. Aplica regras de negócio (desconto PREMIUM)                 │
│  5. Encaminha pedido para a Farmácia                            │
│  6. Retorna resposta unificada ao Hospital                      │
└──────────┬────────────────────────────────────┬─────────────────┘
           │                                    │
           ▼                                    ▼
┌──────────────────────┐            ┌───────────────────────────┐
│  Subscription Service│            │  Farmácia (porta 3001)    │
│     (porta 8000)     │            │  (implementada)           │
│                      │            │                           │
│  - Autenticação JWT  │            │  POST /pedidos            │
│  - Planos BASIC /    │            │  Integração ViaCEP        │
│    PREMIUM           │            │  Retorna endereço         │
│  - Assinaturas       │            └───────────────────────────┘
│  - Pagamentos        │
└──────────────────────┘
```

---

## Estrutura de Pastas

```
projeto-integracao-hospital/
│
├── hospital/                   # Sistema existente — NÃO MODIFICAR
│   ├── app.py
│   ├── requirements.txt
│   └── README.md
│
├── middleware/                 # Orquestrador central (este projeto)
│   ├── adapters/
│   │   └── pharmacy_adapter.py # Camada de integração com a Farmácia
│   ├── app.py
│   ├── config.py
│   ├── subscription_client.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── subscription/               # Serviço de assinaturas (este projeto)
│   ├── app.py
│   ├── auth.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── seed.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── farmacia/                   # Serviço da Farmácia (este projeto)
│   ├── app.py
│   ├── subscription_client.py
│   ├── viacep_client.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
└── README.md                   # Este arquivo
```

---

## Pré-requisitos

- Python 3.10 ou superior
- pip

---

## Instalação e Execução

### 1. Subscription Service (porta 8000)

```bash
cd subscription
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

O banco de dados SQLite é criado automaticamente em `subscription/subscription.db`.  
Os dados de seed (usuários, planos, assinaturas) são inseridos na primeira inicialização.

### 2. Farmácia (porta 3001)

```bash
cd farmacia
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

### 3. Middleware (porta 3000)

```bash
cd middleware
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 3000 --reload
```

### 4. Hospital (porta 8501)

```bash
cd hospital
pip install -r requirements.txt
streamlit run app.py
```

Acesse: http://localhost:8501

---

## Variáveis de Ambiente

### `subscription/.env`

| Variável                    | Padrão                        | Descrição                              |
|-----------------------------|-------------------------------|----------------------------------------|
| `DATABASE_URL`              | `sqlite:///./subscription.db` | URL do banco de dados SQLite           |
| `SECRET_KEY`                | `change-me-in-production`     | Chave secreta para assinar JWTs        |
| `ALGORITHM`                 | `HS256`                       | Algoritmo JWT                          |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                        | Validade do token em minutos           |

### `middleware/.env`

| Variável                      | Padrão                    | Descrição                                    |
|-------------------------------|---------------------------|----------------------------------------------|
| `SUBSCRIPTION_SERVICE_URL`    | `http://localhost:8000`   | URL do Subscription Service                  |
| `PHARMACY_URL`                | `http://localhost:3001`   | URL da Farmácia                               |
| `PREMIUM_DISCOUNT_PERCENT`    | `10`                      | Desconto (%) aplicado ao plano PREMIUM        |
| `SUBSCRIPTION_TIMEOUT_SECONDS`| `10`                      | Timeout para chamadas ao Subscription Service |
| `PHARMACY_TIMEOUT_SECONDS`    | `10`                      | Timeout para chamadas à Farmácia              |

### `farmacia/.env`

| Variável                      | Padrão                    | Descrição                                     |
|-------------------------------|---------------------------|-----------------------------------------------|
| `SUBSCRIPTION_SERVICE_URL`    | `http://localhost:8000`   | URL do Subscription Service                    |
| `SUBSCRIPTION_TIMEOUT_SECONDS`| `10`                      | Timeout para validação de assinatura           |
| `VIACEP_BASE_URL`             | `https://viacep.com.br/ws`| URL base do ViaCEP                             |
| `VIACEP_TIMEOUT_SECONDS`      | `10`                      | Timeout para consulta de endereço por CEP      |

---

## Dados de Seed

Criados automaticamente na primeira inicialização do Subscription Service:

| Usuário          | Senha     | Plano   | Status da Assinatura |
|------------------|-----------|---------|----------------------|
| `doctor_basic`   | `senha123`| BASIC   | ACTIVE               |
| `doctor_premium` | `senha123`| PREMIUM | ACTIVE               |

Planos disponíveis:

| Plano   | Preço Mensal |
|---------|-------------|
| BASIC   | R$ 29,90    |
| PREMIUM | R$ 79,90    |

---

## Fluxo de Autenticação

```
Hospital                    Middleware              Subscription Service
   │                            │                          │
   │  POST /pedidos             │                          │
   │  Authorization: Basic ...  │                          │
   │ ─────────────────────────► │                          │
   │                            │  POST /auth/login        │
   │                            │  { username, password }  │
   │                            │ ────────────────────────►│
   │                            │                          │
   │                            │  { access_token,         │
   │                            │    plan,                 │
   │                            │    subscription_status } │
   │                            │ ◄────────────────────────│
   │                            │                          │
   │                            │  Valida status           │
   │                            │  Aplica regras           │
   │                            │  Encaminha à Farmácia    │
   │                            │                          │
   │  Resposta unificada        │                          │
   │ ◄─────────────────────────│                          │
```

---

## Regras de Negócio

| Status da Assinatura | Comportamento                                      |
|----------------------|----------------------------------------------------|
| `ACTIVE` + PREMIUM   | Pedido processado com desconto configurável        |
| `ACTIVE` + BASIC     | Pedido processado sem desconto                     |
| `EXPIRED`            | HTTP 403 — acesso negado                           |
| `CANCELED`           | HTTP 403 — acesso negado                           |

O percentual de desconto PREMIUM é configurável via `PREMIUM_DISCOUNT_PERCENT` no `.env` do Middleware.

---

## Endpoints

### Subscription Service (porta 8000)

| Método | Endpoint                          | Descrição                              |
|--------|-----------------------------------|----------------------------------------|
| POST   | `/auth/login`                     | Autenticar usuário, retorna JWT + plano|
| POST   | `/users`                          | Criar usuário                          |
| GET    | `/users/{id}`                     | Buscar usuário por ID                  |
| GET    | `/plans`                          | Listar planos                          |
| POST   | `/plans`                          | Criar plano                            |
| GET    | `/subscriptions/{user_id}`        | Buscar assinatura do usuário           |
| POST   | `/subscriptions`                  | Criar assinatura                       |
| PUT    | `/subscriptions/{subscription_id}`| Atualizar status da assinatura         |
| POST   | `/payments`                       | Registrar pagamento                    |
| GET    | `/payments/{user_id}`             | Listar pagamentos do usuário           |
| GET    | `/health`                         | Health check                           |

Documentação interativa: http://localhost:8000/docs

### Middleware (porta 3000)

| Método | Endpoint          | Descrição                                    |
|--------|-------------------|----------------------------------------------|
| POST   | `/pedidos`        | Receber prescrição do Hospital               |
| GET    | `/orders/{id}`    | Buscar pedido registrado por ID              |
| GET    | `/health`         | Health check                                 |

Documentação interativa: http://localhost:3000/docs

### Farmácia (porta 3001)

| Método | Endpoint            | Descrição                                    |
|--------|---------------------|----------------------------------------------|
| POST   | `/pedidos`          | Processar pedido, validar assinatura e CEP   |
| GET    | `/pedidos/{order_id}` | Buscar pedido processado por ID            |
| GET    | `/health`           | Health check                                 |

Documentação interativa: http://localhost:3001/docs

---

## Exemplos de Requisição

### Login no Subscription Service

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "doctor_premium", "password": "senha123"}'
```

Resposta:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user_id": 2,
  "plan": "PREMIUM",
  "subscription_status": "ACTIVE"
}
```

### Enviar Prescrição via Middleware (como o Hospital faz)

```bash
curl -X POST http://localhost:3000/pedidos \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic ZG9jdG9yX3ByZW1pdW06c2VuaGExMjM=" \
  -d '{
    "paciente_nome": "João Silva",
    "paciente_cep": "01310100",
    "medicamento": "Dipirona 500mg"
  }'
```

Resposta (com Farmácia disponível):
```json
{
  "order_id": "uuid-aqui",
  "status": "Pedido processado",
  "plano_medico": "PREMIUM",
  "discount_applied": true,
  "discount_percent": 10.0,
  "pharmacy_response": {
    "status": "Pedido processado",
    "plano_medico": "PREMIUM",
    "endereco_entrega": {
      "logradouro": "Av. Paulista",
      "bairro": "Bela Vista",
      "localidade": "São Paulo",
      "uf": "SP"
    }
  },
  "processed_at": "2024-01-01T12:00:00"
}
```

Resposta (com Farmácia indisponível — comportamento atual):
```json
{
  "order_id": "uuid-aqui",
  "status": "Farmácia indisponível — pedido registrado para reprocessamento",
  "plano_medico": "PREMIUM",
  "discount_applied": true,
  "discount_percent": 10.0,
  "pharmacy_response": {
    "status": "Farmácia indisponível — pedido registrado para reprocessamento",
    "plano_medico": "PREMIUM",
    "endereco_entrega": null
  },
  "processed_at": "2024-01-01T12:00:00"
}
```

### Credenciais inválidas

```bash
curl -X POST http://localhost:3000/pedidos \
  -H "Authorization: Basic dXNlcjplcnJhZG8=" \
  -d '{"paciente_nome": "X", "paciente_cep": "01310100", "medicamento": "Y"}'
```

Resposta HTTP 401:
```json
{ "detail": "Invalid credentials" }
```

---

## Contrato da Farmácia (para o desenvolvedor da Farmácia)

A Farmácia deve implementar o seguinte endpoint:

**`POST /pedidos`** — porta 3001

### Request Body

```json
{
  "paciente_nome": "string",
  "paciente_cep":  "string (8 dígitos, sem hífen)",
  "medicamento":   "string",
  "plano_medico":  "BASIC | PREMIUM"
}
```

### Response (HTTP 200 ou 201)

```json
{
  "status": "Pedido processado",
  "plano_medico": "BASIC | PREMIUM",
  "endereco_entrega": {
    "logradouro": "string",
    "bairro":     "string",
    "localidade": "string",
    "uf":         "string"
  }
}
```

### Códigos de Erro Esperados

| Status | Significado                        |
|--------|------------------------------------|
| 422    | Payload inválido                   |
| 500    | Erro interno da Farmácia           |
| 503    | Farmácia indisponível              |

A autenticação **não é responsabilidade da Farmácia** — o Middleware já validou as credenciais antes de encaminhar o pedido.

---

## Tratamento de Erros

Todos os serviços retornam erros no formato padronizado:

```json
{ "detail": "Mensagem descritiva do erro" }
```

| Status | Situação                                              |
|--------|-------------------------------------------------------|
| 401    | Credenciais inválidas                                 |
| 403    | Assinatura expirada ou cancelada                      |
| 404    | Recurso não encontrado                                |
| 422    | Erro de validação do payload                          |
| 500    | Erro interno                                          |
| 503    | Serviço downstream indisponível                       |

---

## Notas de Desenvolvimento

- O Subscription Service usa **SQLite** — o arquivo `subscription.db` é criado automaticamente.
- O Middleware mantém os pedidos em **memória** (dict Python). Em produção, substituir por banco de dados.
- A Farmácia ainda não está implementada. O Middleware trata a indisponibilidade graciosamente, retornando HTTP 202 com status descritivo.
- Nenhum segredo está hardcoded — tudo vem de variáveis de ambiente via `.env`.
