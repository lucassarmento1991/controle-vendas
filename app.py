import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import hashlib

st.set_page_config(page_title="Vendas Lucas", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .reportview-container {background: linear-gradient(to right, #f0f2f6, #e0e6ff);}
    .main .block-container {padding-top: 2rem;}
    .stTabs [data-baseweb="tab-list"] {gap: 10px;}
    .stTabs [data-baseweb="tab"] {height: 50px; white-space: pre-wrap; font-weight: bold; border-radius: 10px 10px 0 0;}
    .stMetric {background-color: rgba(255,255,255,0.8); border-radius: 10px; padding: 1rem;}
</style>
""", unsafe_allow_html=True)

SHEET_NAME = "Vendas Lucas"

@st.cache_resource
def load_sheets():
    try:
        creds_info = st.secrets["gcp_service_account"]
        private_key = creds_info["private_key"].replace("\\n", "\n").strip()
        creds_info["private_key"] = private_key
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        gc = gspread.authorize(creds)
        sheet = gc.open(SHEET_NAME)
        return sheet
    except Exception as e:
        st.error(f"Erro ao carregar planilhas: {str(e)}")
        return None

def get_sheet():
    if 'sheet' not in st.session_state:
        st.session_state.sheet = load_sheets()
    return st.session_state.sheet

def get_active_df(pagina1_ws):
    all_values = pagina1_ws.get_all_values()
    if len(all_values) <= 1:
        return pd.DataFrame()
    headers = all_values[0]
    df = pd.DataFrame(all_values[1:], columns=headers)
    numeric_cols = ['Quantidade', 'Valor_Unitario', 'Total']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
    active_df = df[df['Status'] == 'ativa'].copy()
    return active_df.reset_index(drop=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.sheet = None

st.title("🚀 App Vendas Lucas")

if not st.session_state.logged_in:
    st.subheader("Login")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        usuario = st.text_input("Usuário")
    with col2:
        senha = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        sheet = get_sheet()
        if sheet:
            try:
                usuarios_ws = sheet.worksheet('usuarios')
                data_users = usuarios_ws.get_all_records()
                if data_users:
                    df_users = pd.DataFrame(data_users)
                    senha_hash = hashlib.sha256(senha.encode('utf-8')).hexdigest()
                    match = df_users[(df_users['Usuario'] == usuario) & (df_users['Senha'] == senha_hash)]
                    if not match.empty:
                        st.session_state.logged_in = True
                        st.session_state.username = usuario
                        st.session_state.role = match.iloc[0]['Role']
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha inválidos.")
                else:
                    st.error("Nenhum usuário encontrado na planilha 'usuarios'.")
            except Exception as e:
                st.error(f"Erro no login: {str(e)}")
        else:
            st.error("Falha ao conectar com as planilhas.")
else:
    # Sidebar
    with st.sidebar:
        st.info(f"👤 Usuário: {st.session_state.username}\n📋 Role: {st.session_state.role}")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.role = None
            st.session_state.sheet = None
            st.rerun()

    sheet = get_sheet()
    if not sheet:
        st.stop()

    pagina1_ws = sheet.worksheet('Página1')

    tab1, tab2, tab3 = st.tabs(["📝 Cadastro de Vendas", "📋 Listagem e Cancelamento", "📊 Relatórios"])

    with tab1:
        st.subheader("Nova Venda")
        col1, col2 = st.columns(2)
        with col1:
            estabelecimento = st.text_input("Estabelecimento")
            data_venda = st.date_input("Data", value=date.today())
            produto = st.text_input("Produto")
            quantidade = st.number_input("Quantidade", min_value=0.01, step=1.0, format="%.2f")
        with col2:
            valor_unitario = st.number_input("Valor Unitário", min_value=0.01, format="%.2f")
            total_calc = quantidade * valor_unitario
            st.number_input("Total", value=total_calc, disabled=True, format="%.2f")
            forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Pix", "Cartão", "Boleto"])
            vendedor = st.text_input("Vendedor")
        cliente = st.text_input("Cliente")
        observacoes = st.text_area("Observações", height=80)

        if st.button("💾 Cadastrar Venda", use_container_width=True):
            if estabelecimento and produto and vendedor and cliente:
                data_str = data_venda.strftime('%d/%m/%Y')
                total = total_calc
                row = [
                    estabelecimento, data_str, produto, quantidade, valor_unitario,
                    total, forma_pagamento, vendedor, cliente, 'ativa', observacoes
                ]
                pagina1_ws.append_row(row)
                st.success("✅ Venda cadastrada com sucesso!")
                st.rerun()
            else:
                st.error("❌ Preencha todos os campos obrigatórios (Estabelecimento, Produto, Vendedor, Cliente).")

    with tab2:
        st.subheader("Vendas Ativas")
        active_df = get_active_df(pagina1_ws)
        if active_df.empty:
            st.info("Nenhuma venda ativa.")
        else:
            st.dataframe(active_df, use_container_width=True)
            idx = st.selectbox(
                "Selecione venda para cancelar:",
                range(len(active_df)),
                format_func=lambda i: f"Linha {i+2}: {active_df.iloc[i]['Estabelecimento']} - {active_df.iloc[i]['Produto']} (R$ {active_df.iloc[i]['Total']:.2f})"
            )
            if st.button("🗑️ Confirmar Cancelamento", use_container_width=True):
                row_num = idx + 2
                pagina1_ws.update(f'J{row_num}', 'cancelada')
                st.success("✅ Venda cancelada com sucesso!")
                st.rerun()

    with tab3:
        st.subheader("Dashboard - Vendas Ativas")
        active_df = get_active_df(pagina1_ws)
        if active_df.empty:
            st.info("Nenhuma venda ativa para relatórios.")
            st.stop()

        col1, col2, col3, col4 = st.columns(4)
        total_vendas = len(active_df)
        total_valor = active_df['Total'].sum()
        avg_ticket = total_valor / total_vendas if total_vendas > 0 else 0
        top_est = active_df['Estabelecimento'].value_counts().index[0] if len(active_df) > 0 else 'N/A'

        col1.metric("📦 Total Vendas", total_vendas)
        col2.metric("💰 Valor Total", f"R$ {total_valor:.2f}")
        col3.metric("🎫 Ticket Médio", f"R$ {avg_ticket:.2f}")
        col4.metric("🏆 Top Estabelecimento", top_est)

        col_a, col_b = st.columns(2)
        with col_a:
            fig_pie = px.pie(active_df, names='Estabelecimento', values='Total', title="Distribuição por Estabelecimento")
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_b:
            fig_bar_prod = px.bar(
                active_df.groupby('Produto')['Total'].sum().reset_index(),
                x='Produto', y='Total',
                title="Vendas por Produto"
            )
            st.plotly_chart(fig_bar_prod, use_container_width=True)

        fig_bar_vend = px.bar(
            active_df.groupby('Vendedor')['Total'].sum().reset_index(),
            x='Vendedor', y='Total',
            title="Vendas por Vendedor"
        )
        st.plotly_chart(fig_bar_vend, use_container_width=True)

        if 'Data' in active_df.columns and not active_df['Data'].isna().all():
            daily_sales = active_df.groupby(active_df['Data'].dt.date)['Total'].sum().reset_index()
            fig_line = px.line(daily_sales, x='Data', y='Total', title="Evolução de Vendas por Data")
            st.plotly_chart(fig_line, use_container_width=True)