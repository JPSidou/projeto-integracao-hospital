# Middleware Service

Orquestrador central do sistema de integração hospitalar.  
Recebe prescrições do Hospital, valida assinaturas, aplica regras de negócio e encaminha pedidos para a Farmácia.

## Portas e URLs

- **Porta:** 3000  
- **Docs:** http://localhost:3000/docs

## Como Rodar

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 3000 --reload
```

O Subscription Service deve estar rodando antes de iniciar o Middleware.

## Endpoints

| Método | Endpoint       | Descrição                          |
|--------|----------------|------------------------------------|
| POST   | `/pedidos`     | Receber prescrição do Hospital     |
| GET    | `/orders/{id}` | Buscar pedido por ID               |
| GET    | `/health`      | Health check                       |

## Pharmacy Adapter

A integração com a Farmácia está encapsulada em `adapters/pharmacy_adapter.py`.  
O middleware envia o payload do pedido com `plano_medico` e `user_id` para a Farmácia validar assinatura no Subscription Service.

Contrato esperado da Farmácia: `POST http://localhost:3001/pedidos`
