# Projeto de Integracao Hospitalar

Sistema distribuido para integrar uma interface hospitalar de prescricoes medicas com um servico de assinaturas, um middleware orquestrador e uma farmacia integrada ao ViaCEP.

O objetivo do projeto e demonstrar um fluxo completo de integracao entre sistemas independentes: o medico envia uma prescricao pelo Hospital, o Middleware autentica o usuario no Subscription Service, valida a assinatura, aplica regras de negocio e encaminha o pedido para a Farmacia, que consulta o endereco de entrega pelo CEP.

## Descricao Tecnica e Arquitetura

A aplicacao e composta por quatro servicos executados separadamente:

| Servico | Porta | Responsabilidade |
| --- | ---: | --- |
| Hospital | 8501 | Interface web em Streamlit usada pelo medico para enviar prescricoes. |
| Middleware | 3000 | API central que recebe pedidos, autentica credenciais, valida assinatura, aplica regras de negocio e integra com a Farmacia. |
| Subscription Service | 8000 | API de usuarios, planos, assinaturas, pagamentos e autenticacao JWT. |
| Farmacia | 3001 | API que processa pedidos, revalida assinatura quando recebe `user_id` e consulta endereco no ViaCEP. |

Fluxo arquitetural:

```text
Hospital (Streamlit)
    |
    | POST /pedidos
    | Authorization: Basic <base64(usuario:senha)>
    v
Middleware (FastAPI)
    |
    | POST /auth/login
    v
Subscription Service (FastAPI + SQLite)
    |
    | retorna user_id, plano e status da assinatura
    v
Middleware
    |
    | aplica regra BASIC/PREMIUM
    | POST /pedidos
    v
Farmacia (FastAPI)
    |
    | GET ViaCEP /{cep}/json/
    v
Resposta unificada para o Hospital
```

Principais decisoes de arquitetura:

- O Hospital nao acessa diretamente o Subscription Service nem a Farmacia; ele se integra apenas ao Middleware.
- O Middleware e o ponto de orquestracao e concentracao das regras de negocio do fluxo de prescricao.
- O Subscription Service persiste dados em SQLite usando SQLAlchemy e cria dados iniciais automaticamente no startup.
- A Farmacia armazena pedidos em memoria e consulta o ViaCEP para enriquecer o pedido com endereco de entrega.
- O Middleware tambem armazena pedidos em memoria para permitir consulta por `GET /orders/{order_id}`.
- As configuracoes externas ficam em arquivos `.env`, com exemplos versionados em `.env.example`.

## Estrutura do Repositorio

```text
projeto-integracao-hospital/
|-- hospital/
|   |-- app.py
|   |-- requirements.txt
|   `-- README.md
|-- middleware/
|   |-- adapters/
|   |   `-- pharmacy_adapter.py
|   |-- app.py
|   |-- config.py
|   |-- subscription_client.py
|   |-- requirements.txt
|   |-- .env.example
|   `-- README.md
|-- subscription/
|   |-- app.py
|   |-- auth.py
|   |-- database.py
|   |-- models.py
|   |-- schemas.py
|   |-- seed.py
|   |-- requirements.txt
|   |-- .env.example
|   `-- README.md
|-- farmacia/
|   |-- app.py
|   |-- subscription_client.py
|   |-- viacep_client.py
|   |-- requirements.txt
|   |-- .env.example
|   `-- README.md
|-- Projeto_Final.pdf
`-- README.md
```

## Ferramentas e Tecnologias

- Python 3.10+
- FastAPI para as APIs do Middleware, Subscription Service e Farmacia
- Uvicorn como servidor ASGI
- Streamlit para a interface do Hospital
- Requests para chamadas HTTP entre servicos
- SQLAlchemy para persistencia do Subscription Service
- SQLite como banco local do Subscription Service
- Pydantic para validacao de payloads e schemas
- python-jose para geracao de JWT
- bcrypt para hash e verificacao de senhas
- python-dotenv para variaveis de ambiente
- ViaCEP como servico externo de consulta de endereco por CEP

