import streamlit as st
import requests

# ==========================================
# CONFIGURAÇÕES DA INTEGRAÇÃO
# ==========================================
# URL base da API da Farmácia. Pode ser alterada conforme o ambiente.
URL_FARMACIA = "http://localhost:3000/pedidos"

def enviar_prescricao(usuario, senha, paciente_nome, paciente_cep, medicamento):
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
        URL_FARMACIA,
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
    elif not paciente_nome or not paciente_cep or not medicamento:
        st.warning("⚠️ Todos os campos da prescrição devem ser preenchidos.")
    else:
        # Exibe um spinner para dar feedback visual de carregamento ao usuário
        with st.spinner("Enviando prescrição para a Farmácia..."):
            try:
                # Realiza a chamada para a API
                resposta = enviar_prescricao(usuario, senha, paciente_nome, paciente_cep, medicamento)
                
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
                st.error(f"❌ Falha de Conexão: Não foi possível alcançar a API da Farmácia em `{URL_FARMACIA}`. Verifique se o serviço está rodando.")
            except requests.exceptions.Timeout:
                st.error("⏳ Tempo Limite Excedido: A API da Farmácia demorou muito para responder.")
            except Exception as e:
                st.error(f"🚨 Ocorreu um erro interno na aplicação: {str(e)}")
