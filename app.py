# IMPORTANT: In your Supabase database, ensure the 'usuarios' table has a row with:
# username = 'vendas'
# password_hash = 'ad1e10c7f2d809520c2191e442ed016ed7507debeaad03d061a97ec69dc2361e'
# This is the SHA256 hash of 'pao123'. Update the DB and the old password 'lucas123' will no longer work.

import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client
import hashlib

st.set_page_config(page_title="Sistema de Controle de Vendas", page_icon="💰", layout="wide")

# Supabase connection
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

supabase: Client = init_supabase()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def authenticate(username: str, password: str) -> bool:
    st.cache_data.clear()  # Clear cache to ensure fresh data from DB
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    response = supabase.table('usuarios').select('password_hash').eq('username', username).execute()
    if not response.data:
        return False
    return password_hash == response.data[0]['password_hash']

# Login
if not st.session_state.logged_in:
    st.title("🔐 Login - Sistema de Controle de Vendas")
    st.info("**Username: vendas** | **Senha: pao123**\n\nVerifique o hash no banco (comentário acima).")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        username = st.text_input("Username", placeholder="vendas")
    with col2:
        password = st.text_input("Senha", type="password", placeholder="pao123")
    
    if st.button("Entrar", type="primary"):
        if username and password:
            if authenticate(username, password):
                st.session_state.logged_in = True
                st.success("Login bem-sucedido!")
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
        else:
            st.warning("Preencha todos os campos.")
else:
    st.title("💰 Sistema de Controle de Vendas")
    
    # Logout
    if st.sidebar.button("🚪 Sair"):
        st.session_state.logged_in = False
        st.rerun()
    
    @st.cache_data(ttl=60)
    def load_sales():
        return supabase.table('vendas').select('*').order('data_venda', desc=True).execute().data
    
    tab1, tab2, tab3 = st.tabs(["📥 Cadastro", "📋 Lista/Exclusão", "📊 Relatórios"])
    
    with tab1:
        st.subheader("Nova Venda")
        with st.form("new_sale"):
            col1, col2 = st.columns(2)
            with col1:
                produto = st.text_input("Produto", key="prod")
                quantidade = st.number_input("Quantidade", min_value=1, step=1, key="qtd")
            with col2:
                valor_unitario = st.number_input("Valor Unitário (R$)", min_value=0.01, format="%.2f", key="vu")
                data_venda = st.date_input("Data", value=date.today(), key="data")
            
            total = quantidade * valor_unitario
            st.number_input("Total (R$)", value=round(total, 2), disabled=True, key="total")
            
            if st.form_submit_button("Cadastrar"):
                if produto.strip():
                    supabase.table('vendas').insert({
                        'produto': produto.strip(),
                        'quantidade': float(quantidade),
                        'valor_unitario': float(valor_unitario),
                        'total': float(total),
                        'data_venda': data_venda.isoformat()
                    }).execute()
                    st.success("Venda cadastrada!")
                    st.rerun()
                else:
                    st.error("Produto obrigatório.")
    
    with tab2:
        st.subheader("Vendas (Exclusão disponível | Edição travada)")
        vendas = load_sales()
        if vendas:
            df = pd.DataFrame(vendas)
            st.dataframe(df, use_container_width=True, hide_index=False)
            
            st.subheader("Excluir Venda")
            if 'id' in df.columns:
                selected_id = st.selectbox("ID para excluir:", df['id'].tolist())
                if st.button("Excluir"):
                    supabase.table('vendas').delete().eq('id', selected_id).execute()
                    st.success("Excluída!")
                    st.rerun()
            else:
                st.warning("Tabela sem coluna 'id'.")
        else:
            st.info("Nenhuma venda.")
    
    with tab3:
        st.subheader("Relatórios")
        vendas = load_sales()
        if vendas:
            df = pd.DataFrame(vendas)
            col1, col2, col3 = st.columns(3)
            total_vendas = df['total'].sum()
            with col1:
                st.metric("Total Vendas", f"R$ {total_vendas:,.2f}")
            with col2:
                st.metric("Qtd. Vendas", len(df))
            with col3:
                st.metric("Média", f"R$ {df['total'].mean():,.2f}")
            
            st.subheader("Total por Produto")
            agrupado = df.groupby('produto')['total'].sum().sort_values(ascending=False)
            st.bar_chart(agrupado)
            
            st.dataframe(df)
        else:
            st.info("Sem dados para relatórios.")