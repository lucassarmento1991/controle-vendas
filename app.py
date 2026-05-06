import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client, PostgrestAPIError
import bcrypt

st.set_page_config(page_title="Dashboard Lucas", page_icon="📊", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

# Initialize Supabase client with cleaned secrets
url = st.secrets.get("SUPABASE_URL", "").strip()
key = st.secrets.get("SUPABASE_ANON_KEY", "").strip()  # or "SUPABASE_SERVICE_KEY"

if not url or not key:
    st.error("❌ Configure SUPABASE_URL e SUPABASE_ANON_KEY nos Secrets do Streamlit.")
    st.stop()

supabase: Client = create_client(url, key)

# Function for initial table check
def initial_check(supabase):
    with st.sidebar:
        st.markdown("### 🛠️ Verificação Inicial da Tabela")
        try:
            supabase.table('usuarios').select('id').limit(1).execute()
            st.success("✅ Tabela 'usuarios' existe e é acessível!")
        except PostgrestAPIError as e:
            st.error(f"❌ Erro ao acessar 'usuarios': **{e.message}**")
            st.info("Verificando nomes alternativos...")
            alts = ['users', 'Users', 'Usuarios']
            found = False
            for alt in alts:
                try:
                    supabase.table(alt).select('id').limit(1).execute()
                    st.success(f"✅ Tabela '{alt}' existe!")
                    found = True
                except PostgrestAPIError:
                    pass
            if not found:
                st.warning("Nenhuma tabela alternativa encontrada. Verifique no Dashboard Supabase.")

initial_check(supabase)

# Sidebar
with st.sidebar:
    st.title("📊 Dashboard Lucas")

    # Schema check button
    if st.button("🔍 Verificar Esquema do Banco"):
        with st.spinner("Verificando colunas da 'usuarios'..."):
            st.markdown("**Teste de colunas na tabela 'usuarios':**")
            cols = ['id', 'username', 'password_hash', 'email', 'created_at']
            for col in cols:
                try:
                    supabase.table('usuarios').select(col).limit(1).execute()
                    st.success(f"✅ {col}")
                except PostgrestAPIError as e:
                    msg = str(e)
                    if 'column' in msg.lower():
                        st.error(f"❌ {col} (coluna não existe)")
                    else:
                        st.error(f"❌ {col}: {e.message}")

    if st.session_state.logged_in:
        st.success(f"👋 Olá, **{st.session_state.user}**!")
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
    else:
        st.markdown("### 🔐 Login")
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("Username")
            password = st.text_input("Senha", type="password")
            col_btn, _ = st.columns([3, 1])
            with col_btn:
                login_submitted = st.form_submit_button("Entrar")

        if login_submitted and username and password:
            try:
                response = supabase.table('usuarios').select('password_hash').eq('username', username).execute()
                if response.data and bcrypt.checkpw(password.encode('utf-8'), response.data[0]['password_hash'].encode('utf-8')):
                    st.session_state.user = username
                    st.session_state.logged_in = True
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Username ou senha incorretos.")
            except PostgrestAPIError as e:
                msg = str(e)
                st.error(f"❌ Erro no login: **{e.message}**")
                if 'relation "usuarios"' in msg.lower():
                    st.error("Tabela 'usuarios' não encontrada.")
                elif '"username"' in msg:
                    st.error("Coluna 'username' não encontrada.")
                elif '"password_hash"' in msg:
                    st.error("Coluna 'password_hash' não encontrada.")

# Main content
if st.session_state.logged_in:
    st.markdown("# 📈 Dashboard de Vendas")

    tab1, tab2 = st.tabs(["➕ Registrar Venda", "📊 Gráficos e Relatórios"])

    with tab1:
        st.subheader("Nova Venda")
        with st.form("venda_form"):
            produto = st.text_input("Produto")
            valor_unit = st.number_input("Valor Unitário (R$)", min_value=0.01, format="%.2f")
            quantidade = st.number_input("Quantidade", min_value=1, step=1)
            data_venda = st.date_input("Data da Venda", value=pd.Timestamp.now().date())
            venda_submitted = st.form_submit_button("Registrar Venda", use_container_width=True)

            if venda_submitted and produto:
                total = valor_unit * quantidade
                venda_data = {
                    "username": st.session_state.user,
                    "produto": produto,
                    "valor_unit": float(valor_unit),
                    "quantidade": int(quantidade),
                    "total": float(total),
                    "data": data_venda.isoformat()
                }
                try:
                    supabase.table('vendas').insert(venda_data).execute()
                    st.success("✅ Venda registrada com sucesso!")
                    st.rerun()
                except PostgrestAPIError as e:
                    st.error(f"❌ Erro ao registrar venda: {e.message}")

    with tab2:
        st.subheader("Relatórios de Vendas")
        try:
            vendas_response = supabase.table('vendas').select("*").eq("username", st.session_state.user).execute()
            if vendas_response.data:
                df = pd.DataFrame(vendas_response.data)
                df['data'] = pd.to_datetime(df['data'])
                df['total'] = pd.to_numeric(df['total'])

                col1, col2 = st.columns(2)

                with col1:
                    fig_pie = px.pie(df, values='total', names='produto',
                                     title="Distribuição por Produto")
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col2:
                    vendas_dia = df.groupby(df['data'].dt.date)['total'].sum().sort_index().reset_index()
                    vendas_dia.columns = ['data', 'total']
                    fig_line = px.line(vendas_dia, x='data', y='total',
                                       title="Vendas ao Longo do Tempo")
                    st.plotly_chart(fig_line, use_container_width=True)

                st.metric("Total de Vendas", f"R$ {df['total'].sum():.2f}")
            else:
                st.info("👆 Registre algumas vendas para ver os gráficos.")
        except PostgrestAPIError as e:
            st.error(f"Erro ao carregar vendas: {e.message}")
else:
    st.markdown("# 🚀 Bem-vindo ao Dashboard")
    st.info("👈 Faça login na sidebar para acessar o formulário de vendas e gráficos.")