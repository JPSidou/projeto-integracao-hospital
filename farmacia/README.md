# Farmácia Service

Serviço da Farmácia do monorepo de integração hospitalar.

Ele recebe pedidos médicos do Middleware, usa o plano já validado pelo Middleware, consulta o endereço de entrega no ViaCEP e devolve uma resposta padronizada para o fluxo Hospital -> Middleware -> Farmácia.

## O que a Farmácia faz

1. Recebe prescrição em `POST /pedidos`.
1. Normaliza o plano médico para `BASIC` ou `PREMIUM`.
1. Por padrão, confia na validação de assinatura feita pelo Middleware.
1. Opcionalmente, se `REVALIDATE_SUBSCRIPTION=true`, revalida a assinatura no Subscription.
1. Consulta o ViaCEP para obter endereço pelo CEP.
1. Se o ViaCEP estiver indisponível, registra o pedido com endereço pendente em vez de derrubar o fluxo.
1. Armazena o pedido em memória para consulta posterior.
1. Retorna status final + plano + endereço de entrega.

## Porta e documentação

- Porta padrão: `3001`
- OpenAPI/Swagger: `http://localhost:3001/docs`
- Health check: `GET http://localhost:3001/health`

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

## Variáveis de ambiente

Arquivo: `.env`

| Variável                       | Padrão                      | Descrição |
|--------------------------------|-----------------------------|-----------|
| `SUBSCRIPTION_SERVICE_URL`     | `http://localhost:8000`     | URL base do serviço de assinatura |
| `SUBSCRIPTION_TIMEOUT_SECONDS` | `10`                        | Timeout da chamada ao subscription |
| `REVALIDATE_SUBSCRIPTION`      | `false`                     | Se `true`, a Farmácia revalida assinatura no Subscription. |
| `VIACEP_BASE_URL`              | `https://viacep.com.br/ws`  | URL base do ViaCEP |
| `VIACEP_TIMEOUT_SECONDS`       | `10`                        | Timeout da consulta de CEP |

## Integrações externas

1. Middleware -> Farmácia
   - `POST /pedidos`
1. Farmácia -> Subscription (opcional)
   - `GET /subscriptions/{user_id}` quando `REVALIDATE_SUBSCRIPTION=true`
1. Farmácia -> ViaCEP
   - `GET /ws/{cep}/json/`

## Endpoints

| Método | Endpoint               | Descrição |
|--------|------------------------|-----------|
| `POST` | `/pedidos`             | Processa pedido e retorna endereço |
| `GET`  | `/pedidos/{order_id}`  | Consulta pedido salvo em memória |
| `GET`  | `/health`              | Verifica disponibilidade do serviço |

## Contrato do `POST /pedidos`

### Entrada

```json
{
  "paciente_nome": "Maria Silva",
  "paciente_cep": "01001000",
  "medicamento": "Dipirona 500mg",
  "plano_medico": "PREMIUM",
  "user_id": 2
}
```

Regras dos campos:

- `paciente_nome`: obrigatório, não vazio.
- `paciente_cep`: obrigatório, 8 dígitos numéricos.
- `medicamento`: obrigatório, não vazio.
- `plano_medico`: obrigatório (`BASIC`/`PREMIUM`, normalizado internamente).
- `user_id`: opcional.

Quando `user_id` é enviado, a farmácia valida assinatura e plano no subscription.
Quando `user_id` não é enviado, o processamento segue com o plano recebido do middleware.

### Saída (201)

```json
{
  "status": "Pedido processado",
  "plano_medico": "PREMIUM",
  "endereco_entrega": {
    "logradouro": "Praça da Sé",
    "bairro": "Sé",
    "localidade": "São Paulo",
    "uf": "SP"
  }
}
```

## Regras de negócio

1. Assinatura `EXPIRED` ou `CANCELED` -> bloqueia pedido (`403`).
1. Assinatura diferente de `ACTIVE` -> bloqueia pedido (`403`).
1. CEP inválido ou inexistente -> retorna `422`.
1. Falha de comunicação com ViaCEP -> pedido é registrado com endereço pendente.
1. Falha de comunicação com subscription -> retorna `503` apenas se `REVALIDATE_SUBSCRIPTION=true`.

## Códigos de resposta esperados

- `201 Created`: pedido processado com sucesso.
- `403 Forbidden`: assinatura inválida/inativa.
- `422 Unprocessable Entity`: payload inválido ou CEP inválido/inexistente.
- `503 Service Unavailable`: subscription indisponível apenas se `REVALIDATE_SUBSCRIPTION=true`.

## Exemplos de teste com curl

### 1) Health

```bash
curl http://localhost:3001/health
```

### 2) Pedido válido

```bash
curl -X POST http://localhost:3001/pedidos \
  -H "Content-Type: application/json" \
  -d '{
    "paciente_nome":"Maria Silva",
    "paciente_cep":"01001000",
    "medicamento":"Dipirona 500mg",
    "plano_medico":"PREMIUM",
    "user_id":2
  }'
```

### 3) CEP inválido

```bash
curl -X POST http://localhost:3001/pedidos \
  -H "Content-Type: application/json" \
  -d '{
    "paciente_nome":"Maria Silva",
    "paciente_cep":"00000000",
    "medicamento":"Dipirona 500mg",
    "plano_medico":"PREMIUM",
    "user_id":2
  }'
```

## Observações técnicas

1. Os pedidos são armazenados em memória (`dict`) e se perdem ao reiniciar o serviço.
1. O serviço não autentica usuário diretamente; ele confia no middleware e no `user_id` para consulta da assinatura.
1. A integração com o middleware usa contrato JSON simples, sem fila ou broker.
