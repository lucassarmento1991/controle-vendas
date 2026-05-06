import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib

@st.cache_resource
def init_supabase():
    supabase_config = st.secrets["supabase"]
    return create_client(supabase_config["url"], supabase_config["anon_key"])

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

st.set_page_config(page_title="Gerenciamento App", page_icon="🔐", layout="wide")

supabase = init_supabase()

# Sidebar for authentication
with st.sidebar:
    st.title("🔐 Autenticação")
    if st.session_state.get('username'):
        st.success(f"👤 Logado como: {st.session_state.username}")
        if st.button("🚪 Sair"):
            st.session_state.username = None
            st.rerun()
    else:
        st.subheader("Entrar")
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            res = supabase.table('usuarios').select('password_hash').eq('username', username).execute()
            if res.data and len(res.data) == 1 and hash_password(password) == res.data[0]['password_hash']:
                st.session_state.username = username
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos")

st.title("📊 App de Gerenciamento de Usuários e Relatórios")

if not st.session_state.get('username'):
    st.warning("⚠️ Por favor, faça login para acessar as funcionalidades.")
    st.stop()

tabs = st.tabs(["👥 Cadastro", "📋 Gerenciar Usuários", "📈 Relatórios", "🔒 Segurança"])

with tabs[0]:
    st.header("Cadastro de Novo Usuário")
    with st.form("form_cadastro", clear_on_submit=True):
        new_username = st.text_input("Nome de Usuário")
        new_password = st.text_input("Senha", type="password")
        confirm_password = st.text_input("Confirme a Senha", type="password")
        submitted = st.form_submit_button("Cadastrar")
        if submitted:
            if new_password != confirm_password:
                st.error("❌ As senhas não coincidem!")
            elif len(new_password) < 6:
                st.error("❌ A senha deve ter pelo menos 6 caracteres.")
            else:
                exists_res = supabase.table('usuarios').select('username').eq('username', new_username).execute()
                if exists_res.data:
                    st.error("❌ Usuário já existe!")
                else:
                    pw_hash = hash_password(new_password)
                    insert_res = supabase.table('usuarios').insert({
                        "username": new_username,
                        "password_hash": pw_hash
                    }).execute()
                    if insert_res.data:
                        st.success("✅ Usuário cadastrado com sucesso!")
                    else:
                        st.error("❌ Erro ao cadastrar.")

with tabs[1]:
    st.header("Gerenciar Usuários")
    users_res = supabase.table('usuarios').select('*').execute()
    if users_res.data:
        df = pd.DataFrame(users_res.data)
        if 'password_hash' in df.columns:
            df = df.drop('password_hash', axis=1)
        st.dataframe(df, use_container_width=True)
        st.info("🛡️ Exclusão de usuários travada por segurança.")
    else:
        st.info("Nenhum usuário cadastrado.")

with tabs[2]:
    st.header("Relatórios de Vendas")
    # Get unique options
    prod_res = supabase.table('vendas').select('produto').execute()
    produtos_options = list({row['produto'] for row in prod_res.data if row.get('produto')})
    user_res = supabase.table('vendas').select('usuario').execute()
    usuarios_options = list({row['usuario'] for row in user_res.data if row.get('usuario')})

    col1, col2 = st.columns(2)
    with col1:
        selected_produtos = st.multiselect("Produtos", produtos_options)
    with col2:
        selected_usuarios = st.multiselect("Usuários", usuarios_options)

    query = supabase.table('vendas').select('*')
    if selected_produtos:
        query = query.in_('produto', selected_produtos)
    if selected_usuarios:
        query = query.in_('usuario', selected_usuarios)
    vendas_data = query.execute()
    if vendas_data.data:
        df = pd.DataFrame(vendas_data.data)
        st.dataframe(df, use_container_width=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Vendas", len(df))
        with col2:
            total_valor = df['valor'].sum() if 'valor' in df.columns and pd.api.types.is_numeric_dtype(df['valor']) else 0
            st.metric("Total Valor", f"R$ {total_valor:.2f}")
        with col3:
            if 'data' in df.columns:
                st.metric("Período", f"{df['data'].min()} a {df['data'].max()}")
    else:
        st.info("📭 Nenhum dado com os filtros selecionados.")

with tabs[3]:
    st.header("🔒 Segurança - Alterar Senha")
    pw_res = supabase.table('usuarios').select('password_hash').eq('username', st.session_state.username).execute()
    if not pw_res.data:
        st.error("❌ Erro: usuário não encontrado.")
        st.stop()
    current_hash = pw_res.data[0]['password_hash']
    with st.form("form_senha", clear_on_submit=True):
        current_password = st.text_input("Senha Atual", type="password")
        new_password = st.text_input("Nova Senha", type="password")
        confirm_new = st.text_input("Confirme Nova Senha", type="password")
        submitted = st.form_submit_button("Alterar Senha")
        if submitted:
            if hash_password(current_password) != current_hash:
                st.error("❌ Senha atual incorreta!")
            elif new_password != confirm_new:
                st.error("❌ As novas senhas não coincidem!")
            elif len(new_password) < 6:
                st.error("❌ Nova senha muito curta (mín. 6 chars)!")
            else:
                new_hash = hash_password(new_password)
                update_res = supabase.table('usuarios').update({
                    "password_hash": new_hash
                }).eq('username', st.session_state.username).execute()
                if update_res.data:
                    st.success("✅ Senha alterada com sucesso!")
                else:
                    st.error("❌ Erro ao atualizar senha.")