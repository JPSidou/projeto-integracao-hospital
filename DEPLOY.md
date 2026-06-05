# Deploy dos Serviços

Este projeto é um monorepo com quatro aplicações independentes. Em plataformas como Render, Railway, Fly ou Heroku-like, cada aplicação deve subir como um serviço separado e escutar na variável de ambiente `PORT`.

## Subscription

- Build command: `pip install -r subscription/requirements.txt`
- Start command: `./subscription/start.sh`
- Health check: `/health`
- Variáveis: veja `subscription/.env.example`

## Farmácia

- Build command: `pip install -r farmacia/requirements.txt`
- Start command: `./farmacia/start.sh`
- Health check: `/health`
- Variáveis:
  - `SUBSCRIPTION_SERVICE_URL`: URL pública do Subscription, sem barra final
  - demais variáveis em `farmacia/.env.example`

## Middleware

- Build command: `pip install -r middleware/requirements.txt`
- Start command: `./middleware/start.sh`
- Health check: `/health`
- Variáveis:
  - `SUBSCRIPTION_SERVICE_URL`: URL pública do Subscription, sem barra final
  - `PHARMACY_URL`: URL pública da Farmácia, sem barra final
  - demais variáveis em `middleware/.env.example`

## Hospital

- Build command: `pip install -r hospital/requirements.txt`
- Start command: `./hospital/start.sh`
- Health check: use a rota raiz do Streamlit
- Variáveis:
  - `MIDDLEWARE_URL`: URL pública do Middleware, sem barra final

## Ordem recomendada

1. Faça deploy do `subscription`.
2. Configure a URL pública do `subscription` em `farmacia` e `middleware`.
3. Faça deploy da `farmacia`.
4. Configure a URL pública da `farmacia` em `middleware`.
5. Faça deploy do `middleware`.
6. Configure a URL pública do `middleware` em `hospital`.
7. Faça deploy do `hospital`.

Se todos os serviços retornarem 502, confira primeiro os logs de start. Os casos mais comuns são comando apontando para a pasta errada, aplicação escutando em porta fixa em vez de `$PORT`, ou serviço escutando em `localhost` em vez de `0.0.0.0`.
