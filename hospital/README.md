# 🏥 Módulo Hospital (Emissor de Prescrições)

Este é o sistema frontend/cliente do nosso projeto de integração da AV3, desenvolvido em **Python + Streamlit**. Ele simula a interface que o médico usa para autenticar sua conta e enviar uma prescrição médica para o sistema da Farmácia.

---

## 🔌 Contrato de Integração (Para os Desenvolvedores da Farmácia e Contas)

Para que os nossos 3 sistemas funcionem de forma consistente, os módulos da **Farmácia** e de **Contas** devem seguir estritamente as especificações abaixo.

### 1. Endpoint de Destino
O Hospital faz um disparo via **HTTP POST** para a Farmácia no seguinte endereço (atualmente local, configurável no código):
* **URL:** `http://localhost:3000/pedidos`

### 2. Cabeçalho de Autenticação (HTTP Basic Auth)
O Hospital **não sabe** qual é o plano do médico (VIP ou Basic) e não valida a senha localmente. Ele injeta as credenciais digitadas pelo médico direto no Header da requisição utilizando **Basic Authentication**.

* **Header enviado:** `Authorization: Basic <credenciais_em_base64>`
* **O que a Farmácia deve fazer:** Pegar esse Header, extrair o usuário/senha e repassar para o **Sistema de Contas** validar.

### 3. Corpo da Requisição (Payload JSON)
Quando o médico clica em enviar, o Hospital dispara exatamente este formato de JSON:

```json
{
  "paciente_nome": "Nome do Paciente",
  "paciente_cep": "12345678",
  "medicamento": "Nome do Remédio"
}

4. Respostas que a Farmácia DEVE retornar
O código do Hospital está programado para reagir aos seguintes Status Codes vindos da Farmácia:

Status 200 ou 201 (Sucesso): Significa que o Sistema de Contas validou o médico e a Farmácia processou o pedido. A Farmácia deve responder com um JSON contendo os dados do endereço (vindos da integração com o ViaCEP) e o tipo de plano do médico. Exemplo de retorno esperado:

JSON
{
  "status": "Pedido processado",
  "plano_medico": "VIP",
  "endereco_entrega": {
    "logradouro": "Av. Paulista",
    "bairro": "Bela Vista",
    "localidade": "São Paulo",
    "uf": "SP"
  }
}
Status 401 (Unauthorized): A Farmácia deve retornar este status caso o Sistema de Contas informe que o usuário ou a senha do médico estão incorretos. O Hospital exibirá um alerta vermelho de "Acesso Negado".

Status 500 / 404 (Erros gerais): O Hospital exibirá o erro bruto na tela para fins de debug.

🚀 Como Rodar este Módulo (Para Testes)
Se você quiser rodar o sistema do Hospital na sua máquina para testar a integração com o seu backend:

Certifique-se de ter o Python instalado.

Instale as dependências necessárias:

Bash
pip install streamlit requests
Execute o servidor do Streamlit:

Bash
streamlit run app.py
A interface abrirá automaticamente no seu navegador no endereço http://localhost:8501.



