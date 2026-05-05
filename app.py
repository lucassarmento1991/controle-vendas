import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib

st.set_page_config(page_title="App Lucas - Debug Edition", page_icon="🔧", layout="wide")

# Custom CSS (mantendo estrutura existente)
st.markdown("""
<style>
    .main { margin-top: 20px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stPlotlyChart { width: 100%; }
</style>
""", unsafe_allow_html=True)

# 1. Limpar rigorosamente os segredos
try:
    supabase_url = st.secrets["SUPABASE_URL"].strip()
    supabase_key = st.secrets["SUPABASE_KEY"].strip()
    
    if not supabase_url or not supabase_key:
        st.error("❌ Segredos SUPABASE_URL ou SUPABASE_KEY não configurados ou vazios.")
        st.stop()
    
    st.success("✅ Segredos carregados com sucesso.")
except Exception as e:
    st.error(f"❌ Erro ao carregar segredos: {str(e)}")
    st.stop()

# Inicializar cliente Supabase
supabase: Client = create_client(supabase_url, supabase_key)

# 2. Bloco de debug visível
st.sidebar.header("🔧 Debug")
with st.sidebar.expander("Status do Cliente Supabase", expanded=True):
    st.success("✅ Cliente Supabase inicializado com sucesso.")
    st.code(f"URL: {supabase_url[:20]}...\nKey: {'*' * 20}")

# 7. Botão Testar Conexão
if st.sidebar.button("🧪 Testar Conexão"):
    try:
        response = supabase.table("usuarios").select("id").limit(1).execute()
        if response.data:
            st.sidebar.success("✅ Conexão OK! Tabela 'usuarios' acessível.")
        else:
            st.sidebar.warning("⚠️ Tabela 'usuarios' vazia, mas conexão OK.")
    except Exception as e:
        st.sidebar.error(f"❌ Erro na conexão: {str(e)}")

# Gerenciar estado de login
if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    # Tela de Login
    st.title("🔐 Login")
    st.markdown("---")
    
    with st.form("login_form"):
        nome_usuario = st.text_input("Nome de Usuário", placeholder="Digite seu nome de usuário")
        senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        col1, col2 = st.columns([4,1])
        with col2:
            submit = st.form_submit_button("Entrar", use_container_width=True)
        
        if submit:
            if not nome_usuario.strip() or not senha.strip():
                st.error("❌ Preencha todos os campos.")
            else:
                nome_usuario = nome_usuario.strip()
                # 3. Log de busca
                st.info(f"🔍 Buscando usuário: **{nome_usuario}**")
                
                # 5. Hash da senha (mesmo usado no INSERT)
                senha_hash = hashlib.sha256(senha.encode('utf-8')).hexdigest()
                
                try:
                    # Busca no Supabase
                    response = supabase.table("usuarios").select("*") \
                                     .eq("nome_usuario", nome_usuario).execute()
                    
                    data = response.data
                    
                    # 4. Tratamento detalhado de erros
                    if len(data) == 0:
                        st.error("❌ **Usuário não encontrado.**\nVerifique o nome de usuário.")
                    elif data[0]["senha"] != senha_hash:
                        st.error("❌ **Senha não confere.**\nVerifique a senha digitada.")
                    else:
                        st.session_state.user = nome_usuario
                        st.success(f"🎉 Login realizado com sucesso, {nome_usuario}!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Erro durante login: {str(e)}")
else:
    # Interface principal após login (mantendo Tabs e Relatórios Plotly)
    st.title(f"👋 Bem-vindo, {st.session_state.user}!")
    st.markdown("---")
    
    # Botão de Logout
    col1, col2 = st.columns([1, 10])
    with col1:
        if st.button("🚪 Logout", use_container_width=True):
            del st.session_state.user
            st.rerun()
    
    # Tabs com Relatórios Plotly (estrutura mantida)
    tab1, tab2, tab3 = st.tabs(["📊 Vendas", "👥 Usuários", "📈 Dashboard Geral"])
    
    with tab1:
        st.header("Relatório de Vendas")
        try:
            response = supabase.table("vendas").select("*") \
                             .order("data", desc=True).limit(100).execute()
            df = pd.DataFrame(response.data)
            if not df.empty:
                fig = px.bar(df, x="produto", y="valor_total", color="regiao", title="Vendas por Produto")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum dado de vendas encontrado.")
        except Exception as e:
            st.error(f"Erro ao carregar vendas: {e}")
    
    with tab2:
        st.header("Relatório de Usuários")
        try:
            response = supabase.table("usuarios").select("nome_usuario, email, data_cadastro") \
                             .neq("nome_usuario", st.session_state.user).limit(50).execute()
            df = pd.DataFrame(response.data)
            if not df.empty:
                fig = px.pie(df, names="nome_usuario", title="Distribuição de Usuários")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum outro usuário encontrado.")
        except Exception as e:
            st.error(f"Erro ao carregar usuários: {e}")
    
    with tab3:
        st.header("Dashboard Geral")
        col1, col2 = st.columns(2)
        with col1:
            # Exemplo de métricas
            try:
                count_resp = supabase.table("vendas").select("count").execute()
                st.metric("Total Vendas", count_resp.count)
            except:
                st.metric("Total Vendas", "N/A")
        with col2:
            try:
                user_resp = supabase.table("usuarios").select("count").execute()
                st.metric("Total Usuários", user_resp.count)
            except:
                st.metric("Total Usuários", "N/A")
