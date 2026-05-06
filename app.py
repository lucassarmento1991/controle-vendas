import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client
import hashlib

st.set_page_config(page_title="Sistema de Controle de Vendas", page_icon="💰", layout="wide")

# 1. INICIALIZAÇÃO RESILIENTE (Resolve o KeyError)
@st.cache_resource
def init_supabase():
    url = None
    key = None
    
    # Tentativa 1: Busca dentro do bloco [supabase] (conforme sua configuração anterior)
    if "supabase" in st.secrets:
        url = st.secrets["supabase"].get("url") or st.secrets["supabase"].get("SUPABASE_URL")
        key = st.secrets["supabase"].get("key") or st.secrets["supabase"].get("SUPABASE_ANON_KEY")
    
    # Tentativa 2: Busca na raiz dos Secrets
    if not url or not key:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_ANON_KEY")

    if not url or not key:
        st.error("❌ Erro de Configuração: As chaves 'SUPABASE_URL' e 'SUPABASE_ANON_KEY' não foram encontradas nos Secrets do Streamlit.")
        st.info("Verifique se o seu arquivo Secrets está assim:\n\n[supabase]\nurl = 'sua_url'\nkey = 'sua_key'")
        st.stop()
        
    return create_client(url.strip(), key.strip())

supabase: Client = init_supabase()

# 2. AUTENTICAÇÃO E CONTROLE DE SESSÃO
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def authenticate(username: str, password: str) -> bool:
    # Limpeza de cache para garantir que a consulta ao banco seja atualizada
    st.cache_data.clear() 
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    try:
        response = supabase.table('usuarios').select('password_hash').eq('username', username).execute()
        if response.data and response.data[0]['password_hash'] == password_hash:
            return True
        return False
    except Exception as e:
        st.error(f"Erro na autenticação: {str(e)}")
        return False

# Interface de Login
if not st.session_state.logged_in:
    st.title("🔐 Login - Controle de Vendas")
    
    with st.form("login_form"):
        u_input = st.text_input("Username").strip()
        p_input = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", type="primary", use_container_width=True):
            if authenticate(u_input, p_input):
                st.session_state.logged_in = True
                st.session_state.username = u_input
                st.rerun()
            else:
                st.error("Credenciais inválidas ou erro de sincronia.")
    st.stop()

# 3. INTERFACE PRINCIPAL
st.sidebar.write(f"👤 Usuário: **{st.session_state.username}**")
if st.sidebar.button("🚪 Sair"):
    st.session_state.logged_in = False
    st.rerun()

@st.cache_data(ttl=60)
def load_sales():
    return supabase.table('vendas').select('*').order('data_venda', desc=True).execute().data

tab1, tab2, tab3 = st.tabs(["📥 Cadastro", "📋 Gerenciar/Excluir", "📊 Relatórios"])

with tab1:
    st.subheader("Novo Registro")
    with st.form("new_sale", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            prod = st.text_input("Produto")
            qtd = st.number_input("Quantidade", min_value=1, step=1)
        with c2:
            val = st.number_input("Valor Unitário (R$)", min_value=0.01, format="%.2f")
            dt_venda = st.date_input("Data", value=date.today())
        
        if st.form_submit_button("Cadastrar Venda"):
            total = qtd * val
            supabase.table('vendas').insert({
                'produto': prod, 'quantidade': float(qtd), 'valor_unitario': float(val),
                'total': float(total), 'data_venda': dt_venda.isoformat()
            }).execute()
            st.success("Venda registrada!")
            st.cache_data.clear()
            st.rerun()

with tab2:
    st.subheader("Lista de Vendas (Edição bloqueada)")
    data = load_sales()
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("🗑️ Excluir Registro")
        id_excluir = st.selectbox("Selecione o ID para remover:", df['id'].tolist())
        if st.button("Confirmar Exclusão", type="primary"):
            supabase.table('vendas').delete().eq('id', id_excluir).execute()
            st.success(f"ID {id_excluir} removido.")
            st.cache_data.clear()
            st.rerun()

with tab3:
    st.subheader("Análise Analítica")
    data = load_sales()
    if data:
        df = pd.DataFrame(data)
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento Total", f"R$ {df['total'].sum():,.2f}")
        m2.metric("Média por Venda", f"R$ {df['total'].mean():,.2f}")
        m3.metric("Total Itens", int(df['quantidade'].sum()))
        st.bar_chart(df.groupby('produto')['total'].sum())