## Execucao Local

Pre-requisitos:

- Python 3.10 ou superior
- `pip`
- Quatro terminais, um para cada servico

Recomendado: criar um ambiente virtual para cada servico ou um ambiente virtual na raiz do projeto. Os comandos abaixo assumem execucao a partir da raiz do repositorio.

### 1. Subscription Service

```bash
cd subscription
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Ao iniciar, o servico cria automaticamente o banco `subscription/subscription.db` e executa o seed idempotente de planos, usuarios, assinaturas e pagamentos.

Documentacao interativa: http://localhost:8000/docs

### 2. Farmacia

```bash
cd farmacia
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

Documentacao interativa: http://localhost:3001/docs

### 3. Middleware

```bash
cd middleware
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 3000 --reload
```

Documentacao interativa: http://localhost:3000/docs

### 4. Hospital

```bash
cd hospital
pip install -r requirements.txt
streamlit run app.py
```

Interface web: http://localhost:8501

Ordem recomendada de inicializacao: Subscription Service, Farmacia, Middleware e Hospital.

## Implantacao

O projeto nao inclui Docker ou arquivo de orquestracao. Para implantar em outro ambiente:

1. Provisionar Python 3.10+ no servidor.
2. Instalar as dependencias de cada servico com o respectivo `requirements.txt`.
3. Criar os arquivos `.env` a partir dos `.env.example`.
4. Ajustar URLs internas:
   - `SUBSCRIPTION_SERVICE_URL`
   - `PHARMACY_URL`
   - `VIACEP_BASE_URL`, se necessario
5. Executar as APIs FastAPI com Uvicorn em processos separados.
6. Executar a interface Streamlit apontando para o Middleware.

Em producao, recomenda-se trocar `SECRET_KEY`, desativar `--reload`, persistir pedidos do Middleware/Farmacia em banco de dados e usar um gerenciador de processos ou reverse proxy.

## Variaveis de Ambiente

### `subscription/.env`

| Variavel | Padrao | Descricao |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./subscription.db` | URL do banco SQLite. |
| `SECRET_KEY` | `change-me-in-production` | Chave usada para assinar JWTs. |
| `ALGORITHM` | `HS256` | Algoritmo do JWT. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Tempo de validade do token. |
| `BASIC_PLAN_PRICE` | `29.90` | Valor de referencia do plano BASIC. |
| `PREMIUM_PLAN_PRICE` | `79.90` | Valor de referencia do plano PREMIUM. |

### `middleware/.env`

| Variavel | Padrao | Descricao |
| --- | --- | --- |
| `SUBSCRIPTION_SERVICE_URL` | `http://localhost:8000` | URL do Subscription Service. |
| `PHARMACY_URL` | `http://localhost:3001` | URL da Farmacia. |
| `SUBSCRIPTION_TIMEOUT_SECONDS` | `10` | Timeout para chamadas ao Subscription Service. |
| `PHARMACY_TIMEOUT_SECONDS` | `10` | Timeout para chamadas a Farmacia. |
| `PREMIUM_DISCOUNT_PERCENT` | `10` | Percentual de desconto aplicado a pedidos PREMIUM. |

### `farmacia/.env`

| Variavel | Padrao | Descricao |
| --- | --- | --- |
| `SUBSCRIPTION_SERVICE_URL` | `http://localhost:8000` | URL do Subscription Service para revalidacao de assinatura. |
| `SUBSCRIPTION_TIMEOUT_SECONDS` | `10` | Timeout para consultar assinatura. |
| `VIACEP_BASE_URL` | `https://viacep.com.br/ws` | URL base da API ViaCEP. |
| `VIACEP_TIMEOUT_SECONDS` | `10` | Timeout para consulta de CEP. |

## Dados Iniciais

O seed e executado automaticamente pelo Subscription Service no startup.

| Usuario | Senha | Plano | Status |
| --- | --- | --- | --- |
| `doctor_basic` | `senha123` | BASIC | ACTIVE |
| `doctor_premium` | `senha123` | PREMIUM | ACTIVE |

