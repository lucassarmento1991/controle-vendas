import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib
from datetime import date

st.set_page_config(page_title="Sistema de Vendas Lucas", layout="wide")

# Inicialização do Cliente Supabase com Padronização de Governança
@st.cache_resource
def init_supabase():
    try:
        # Busca usando o caminho exato do TOML [supabase]
        url = st.secrets["supabase"]["url"].strip()
        key = st.secrets["supabase"]["key"].strip()
        return create_client(url, key)
    except KeyError as e:
        st.error(f"❌ Erro de Configuração: A chave {str(e)} não foi encontrada nos Secrets.")
        st.info("Certifique-se de que o Secret está no formato:\n\n[supabase]\nurl = '...'\nkey = '...'")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro de Conexão: {str(e)}")
        st.stop()

supabase: Client = init_supabase()

# Função de Teste de Conexão (Botão na Sidebar)
if st.sidebar.button("🧪 Testar Link com Banco"):
    try:
        # Testa se a tabela usuarios responde
        res = supabase.table("usuarios").select("count", count="exact").limit(1).execute()
        st.sidebar.success(f"✅ Conexão Ativa! Total de usuários: {res.count}")
    except Exception as e:
        st.sidebar.error(f"❌ Falha: {str(e)}")

# Lógica de Login (Usando a coluna 'username' que criamos via SQL)
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login Administrativo")
    with st.form("login_form"):
        user_input = st.text_input("Usuário").strip()
        pass_input = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            try:
                # Busca exata pelo username
                response = supabase.table("usuarios").select("*").eq("username", user_input).execute()
                if response.data:
                    stored_hash = response.data[0]["password_hash"]
                    if hash_password(pass_input) == stored_hash:
                        st.session_state.logged_in = True
                        st.success("Acesso concedido!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("Usuário não encontrado no banco.")
            except Exception as e:
                st.error(f"Erro na consulta: {str(e)}")
else:
    st.sidebar.success(f"Conectado: {st.session_state.logged_in}")
    if st.sidebar.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()
    
    # Restante das abas de Vendas e Relatórios...
    st.write("### 💰 Bem-vindo ao Painel de Controle")
    # (Inserir aqui as abas de Cadastro e Listagem enviadas anteriormente)