import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib
from datetime import datetime

st.set_page_config(page_title="App Vendas", page_icon="📊", layout="wide")

@st.cache_resource
def init_supabase():
    # Try different secrets formats
    SUPABASE_URL = (st.secrets.get('SUPABASE_URL') or '').strip()
    if not SUPABASE_URL:
        SUPABASE_URL = (st.secrets.get('supabase', {}).get('url') or '').strip()
    
    SUPABASE_KEY = (st.secrets.get('SUPABASE_KEY') or '').strip()
    if not SUPABASE_KEY:
        SUPABASE_KEY = (st.secrets.get('supabase', {}).get('key') or '').strip()
    
    if not SUPABASE_URL:
        st.error("❌ Missing Supabase URL in secrets.toml")
        st.stop()
    
    if not SUPABASE_URL.startswith('https://'):
        st.error("❌ Invalid Supabase URL. It must start with 'https://'. Check your secrets.toml file.")
        st.stop()
    
    if not SUPABASE_KEY:
        st.error("❌ Missing Supabase Key in secrets.toml")
        st.stop()
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

# Session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Login handling
if not st.session_state.logged_in:
    st.title("🔐 Login")
    st.markdown("---")
    email = st.text_input("Email", placeholder="Digite seu email")
    password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
    
    col1, col2 = st.columns([3,1])
    with col1:
        if st.button("Entrar", use_container_width=True):
            if email and password:
                hashed_pw = hash_password(password)
                response = supabase.table('users').select('*').eq('email', email).eq('password_hash', hashed_pw).execute()
                if response.data:
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Email ou senha inválidos!")
            else:
                st.warning("Preencha email e senha.")
    with col2:
        st.markdown("**ou**")
    
    if st.button("Cadastrar novo usuário"):
        st.session_state.show_register = True
    
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown(f"👋 Logado como: **{st.session_state.user_email}**")
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.user_email = None
        st.rerun()

# Main app
st.title("📊 Dashboard de Vendas")
st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Dashboard", "🛒 Vendas", "👥 Cadastro", "📋 Listagem", "📊 Relatórios"])

@st.cache_data
def get_vendas():
    return supabase.table('vendas').select('*').order('created_at', desc=True).execute().data

with tab1:
    st.header("📈 Dashboard")
    
    vendas_data = get_vendas()
    df = pd.DataFrame(vendas_data)
    
    if not df.empty:
        total_vendas = len(df)
        total_revenue = df['total'].sum()
        avg_ticket = total_revenue / total_vendas if total_vendas > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Vendas", total_vendas)
        col2.metric("Receita Total", f"R$ {total_revenue:.2f}")
        col3.metric("Ticket Médio", f"R$ {avg_ticket:.2f}")
        col4.metric("Produtos Únicos", df['product'].nunique())
        
        df['date'] = pd.to_datetime(df['date'])
        fig = px.bar(df, x='date', y='total', title="Vendas por Data", color='product')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhuma venda registrada ainda.")

with tab2:
    st.header("🛒 Gerenciar Vendas")
    
    with st.form("nova_venda"):
        col1, col2 = st.columns(2)
        with col1:
            product = st.text_input("Produto")
            quantity = st.number_input("Quantidade", min_value=1, step=1)
        with col2:
            price = st.number_input("Preço Unitário (R$)", min_value=0.01, format="%.2f")
        
        total = quantity * price
        st.info(f"**Total: R$ {total:.2f}**")
        
        submitted = st.form_submit_button("➕ Adicionar Venda", use_container_width=True)
        if submitted:
            data = {
                'product': product,
                'quantity': int(quantity),
                'price': float(price),
                'total': float(total),
                'date': datetime.now().isoformat()
            }
            supabase.table('vendas').insert(data).execute()
            st.success("✅ Venda adicionada com sucesso!")
            st.cache_data.clear()
            st.rerun()
    
    st.subheader("Últimas Vendas")
    vendas_data = get_vendas()[:10]
    if vendas_data:
        st.dataframe(pd.DataFrame(vendas_data), use_container_width=True)
    else:
        st.info("Nenhuma venda.")

with tab3:
    st.header("👥 Cadastro de Usuário")
    st.warning("⚠️ Use com cuidado - para novos usuários.")
    
    with st.form("novo_usuario"):
        new_email = st.text_input("Email")
        new_password = st.text_input("Senha", type="password")
        
        submitted = st.form_submit_button("👤 Cadastrar", use_container_width=True)
        if submitted:
            if new_email and new_password:
                hashed = hash_password(new_password)
                try:
                    supabase.table('users').insert({
                        'email': new_email,
                        'password_hash': hashed
                    }).execute()
                    st.success("✅ Usuário cadastrado!")
                except Exception as e:
                    st.error(f"❌ Erro: {str(e)}")
            else:
                st.error("Preencha todos os campos.")

with tab4:
    st.header("📋 Listagem Completa de Vendas")
    vendas_data = get_vendas()
    if vendas_data:
        df = pd.DataFrame(vendas_data)
        df['date'] = pd.to_datetime(df['date'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhuma venda registrada.")

with tab5:
    st.header("📊 Relatórios")
    
    vendas_data = get_vendas()
    if not vendas_data:
        st.info("Nenhuma venda para relatórios.")
    else:
        df = pd.DataFrame(vendas_data)
        df['date'] = pd.to_datetime(df['date'])
        
        col1, col2 = st.columns(2)
        with col1:
            fig_pie = px.pie(df, names='product', values='total', title="Distribuição por Produto")
            st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
            fig_line = px.line(df.groupby(df['date'].dt.date)['total'].sum().reset_index(), x='date', y='total', title="Evolução das Vendas")
            st.plotly_chart(fig_line, use_container_width=True)