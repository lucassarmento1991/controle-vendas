import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib
from datetime import date

@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

st.set_page_config(page_title="Sistema de Vendas - Supabase", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None

supabase = get_supabase()

if not st.session_state.logged_in:
    st.title(":lock: Login")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://supabase.com/assets/images/supabase-heart-full.svg", width=100)
    with col2:
        user_input = st.text_input("Nome de Usuário", key="user_input")
        pass_input = st.text_input("Senha", type="password", key="pass_input")
        super_debug = st.checkbox("Super Debug")
        if st.button("Entrar", type="primary"):
            if user_input and pass_input:
                data = supabase.table('usuarios').select('*').ilike('username', user_input).execute()
                if data.data:
                    user = data.data[0]
                    generated_hash = hash_password(pass_input)
                    db_hash = user['password_hash']
                    if super_debug:
                        st.write(f"**Generated hash:** `{generated_hash}`")
                        st.write(f"**DB hash:** `{db_hash}`")
                    if generated_hash == db_hash:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user['id']
                        st.session_state.username = user['username']
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta!")
                else:
                    st.error("Usuário não encontrado!")
            else:
                st.warning("Preencha todos os campos.")
else:
    # Header
    col1, col2, col3 = st.columns([1, 3, 1])
    col1.metric("Usuário", st.session_state.username)
    col3.button("Sair", on_click=lambda: (st.session_state.update(logged_in=False, user_id=None, username=None), st.rerun()))

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📈 Cadastrar Venda", "📋 Listar Vendas", "📊 Gráficos"])

    with tab1:
        st.header("Nova Venda")
        with st.form("venda_form"):
            data_venda = st.date_input("Data da Venda", value=date.today())
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            produto = st.text_input("Produto")
            descricao = st.text_area("Descrição")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.form_submit_button("Cadastrar Venda"):
                    result = supabase.table('vendas').insert({
                        'user_id': st.session_state.user_id,
                        'data_venda': data_venda.isoformat(),
                        'valor': float(valor),
                        'produto': produto,
                        'descricao': descricao
                    }).execute()
                    if result.data:
                        st.success("Venda cadastrada com sucesso!")
                        st.rerun()
            with col_b:
                st.info("Campos obrigatórios: *data, valor, produto*")

    with tab2:
        st.header("Lista de Vendas")
        vendas_data = supabase.table('vendas').select('*').eq('user_id', st.session_state.user_id).order('data_venda', desc=True).execute()
        if vendas_data.data:
            df = pd.DataFrame(vendas_data.data)
            df['data_venda'] = pd.to_datetime(df['data_venda'])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhuma venda cadastrada ainda.")

    with tab3:
        st.header("Gráficos")
        vendas_data = supabase.table('vendas').select('*').eq('user_id', st.session_state.user_id).order('data_venda').execute()
        if vendas_data.data:
            df = pd.DataFrame(vendas_data.data)
            df['data_venda'] = pd.to_datetime(df['data_venda'])

            col1, col2 = st.columns(2)
            with col1:
                fig_bar = px.bar(df, x='data_venda', y='valor', title='Vendas por Data',
                                 color='produto')
                st.plotly_chart(fig_bar, use_container_width=True)
            with col2:
                vendas_produto = df.groupby('produto')['valor'].sum().reset_index()
                fig_pie = px.pie(vendas_produto, values='valor', names='produto',
                                 title='Distribuição por Produto')
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Dados insuficientes para gráficos. Cadastre vendas primeiro.")