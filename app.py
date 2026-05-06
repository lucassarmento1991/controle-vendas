import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib
from datetime import date

# Configuração de Página
st.set_page_config(page_title="Controle de Vendas Lucas", layout="wide")

@st.cache_resource
def init_supabase():
    try:
        # Garante a limpeza das chaves
        url = st.secrets["supabase"]["url"].strip()
        key = st.secrets["supabase"]["key"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro de Infraestrutura: {str(e)}")
        st.stop()

supabase: Client = init_supabase()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

# Interface de Login
if not st.session_state.logged_in:
    st.title("🚀 Login Administrativo")
    with st.form("login_form"):
        # Alterado para 'Usuário' para refletir o Banco de Dados
        user_input = st.text_input("Usuário (Username)").strip()
        pass_input = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            try:
                # SINCRONIA CRÍTICA: Tabela 'usuarios' e Coluna 'username'
                hashed_pw = hash_password(pass_input)
                response = supabase.table('usuarios').select('*').eq('username', user_input).execute()
                
                if response.data:
                    user_data = response.data[0]
                    # Verifica se o hash confere
                    if user_data['password_hash'] == hashed_pw:
                        st.session_state.logged_in = True
                        st.session_state.username = user_input
                        st.success("Acesso autorizado!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("Usuário não encontrado no banco de dados.")
            except Exception as e:
                st.error(f"Erro de comunicação com o banco: {str(e)}")
else:
    # App Principal (Abas de Vendas e Relatórios)
    st.sidebar.success(f"Logado como: {st.session_state.username}")
    if st.sidebar.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()
    
    # Suas abas de Vendas, Listagem e Relatórios continuam aqui...
    st.info("Sistema operando normalmente com Supabase.")