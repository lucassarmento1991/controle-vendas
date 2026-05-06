import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from supabase import create_client, Client
from datetime import date, datetime

st.set_page_config(page_title="Controle de Vendas", layout="wide", page_icon="📊")

# 1. INICIALIZAÇÃO RESILIENTE (Resolve o KeyError)
@st.cache_resource
def init_supabase():
    url = None
    key = None
    
    # Tenta buscar no bloco [supabase]
    if "supabase" in st.secrets:
        url = st.secrets["supabase"].get("url") or st.secrets["supabase"].get("SUPABASE_URL")
        key = st.secrets["supabase"].get("key") or st.secrets["supabase"].get("SUPABASE_KEY")
    
    # Tenta buscar na raiz
    if not url or not key:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        st.error("❌ Erro de Configuração: Chaves do Supabase não encontradas nos Secrets.")
        st.stop()
        
    return create_client(url.strip(), key.strip())

supabase: Client = init_supabase()

# 2. AUTENTICAÇÃO (Corrigida para 'paodequeijo')
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Gestão de Vendas")
    with st.form("login_form"):
        user_input = st.text_input("Usuário").strip()
        pass_input = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            try:
                # Busca na tabela 'usuarios'
                res = supabase.table('usuarios').select('*').eq('username', user_input).execute()
                if res.data:
                    # Verifica o hash da senha
                    if res.data[0]['password_hash'] == hash_password(pass_input):
                        st.session_state.logged_in = True
                        st.session_state.username = user_input
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("Usuário não encontrado.")
            except Exception as e:
                st.error(f"Erro de login: {str(e)}")
    st.stop()

# 3. INTERFACE E CARREGAMENTO
st.sidebar.title(f"👤 {st.session_state.username}")
if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

@st.cache_data(ttl=60)
def load_data():
    res = supabase.table('vendas').select('*').order('data_venda', desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['data_venda'] = pd.to_datetime(df['data_venda']).dt.date
        cols_num = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
    return df

tab1, tab2, tab3 = st.tabs(["🛒 Cadastro", "🗑️ Gerenciar Registros", "📊 Relatórios"])

# --- ABA CADASTRO ---
with tab1:
    st.header("Novo Cadastro")
    with st.form("cadastro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            est = st.text_input("Estabelecimento")
            dt = st.date_input("Data", value=date.today())
            br = st.text_input("Bairro")
            pg = st.selectbox("Pagamento", ["Pix", "Cartão", "Dinheiro", "Boleto", "Não Pago"])
        with c2:
            prod = st.text_input("Produto")
            qtd = st.number_input("Quantidade", min_value=1)
            val = st.number_input("Valor Unitário", min_value=0.01)
            com = st.number_input("Comissão %", value=10.0)
        
        total = qtd * val
        v_com = total * (com / 100)
        
        if st.form_submit_button("Salvar Venda", use_container_width=True):
            data = {
                "estabelecimento": est, "data_venda": dt.isoformat(), "bairro": br,
                "forma_pagamento": pg, "produto": prod, "quantidade": float(qtd),
                "valor_produto": float(val), "total_venda": float(total),
                "comissao_percentual": float(com), "valor_comissao": float(v_com), "status": "ativa"
            }
            supabase.table('vendas').insert(data).execute()
            st.success("Venda salva com sucesso!")
            st.cache_data.clear()

# --- ABA GERENCIAR (Apenas Exclusão) ---
with tab2:
    st.header("Exclusão de Registros")
    st.warning("⚠️ Nesta aba você pode apenas excluir registros. Edições não são permitidas.")
    df_excluir = load_data()
    
    if not df_excluir.empty:
        # Trava todas as colunas para edição
        config_view = {col: st.column_config.Column(disabled=True) for col in df_excluir.columns}
        config_view["id"] = st.column_config.NumberColumn("ID", disabled=True)
        config_view["data_venda"] = st.column_config.DateColumn("Data")

        edited_df = st.data_editor(
            df_excluir, 
            num_rows="dynamic", 
            column_config=config_view, 
            use_container_width=True,
            hide_index=True
        )

        if st.button("🗑️ Confirmar Exclusões no Banco", type="primary"):
            orig_ids = set(df_excluir['id'].tolist())
            curr_ids = set(edited_df['id'].dropna().tolist())
            ids_para_deletar = orig_ids - curr_ids