import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
from datetime import date
import hashlib

# Configuração de Página
st.set_page_config(page_title="Gestão de Vendas Lucas", layout="wide")

# CSS Profissional
st.markdown("""
<style>
    .main {padding: 2rem;}
    .stMetric {background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    .stTabs [data-baseweb="tab"] {font-weight: bold; font-size: 16px;}
</style>
""", unsafe_allow_html=True)

# Nome da sua planilha (ajuste se necessário)
SHEET_NAME = "Vendas Lucas"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@st.cache_resource
def load_sheets():
    """Função blindada para carregar credenciais do Google Cloud"""
    try:
        # 1. Busca os dados dos Secrets
        creds_info = dict(st.secrets["gcp_service_account"])
        
        # 2. Limpeza profunda da Private Key (Remove escapes e espaços extras)
        raw_key = creds_info["private_key"]
        cleaned_key = raw_key.replace("\\n", "\n").replace("\\\n", "\n").strip()
        
        # 3. Garante que as bordas da chave existam (Indispensável para Governança)
        if "-----BEGIN PRIVATE KEY-----" not in cleaned_key:
            cleaned_key = f"-----BEGIN PRIVATE KEY-----\n{cleaned_key}"
        if "-----END PRIVATE KEY-----" not in cleaned_key:
            cleaned_key = f"{cleaned_key}\n-----END PRIVATE KEY-----"
            
        creds_info["private_key"] = cleaned_key
        
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        gc = gspread.authorize(creds)
        
        # 4. Tenta abrir a planilha
        return gc.open(SHEET_NAME)
    except Exception as e:
        st.error(f"Erro crítico de conexão: {str(e)}")
        return None

# Estado da Sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None

# App Principal
sh = load_sheets()

if not st.session_state.logged_in:
    st.title("🚀 Login - Sistema de Vendas")
    with st.form("login"):
        user = st.text_input("Usuário")
        pw = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            if sh:
                try:
                    ws_users = sh.worksheet("usuarios")
                    users = pd.DataFrame(ws_users.get_all_records())
                    hashed_pw = hash_password(pw)
                    match = users[(users['Usuario'] == user) & (users['Senha'] == hashed_pw)]
                    if not match.empty:
                        st.session_state.logged_in = True
                        st.session_state.user_role = match.iloc[0]['Role']
                        st.success("Acesso autorizado!")
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")
                except:
                    st.error("Erro ao ler tabela de usuários. Verifique se a aba 'usuarios' existe.")
            else:
                st.error("Servidor indisponível. Verifique os Secrets.")
else:
    # Sidebar com Logout
    st.sidebar.success(f"Logado como: {st.session_state.user_role}")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.logged_in = False
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["📝 Cadastro", "📋 Listagem", "📊 Relatórios"])

    with tab1:
        st.subheader("Nova Venda")
        with st.form("venda_form"):
            col1, col2 = st.columns(2)
            with col1:
                est = st.text_input("Estabelecimento")
                prod = st.text_input("Produto")
            with col2:
                val = st.number_input("Valor", min_value=0.0, format="%.2f")
                forma = st.selectbox("Pagamento", ["Pix", "Dinheiro", "Cartão"])
            if st.form_submit_button("Salvar Venda"):
                if sh and est and prod:
                    sh.worksheet("Página1").append_row([est, date.today().strftime("%d/%m/%Y"), prod, val, forma, "ativa"])
                    st.success("Venda registrada!")
                else:
                    st.error("Preencha todos os campos.")

    with tab2:
        st.subheader("Histórico de Vendas")
        if sh:
            vendas = pd.DataFrame(sh.worksheet("Página1").get_all_records())
            st.dataframe(vendas[vendas['Status'] == 'ativa'], use_container_width=True)

    with tab3:
        st.subheader("Dashboard")
        if sh:
            df = pd.DataFrame(sh.worksheet("Página1").get_all_records())
            if not df.empty:
                st.metric("Total de Vendas", f"R$ {pd.to_numeric(df['Valor']).sum():,.2f}")
                fig = px.pie(df, names='Estabelecimento', values='Valor', title="Vendas por Loja")
                st.plotly_chart(fig, use_container_width=True)