Planos criados:

| Plano | Preco mensal | Regra no Middleware |
| --- | ---: | --- |
| BASIC | R$ 29,90 | Fluxo padrao, sem desconto. |
| PREMIUM | R$ 79,90 | Aplica desconto configurado em `PREMIUM_DISCOUNT_PERCENT`. |

## Endpoints

### Subscription Service - porta 8000

| Metodo | Endpoint | Descricao |
| --- | --- | --- |
| `POST` | `/auth/login` | Autentica usuario e retorna JWT, `user_id`, plano e status da assinatura. |
| `POST` | `/users` | Cria usuario. |
| `GET` | `/users/{user_id}` | Busca usuario por ID. |
| `GET` | `/plans` | Lista planos. |
| `POST` | `/plans` | Cria plano. |
| `GET` | `/subscriptions/{user_id}` | Busca assinatura mais recente do usuario. |
| `POST` | `/subscriptions` | Cria assinatura. |
| `PUT` | `/subscriptions/{subscription_id}` | Atualiza status e validade da assinatura. |
| `POST` | `/payments` | Registra pagamento. |
| `GET` | `/payments/{user_id}` | Lista pagamentos de um usuario. |
| `GET` | `/health` | Verifica saude do servico. |

Payload de login:

```json
{
  "username": "doctor_premium",
  "password": "senha123"
}
```

Resposta de login:

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "user_id": 2,
  "plan": "PREMIUM",
  "subscription_status": "ACTIVE"
}
```

### Middleware - porta 3000

| Metodo | Endpoint | Descricao |
| --- | --- | --- |
| `POST` | `/pedidos` | Recebe prescricao do Hospital, autentica, valida assinatura, aplica regras e encaminha a Farmacia. |
| `GET` | `/orders/{order_id}` | Consulta pedido registrado em memoria. |
| `GET` | `/health` | Verifica saude do servico. |

Headers esperados em `POST /pedidos`:

```text
Authorization: Basic <base64(usuario:senha)>
Content-Type: application/json
```

Payload:

```json
{
  "paciente_nome": "Joao Silva",
  "paciente_cep": "01310100",
  "medicamento": "Dipirona 500mg"
}
```

Resposta de sucesso com Farmacia disponivel:

```json
{
  "order_id": "uuid",
  "status": "Pedido processado",
  "plano_medico": "PREMIUM",
  "discount_applied": true,
  "discount_percent": 10.0,
  "pharmacy_response": {
    "status": "Pedido processado",
    "plano_medico": "PREMIUM",
    "endereco_entrega": {
      "logradouro": "Avenida Paulista",
      "bairro": "Bela Vista",
      "localidade": "Sao Paulo",
      "uf": "SP"
    }
  },
  "processed_at": "2026-06-05T12:00:00"
}
```

Resposta quando a Farmacia esta indisponivel:

```json
{
  "order_id": "uuid",
  "status": "Farmácia indisponível — pedido registrado para reprocessamento",
  "plano_medico": "PREMIUM",
  "discount_applied": true,
  "discount_percent": 10.0,
  "pharmacy_response": {
    "status": "Farmácia indisponível — pedido registrado para reprocessamento",
    "plano_medico": "PREMIUM",
    "endereco_entrega": null
  },
  "processed_at": "2026-06-05T12:00:00"
}
```

### Farmacia - porta 3001

| Metodo | Endpoint | Descricao |
| --- | --- | --- |
| `POST` | `/pedidos` | Processa pedido recebido do Middleware, valida assinatura quando possivel e consulta endereco no ViaCEP. |
| `GET` | `/pedidos/{order_id}` | Consulta pedido processado em memoria. |
| `GET` | `/health` | Verifica saude do servico. |

Payload recebido do Middleware:

```json
{
  "paciente_nome": "Joao Silva",
  "paciente_cep": "01310100",
  "medicamento": "Dipirona 500mg",
  "plano_medico": "PREMIUM",
  "user_id": 2
}
```

Resposta:

```json
{
  "status": "Pedido processado",
  "plano_medico": "PREMIUM",
  "endereco_entrega": {
    "logradouro": "Avenida Paulista",
    "bairro": "Bela Vista",
    "localidade": "Sao Paulo",
    "uf": "SP"
  }
}
```

## Fluxos de Integracao

### Fluxo principal de prescricao

1. O medico abre o Hospital em `http://localhost:8501`.
2. O medico informa usuario e senha na barra lateral.
3. O medico preenche nome do paciente, CEP com 8 digitos e medicamento.
4. O Hospital envia `POST http://localhost:3000/pedidos` com Basic Auth.
5. O Middleware extrai as credenciais e chama `POST http://localhost:8000/auth/login`.
6. O Subscription Service valida senha, gera JWT e retorna plano/status da assinatura.
7. O Middleware bloqueia assinaturas `EXPIRED` ou `CANCELED`.
8. Se a assinatura for `ACTIVE`, o Middleware aplica regra BASIC/PREMIUM.
9. O Middleware encaminha o pedido para `POST http://localhost:3001/pedidos`.
10. A Farmacia revalida a assinatura via `GET /subscriptions/{user_id}` quando recebe `user_id`.
11. A Farmacia consulta o ViaCEP usando o CEP do paciente.
12. A resposta da Farmacia e incorporada a resposta final do Middleware.
13. O Hospital exibe o JSON final ao medico.

