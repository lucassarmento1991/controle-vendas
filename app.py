import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import hashlib
from datetime import date

st.set_page_config(page_title="App Vendas Lucas", layout="wide")

# Nome da planilha no Google Drive
SHEET_NAME = "Vendas Lucas" # Mude para o nome exato se for diferente

@st.cache_resource
def load_sheets():
    try:
        # Carrega os segredos e limpa a chave privada de caracteres de escape
        creds_info = dict(st.secrets["gcp_service_account"])
        # Limpeza para evitar o erro InvalidPadding
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n").strip()
        
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        gc = gspread.authorize(creds)
        # Abre a planilha pelo nome ou pela URL se preferir
        return gc.open(SHEET_NAME)
    except Exception as e:
        st.error(f"Erro crítico de conexão: {str(e)}")
        return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Inicialização
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

sh = load_sheets()

if not st.session_state.logged_in:
    st.title("🚀 Login - Sistema de Vendas")
    with st.form("login"):
        user = st.text_input("Usuário")
        pw = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            if sh:
                ws_users = sh.worksheet("usuarios")
                df_users = pd.DataFrame(ws_users.get_all_records())
                hashed_pw = hash_password(pw)
                match = df_users[(df_users['Usuario'] == user) & (df_users['Senha'] == hashed_pw)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.success("Acesso autorizado!")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
            else:
                st.error("Servidor indisponível. Verifique os Secrets.")
else:
    st.sidebar.success("Conectado")
    if st.sidebar.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()
    
    st.title("💰 Controle de Vendas")
    # Restante do seu código de cadastro e relatórios aqui...