import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime

st.set_page_config(page_title="App Vendas", page_icon="📊", layout="wide")

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
    }
    .stButton > button {
        background-color: #ff4b4b;
        color: white;
        border-radius: 10px;
    }
    .stButton > button:hover {
        background-color: #ff6b6b;
    }
</style>
""", unsafe_allow_html=True)

# URL da planilha como CSV público (somente leitura)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZV0TfPigj1MvQj4dqqvYgCnQX7TNq-n5RdIS4egh5GA/export?format=csv"

# Inicialização do estado de login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Tela de login
if not st.session_state.logged_in:
    st.markdown("<h1 class='main-header'>📱 App Vendas</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        if st.button("Entrar", use_container_width=True):
            if st.session_state.username == "admin" and st.session_state.password == "123456":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos!")
    st.stop()

# Carregamento dos dados
@st.cache_data
def load_data():
    df = pd.read_csv(SHEET_URL)
    df.columns = df.columns.str.strip().str.lower()
    return df

df = load_data()

# Função para processar dados para relatórios
def process_df(df_raw):
    df = df_raw.copy()
    if 'data' in df.columns:
        df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
    if 'total' in df.columns:
        df['total'] = pd.to_numeric(df['total'].astype(str).str.replace('R\$', '', regex=False).str.replace(',', '.').str.strip(), errors='coerce')
    if 'quantidade' in df.columns:
        df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce')
    if 'valor_unitario' in df.columns:
        df['valor_unitario'] = pd.to_numeric(df['valor_unitario'].astype(str).str.replace('R\$', '', regex=False).str.replace(',', '.').str.strip(), errors='coerce')
    df = df.dropna(subset=['data', 'total'])
    return df

processed_df = process_df(df)

# Sidebar para filtros
st.sidebar.header("Filtros")
min_date = processed_df['data'].min().date() if not processed_df.empty else date.today()
max_date = processed_df['data'].max().date() if not processed_df.empty else date.today()
start_date = st.sidebar.date_input("Data Inicial", min_date, key="start_date")
end_date = st.sidebar.date_input("Data Final", max_date, key="end_date")

filtered_df = processed_df[(processed_df['data'] >= pd.to_datetime(start_date)) & (processed_df['data'] <= pd.to_datetime(end_date))]

if 'produto' in df.columns:
    produtos = sorted(df['produto'].dropna().unique())
    selected_produto = st.sidebar.multiselect("Produto", produtos, default=produtos)
    filtered_df = filtered_df[filtered_df['produto'].isin(selected_produto)] if selected_produto else filtered_df

# Cabeçalho
st.markdown("<h1 class='main-header'>📊 Dashboard de Vendas</h1>", unsafe_allow_html=True)

# Métricas
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total de Vendas", len(filtered_df), delta=None, help="Número de registros")
with col2:
    total_receita = filtered_df['total'].sum()
    st.metric("Receita Total", f"R$ {total_receita:,.2f}", delta=None)
with col3:
    avg_ticket = filtered_df['total'].mean() if len(filtered_df) > 0 else 0
    st.metric("Ticket Médio", f"R$ {avg_ticket:,.2f}", delta=None)
with col4:
    total_qtd = filtered_df['quantidade'].sum() if 'quantidade' in filtered_df else 0
    st.metric("Qtd Total Vendida", f"{total_qtd:,.0f}", delta=None)

# Abas
 tab1, tab2, tab3 = st.tabs(["📝 Cadastro", "📋 Listagem", "📈 Relatórios"])

with tab1:
    st.header("Cadastro de Nova Venda")
    """
    # OBSERVAÇÃO: Como o link é um CSV público de exportação do Google Sheets (somente LEITURA),
    # não é possível escrever diretamente no arquivo via este app sem autenticação.
    # Para CADASTRO de novas vendas (escrita), o ideal é usar um Google Forms vinculado à planilha,
    # garantindo integridade dos dados sem depender de bibliotecas de conexão como gsheets.
    # Exemplo: Crie um Form -> Link para Sheet -> Compartilhe o link do Form com usuários.
    # Aqui, o form é para simulação/visualização dos dados a serem cadastrados.
    """
    with st.form("cadastro_venda"):
        col1, col2 = st.columns(2)
        with col1:
            data_venda = st.date_input("Data da Venda", value=date.today())
            produto = st.text_input("Produto")
            quantidade = st.number_input("Quantidade", min_value=1, step=1)
        with col2:
            valor_unitario = st.number_input("Valor Unitário (R$)", min_value=0.01, format="%.2f", step=0.01)
            total = quantidade * valor_unitario
            st.number_input("Total (R$)", value=total, disabled=True, format="%.2f")
        
        submitted = st.form_submit_button("Simular Cadastro", use_container_width=True)
        if submitted:
            nova_venda = {
                'data': data_venda,
                'produto': produto,
                'quantidade': quantidade,
                'valor_unitario': valor_unitario,
                'total': total
            }
            st.success("✅ Dados simulados com sucesso!")
            st.json(nova_venda)
            st.info("📝 Para salvar de verdade, acesse o Google Forms da planilha ou edite manualmente.")

with tab2:
    st.header("Listagem de Vendas")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

with tab3:
    st.header("Relatórios")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not filtered_df.empty and 'produto' in filtered_df.columns:
            vendas_por_produto = filtered_df.groupby('produto')['total'].sum().reset_index()
            fig1 = px.bar(vendas_por_produto, x='produto', y='total', title="Vendas por Produto")
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        if not filtered_df.empty:
            vendas_por_data = filtered_df.groupby(filtered_df['data'].dt.date)['total'].sum().reset_index()
            vendas_por_data['data'] = pd.to_datetime(vendas_por_data['data'])
            fig2 = px.line(vendas_por_data, x='data', y='total', title="Evolução de Vendas")
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
    
    if not filtered_df.empty and 'quantidade' in filtered_df.columns:
        fig3 = px.pie(filtered_df, names='produto', values='quantidade', title="Distribuição de Quantidade por Produto")
        st.plotly_chart(fig3, use_container_width=True)