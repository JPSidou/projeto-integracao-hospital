import streamlit as st
import requests
import os

# ==========================================
# CONFIGURAÇÕES DA INTEGRAÇÃO
# ==========================================
# URL do Middleware. Em deploy, defina MIDDLEWARE_URL com a URL pública do serviço.
def get_config_value(name):
    value = os.getenv(name)
    if value:
        return value

    try:
        value = st.secrets.get(name)
    except Exception:
        value = None

    return value


def get_default_middleware_url():
    explicit_url = get_config_value("URL_FARMACIA")
    if explicit_url:
        return explicit_url

    middleware_url = get_config_value("MIDDLEWARE_URL")
    if middleware_url:
        return middleware_url

    # Em deploy, PORT geralmente existe. Nesse caso, não assumir localhost.
    if os.getenv("PORT"):
        return ""

    return "http://localhost:3000"


def build_pedidos_url(middleware_url):
    middleware_url = (middleware_url or "").strip().rstrip("/")
    if not middleware_url:
        return ""
    if middleware_url.endswith("/pedidos"):
        return middleware_url
    return f"{middleware_url}/pedidos"


DEFAULT_MIDDLEWARE_URL = get_default_middleware_url()
print(f"Hospital MIDDLEWARE_URL inicial: {DEFAULT_MIDDLEWARE_URL or '<nao configurada>'}")

def enviar_prescricao(url_pedidos, usuario, senha, paciente_nome, paciente_cep, medicamento):
    """
    Função responsável por realizar a integração via HTTP POST com a Farmácia.
    Utiliza HTTP Basic Authentication para repassar as credenciais do médico.
    """
    payload = {
        "paciente_nome": paciente_nome,
        "paciente_cep": paciente_cep,
        "medicamento": medicamento
    }
    
    # Timeout de 10 segundos para evitar que a interface trave caso a API demore
    response = requests.post(
        url_pedidos,
        json=payload,
        auth=(usuario, senha),
        timeout=10
    )
    return response

# ==========================================
# INTERFACE COM STREAMLIT
# ==========================================

# Configuração inicial da página
st.set_page_config(
    page_title="Hospital Central - Prescrição",
    page_icon="🏥",
    layout="centered"
)

st.title("🏥 Hospital Central - Sistema de Prescrição Médica")

# ------------------------------------------
# Barra Lateral: Credenciais do Médico
# ------------------------------------------
st.sidebar.header("Credenciais do Médico")
st.sidebar.info("Por favor, informe seu usuário e senha para autorizar o envio.")

usuario = st.sidebar.text_input("Usuário")
senha = st.sidebar.text_input("Senha", type="password")

st.sidebar.header("Integração")
middleware_url = st.sidebar.text_input(
    "URL do Middleware",
    value=DEFAULT_MIDDLEWARE_URL,
    placeholder="https://dominio-do-middleware",
)
url_pedidos = build_pedidos_url(middleware_url)

if url_pedidos:
    st.sidebar.caption(f"Destino: {url_pedidos}")
else:
    st.sidebar.warning("Informe a URL pública do Middleware.")

# ------------------------------------------
# Corpo Principal: Formulário de Prescrição
# ------------------------------------------
st.markdown("Preencha os dados abaixo para gerar uma nova prescrição e enviá-la para a Farmácia.")

# O uso do st.form garante que a página não será recarregada a cada tecla digitada
with st.form("form_prescricao"):
    st.subheader("Nova Prescrição")
    
    paciente_nome = st.text_input("Nome do Paciente")
    paciente_cep = st.text_input("CEP do Paciente", max_chars=8, help="Digite apenas os números, sem hífen.")
    medicamento = st.text_input("Medicamento Prescrito")
    
    # O botão de submissão do formulário
    submitted = st.form_submit_button("Enviar Prescrição para a Farmácia")

# ------------------------------------------
# Lógica de Processamento e Integração
# ------------------------------------------
if submitted:
    # Validações locais antes de disparar a requisição
    if not usuario or not senha:
        st.warning("⚠️ Informe o Usuário e a Senha na barra lateral antes de enviar.")
    elif not url_pedidos:
        st.warning("⚠️ Informe a URL pública do Middleware na barra lateral antes de enviar.")
    elif not paciente_nome or not paciente_cep or not medicamento:
        st.warning("⚠️ Todos os campos da prescrição devem ser preenchidos.")
    else:
        # Exibe um spinner para dar feedback visual de carregamento ao usuário
        with st.spinner("Enviando prescrição para a Farmácia..."):
            try:
                # Realiza a chamada para a API
                resposta = enviar_prescricao(url_pedidos, usuario, senha, paciente_nome, paciente_cep, medicamento)
                
                # Trata os possíveis retornos da API
                if resposta.status_code in (200, 201):
                    # Sucesso
                    st.success("✅ Prescrição enviada com sucesso!")
                    st.markdown("### Resposta da Farmácia:")
                    # Exibe o JSON de resposta formatado, contendo os dados de entrega (ViaCEP) e plano do médico
                    st.json(resposta.json())
                    
                elif resposta.status_code == 401:
                    # Erro de autenticação específico
                    st.error("❌ Acesso Negado (401 Unauthorized): As Credenciais do Médico são inválidas no Sistema de Contas.")
                    
                else:
                    # Outros erros mapeados pela API
                    st.error(f"⚠️ A Farmácia retornou um erro (Status {resposta.status_code}).")
                    try:
                        st.json(resposta.json())
                    except ValueError:
                        st.text(resposta.text)
                        
            # Tratamento de exceções de rede e infraestrutura
            except requests.exceptions.ConnectionError:
                st.error(f"❌ Falha de Conexão: Não foi possível alcançar o Middleware em `{url_pedidos}`. Verifique a URL pública do Middleware.")
            except requests.exceptions.Timeout:
                st.error("⏳ Tempo Limite Excedido: A API da Farmácia demorou muito para responder.")
            except Exception as e:
                st.error(f"🚨 Ocorreu um erro interno na aplicação: {str(e)}")