### Fluxo de indisponibilidade da Farmacia

Se a Farmacia estiver fora do ar ou exceder timeout, o Middleware nao perde o pedido. Ele registra os dados em memoria, retorna HTTP 202 e informa que o pedido foi registrado para reprocessamento.

### Fluxo de assinatura invalida

Se o Subscription Service retornar assinatura `EXPIRED`, `CANCELED` ou diferente de `ACTIVE`, o Middleware encerra o fluxo antes de chamar a Farmacia e retorna HTTP 403.

## Exemplos de Teste com `curl`

Login direto no Subscription Service:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"doctor_premium","password":"senha123"}'
```

Envio de prescricao pelo Middleware:

```bash
curl -X POST http://localhost:3000/pedidos \
  -u doctor_premium:senha123 \
  -H "Content-Type: application/json" \
  -d '{"paciente_nome":"Joao Silva","paciente_cep":"01310100","medicamento":"Dipirona 500mg"}'
```

Consulta de saude dos servicos:

```bash
curl http://localhost:8000/health
curl http://localhost:3001/health
curl http://localhost:3000/health
```

## Tratamento de Erros

| Status | Situacao |
| ---: | --- |
| 401 | Credenciais ausentes, malformadas ou invalidas. |
| 403 | Assinatura expirada, cancelada ou nao ativa. |
| 404 | Recurso nao encontrado. |
| 422 | Payload invalido, CEP invalido ou CEP nao encontrado. |
| 500 | Erro interno nao tratado. |
| 503 | Servico downstream indisponivel ou resposta inesperada. |

Formato padrao de erro:

```json
{
  "detail": "Mensagem descritiva do erro"
}
```

## Informacoes para Avaliacao

- O ponto de entrada para demonstracao funcional e a interface do Hospital em `http://localhost:8501`.
- As credenciais de teste sao `doctor_basic` / `senha123` e `doctor_premium` / `senha123`.
- O plano PREMIUM aplica desconto no Middleware; o plano BASIC segue sem desconto.
- O banco SQLite do Subscription Service e criado automaticamente e pode ser removido para reiniciar os dados locais.
- Middleware e Farmacia usam armazenamento em memoria para pedidos; ao reiniciar os processos, esses registros sao perdidos.
- A consulta de endereco depende da disponibilidade externa do ViaCEP.
- As APIs FastAPI possuem documentacao Swagger nas rotas `/docs`.
- O Hospital usa a constante `URL_FARMACIA = "http://localhost:3000/pedidos"` em `hospital/app.py`; apesar do nome, essa URL aponta para o Middleware, que e o gateway de integracao.
- Os arquivos `.env.example` indicam os valores esperados para execucao local.
