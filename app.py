import streamlit as st
import hashlib
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# Supabase configuration (use st.secrets in production)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "your_supabase_url")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "your_supabase_key")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

# Login/Register page
if not st.session_state.logged_in:
    st.title("🛡️ Login / Cadastro de Usuário")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Login")
        username = st.text_input("Usuário", key="login_user")
        password = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Entrar"):
            if username and password:
                result = supabase.table('users').select('username, password_hash').eq('username', username).execute()
                if result.data:
                    user_data = result.data[0]
                    if hash_password(password) == user_data['password_hash']:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.success(f"Bem-vindo, {username}!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta!")
                else:
                    st.error("Usuário não encontrado!")
            else:
                st.error("Preencha todos os campos!")
    
    with col2:
        st.subheader("Novo Usuário")
        new_username = st.text_input("Novo Usuário", key="new_user")
        new_password = st.text_input("Nova Senha", type="password", key="new_pass")
        if st.button("Cadastrar"):
            if new_username and new_password:
                # Check if user exists
                existing = supabase.table('users').select('username').eq('username', new_username).execute()
                if not existing.data:
                    hashed_pw = hash_password(new_password)
                    supabase.table('users').insert({
                        'username': new_username,
                        'password_hash': hashed_pw
                    }).execute()
                    st.success("Usuário cadastrado com sucesso!")
                else:
                    st.error("Usuário já existe!")
            else:
                st.error("Preencha todos os campos!")
else:
    # Main dashboard after login
    st.title(f"📊 Dashboard - {st.session_state.username}")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["Cadastro", "Listagem", "Relatórios Plotly"])
    
    with tab1:
        st.subheader("📝 Cadastro de Dados")
        col_a, col_b = st.columns(2)
        with col_a:
            name = st.text_input("Nome")
        with col_b:
            value = st.number_input("Valor", min_value=0.0)
        if st.button("Cadastrar Dados"):
            if name and value:
                supabase.table('dados').insert({
                    'name': name,
                    'value': float(value)
                }).execute()
                st.success("Dados cadastrados!")
                st.rerun()
    
    with tab2:
        st.subheader("📋 Listagem de Dados")
        result = supabase.table('dados').select('*').order('created_at', desc=True).execute()
        if result.data:
            df = pd.DataFrame(result.data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum dado cadastrado ainda.")
    
    with tab3:
        st.subheader("📈 Relatórios com Plotly")
        result = supabase.table('dados').select('*').execute()
        if result.data:
            df = pd.DataFrame(result.data)
            
            col1, col2 = st.columns(2)
            with col1:
                fig_bar = px.bar(df, x='name', y='value', title='Gráfico de Barras')
                st.plotly_chart(fig_bar, use_container_width=True)
            with col2:
                fig_pie = px.pie(df, names='name', values='value', title='Gráfico de Pizza')
                st.plotly_chart(fig_pie, use_container_width=True)
            
            st.metric("Total de Registros", len(df))
            st.metric("Valor Total", df['value'].sum())
        else:
            st.info("Nenhum dado para relatórios.")
    
    # Logout
    st.sidebar.button("🚪 Logout", on_click=lambda: (setattr(st.session_state, 'logged_in', False), setattr(st.session_state, 'username', None), st.rerun()))