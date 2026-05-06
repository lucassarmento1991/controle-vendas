import streamlit as st
import hashlib
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import datetime

@st.cache_resource
def get_supabase() -> Client:
    try:
        url = st.secrets.get("SUPABASE_URL") or st.secrets.get("supabase", {}).get("url")
        key = st.secrets.get("SUPABASE_KEY") or st.secrets.get("supabase", {}).get("key")
        if not url or not key:
            raise ValueError("Credenciais do Supabase não encontradas.")
        return create_client(url, key)
    except Exception as e:
        st.error(
            f"Erro ao conectar com Supabase: {str(e)}. "
            "Configure o arquivo `.streamlit/secrets.toml` com:"
        )
        st.code("""
SUPABASE_URL = "sua_url_aqui"
SUPABASE_KEY = "sua_chave_aqui"
        """)
        st.code("""
[supabase]
url = "sua_url_aqui"
key = "sua_chave_aqui"
        """)
        st.stop()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# hexdigest

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_email = None

st.title("App do Lucas - Gerenciamento de Usuários")

if not st.session_state.logged_in:
    st.subheader("Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")
        col1, col2 = st.columns([1, 1])
        with col1:
            login_btn = st.form_submit_button("Entrar")
        with col2:
            cadastro_link = st.form_submit_button("Cadastrar novo usuário")

    if login_btn:
        if email and password:
            supabase: Client = get_supabase()
            hashed_pw = hash_password(password)
            response = (
                supabase.table('users')
                .select('id, email')
                .ilike('email', email)
                .eq('password_hash', hashed_pw)
                .execute()
            )
            if response.data:
                st.session_state.logged_in = True
                st.session_state.user_email = response.data[0]['email']
                st.success(f"Login realizado com sucesso! Bem-vindo, {st.session_state.user_email}")
                st.rerun()
            else:
                st.error("Email ou senha incorretos.")
        else:
            st.error("Preencha email e senha.")

    if cadastro_link:
        st.session_state.show_cadastro = True
        st.rerun()

    if 'show_cadastro' in st.session_state and st.session_state.show_cadastro:
        st.subheader("Cadastro de Novo Usuário")
        with st.form("cadastro_form"):
            new_email = st.text_input("Novo Email")
            new_password = st.text_input("Nova Senha", type="password")
            confirm_password = st.text_input("Confirmar Senha", type="password")
            col1, col2 = st.columns([1, 1])
            with col1:
                submit_cadastro = st.form_submit_button("Cadastrar")
            with col2:
                cancel_btn = st.form_submit_button("Cancelar")

        if submit_cadastro:
            if new_password != confirm_password:
                st.error("As senhas não coincidem.")
            elif not new_email or not new_password:
                st.error("Preencha todos os campos.")
            else:
                supabase: Client = get_supabase()
                hashed_pw = hash_password(new_password)
                # Check if exists (case-insensitive)
                exists_resp = supabase.table('users').select('id').ilike('email', new_email).execute()
                if exists_resp.data:
                    st.error("Este email já está cadastrado.")
                else:
                    insert_resp = supabase.table('users').insert({
                        'email': new_email,
                        'password_hash': hashed_pw
                    }).execute()
                    if insert_resp.data:
                        st.success("Usuário cadastrado com sucesso!")
                        st.session_state.show_cadastro = False
                        st.rerun()
                    else:
                        st.error("Erro ao cadastrar usuário.")

        if cancel_btn:
            st.session_state.show_cadastro = False
            st.rerun()
else:
    # Sidebar logout
    st.sidebar.title("Perfil")
    st.sidebar.info(f"Usuário: {st.session_state.user_email}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_email = None
        st.session_state.show_cadastro = False
        st.rerun()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Cadastro", "Listagem", "Gráficos Plotly"])

    supabase: Client = get_supabase()

    with tab1:
        st.subheader("Cadastro de Novo Usuário")
        with st.form("cadastro_tab"):
            new_email = st.text_input("Novo Email", key="new_email_tab")
            new_password = st.text_input("Nova Senha", type="password", key="new_pass_tab")
            confirm_password = st.text_input("Confirmar Senha", type="password", key="confirm_pass_tab")
            col1, col2 = st.columns([1, 1])
            with col1:
                submit_cadastro = st.form_submit_button("Cadastrar")
            with col2:
                pass  # space

        if submit_cadastro:
            if new_password != confirm_password:
                st.error("As senhas não coincidem.")
            elif not new_email or not new_password:
                st.error("Preencha todos os campos.")
            else:
                hashed_pw = hash_password(new_password)
                exists_resp = supabase.table('users').select('id').ilike('email', new_email).execute()
                if exists_resp.data:
                    st.error("Este email já está cadastrado.")
                else:
                    insert_resp = supabase.table('users').insert({
                        'email': new_email,
                        'password_hash': hashed_pw
                    }).execute()
                    if insert_resp.data:
                        st.success("Usuário cadastrado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao cadastrar usuário.")

    with tab2:
        st.subheader("Listagem de Usuários")
        response = supabase.table('users').select('email, created_at').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            df['created_at'] = pd.to_datetime(df['created_at'])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum usuário cadastrado.")

    with tab3:
        st.subheader("Gráficos Plotly")
        response = supabase.table('users').select('email, created_at').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['month'] = df['created_at'].dt.to_period('M').astype(str)
            monthly_counts = df.groupby('month').size().reset_index(name='count')
            fig = px.bar(
                monthly_counts,
                x='month',
                y='count',
                title='Número de Usuários por Mês',
                labels={'month': 'Mês', 'count': 'Quantidade'}
            )
            st.plotly_chart(fig, use_container_width=True)

            # Additional chart: email length histogram
            df['email_length'] = df['email'].str.len()
            fig2 = px.histogram(df, x='email_length', nbins=20, title='Distribuição do Tamanho dos Emails')
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nenhum dado para gráficos. Cadastre usuários primeiro.")
