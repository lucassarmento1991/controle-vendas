import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import datetime

st.set_page_config(page_title="App Vendas", page_icon="💰", layout="wide")

# Professional CSS
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: normal;
        font-size: 16px;
        font-weight: bold;
    }
    .stMetric > label {
        color: #1f77b4;
        font-size: 18px;
    }
    .stMetric > div > div {
        font-size: 28px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_supabase():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase: Client = init_supabase()

# Session state
if 'user' not in st.session_state:
    st.session_state.user = None


def login(email: str, senha: str) -> bool:
    try:
        response = supabase.table('usuarios').select('*').eq('email', email).execute()
        if response.data and response.data[0]['senha'] == senha:
            st.session_state.user = response.data[0]
            st.success("Login realizado com sucesso!")
            st.rerun()
            return True
        else:
            st.error("Email ou senha incorretos.")
            return False
    except Exception as e:
        st.error(f"Erro no login: {str(e)}")
        return False


def register_venda(data: dict) -> bool:
    try:
        supabase.table("vendas").insert(data).execute()
        st.success("Venda cadastrada com sucesso!")
        st.rerun()
        return True
    except Exception as e:
        st.error(f"Erro ao cadastrar venda: {str(e)}")
        return False


def get_vendas(usuario_id: int = None, status: str = None) -> pd.DataFrame:
    try:
        query = supabase.table('vendas').select('*').order('data', desc=True)
        if usuario_id:
            query = query.eq('usuario_id', usuario_id)
        if status:
            query = query.eq('status', status)
        response = query.execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erro ao buscar vendas: {str(e)}")
        return pd.DataFrame()

# Main tabs
st.title("💰 Sistema de Vendas")
tab1, tab2, tab3, tab4 = st.tabs(["🔐 Login", "➕ Cadastro Venda", "📋 Listagem", "📊 Relatórios"])

with tab1:
    st.header("Login no Sistema")
    col1, col2 = st.columns([3, 1])
    with col1:
        email = st.text_input("Email", placeholder="seu@email.com")
    with col2:
        senha = st.text_input("Senha", type="password")
    if st.button("Entrar", type="primary"):
        login(email, senha)
    
    if st.session_state.user:
        st.success(f"Bem-vindo, {st.session_state.user.get('nome', 'Usuário')}!")
        if st.button("Sair", type="secondary"):
            st.session_state.user = None
            st.rerun()

with tab2:
    st.header("Cadastro de Nova Venda")
    if not st.session_state.user:
        st.warning("👈 Faça login primeiro na aba Login!")
    else:
        col1, col2 = st.columns(2)
        with col1:
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            produto = st.text_input("Produto/Serviço")
        with col2:
            data_venda = st.date_input("Data", value=datetime.now().date())
        
        if st.button("Cadastrar Venda", type="primary"):
            if valor > 0 and produto:
                data = {
                    "usuario_id": st.session_state.user['id'],
                    "valor": float(valor),
                    "produto": produto,
                    "data": data_venda.isoformat(),
                    "status": "ativa"
                }
                register_venda(data)
            else:
                st.error("Preencha todos os campos corretamente.")

with tab3:
    st.header("Listagem e Filtros de Vendas")
    if not st.session_state.user:
        st.warning("👈 Faça login primeiro na aba Login!")
    else:
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox("Filtrar por Status", ["Todas", "ativa", "concluida"])
        with col2:
            search_produto = st.text_input("Buscar por Produto")
        
        status = None if status_filter == "Todas" else status_filter
        df = get_vendas(st.session_state.user['id'], status)
        
        if search_produto:
            df = df[df['produto'].str.contains(search_produto, case=False, na=False)]
        
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma venda encontrada.")

with tab4:
    st.header("Dashboards e Relatórios")
    if not st.session_state.user:
        st.warning("👈 Faça login primeiro na aba Login!")
    else:
        df = get_vendas(st.session_state.user['id'])
        if df.empty:
            st.info("Nenhuma venda para relatórios.")
        else:
            df['data'] = pd.to_datetime(df['data'])
            df['mes'] = df['data'].dt.to_period('M')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                total_vendas = df['valor'].sum()
                st.metric("Total Vendas", f"R$ {total_vendas:,.2f}")
            with col2:
                vendas_ativas = len(df[df['status'] == 'ativa'])
                st.metric("Vendas Ativas", vendas_ativas)
            with col3:
                avg_valor = df['valor'].mean()
                st.metric("Ticket Médio", f"R$ {avg_valor:,.2f}")
            
            col_chart, pie_chart = st.columns(2)
            with col_chart:
                fig_bar = px.bar(df, x='data', y='valor', color='status',
                                 title="Vendas por Data",
                                 color_discrete_map={'ativa': '#1f77b4', 'concluida': '#ff7f0e'})
                st.plotly_chart(fig_bar, use_container_width=True)
            with pie_chart:
                fig_pie = px.pie(df, values='valor', names='status', title="Distribuição por Status")
                st.plotly_chart(fig_pie, use_container_width=True)
            
            # Line chart por mês
            monthly = df.groupby('mes')['valor'].sum().reset_index()
            monthly['mes'] = monthly['mes'].astype(str)
            fig_line = px.line(monthly, x='mes', y='valor', title="Vendas Mensais")
            st.plotly_chart(fig_line, use_container_width=True)