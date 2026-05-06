import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from supabase import create_client, Client
from datetime import date, datetime

st.set_page_config(page_title="Controle de Vendas", layout="wide", page_icon="📊")

# 1. INICIALIZAÇÃO RESILIENTE DO SUPABASE
@st.cache_resource
def init_supabase():
    # Lista de tentativas para encontrar as chaves
    url = None
    key = None
    
    # Tentativa 1: Formato [supabase] url/key
    if "supabase" in st.secrets:
        url = st.secrets["supabase"].get("url") or st.secrets["supabase"].get("SUPABASE_URL")
        key = st.secrets["supabase"].get("key") or st.secrets["supabase"].get("SUPABASE_KEY")
    
    # Tentativa 2: Formato raiz SUPABASE_URL/SUPABASE_KEY
    if not url or not key:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        st.error("❌ Erro de Configuração: Chaves do Supabase não encontradas.")
        st.info("Certifique-se de que seus Secrets no Streamlit Cloud estão assim:")
        st.code("""
SUPABASE_URL = "sua_url"
SUPABASE_KEY = "sua_chave"
        """)
        st.stop()
        
    return create_client(url.strip(), key.strip())

supabase: Client = init_supabase()

# 2. AUTENTICAÇÃO
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acesso Administrativo")
    with st.form("login_form"):
        user_input = st.text_input("Usuário").strip()
        pass_input = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            try:
                # Consulta na tabela 'usuarios'
                res = supabase.table('usuarios').select('*').eq('username', user_input).execute()
                if res.data and res.data[0]['password_hash'] == hash_password(pass_input):
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
            except Exception as e:
                st.error(f"Erro de login: {str(e)}")
    st.stop()

# 3. INTERFACE PRINCIPAL
st.sidebar.title(f"👤 Usuário: Admin")
if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

tab1, tab2, tab3 = st.tabs(["🛒 Cadastro", "✏️ Edição/Exclusão", "📊 Relatórios"])

def load_data():
    res = supabase.table('vendas').select('*').order('data_venda', desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['data_venda'] = pd.to_datetime(df['data_venda']).dt.date
        # Forçar tipos numéricos para evitar erro no st.data_editor
        cols_num = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
    return df

# --- ABA CADASTRO ---
with tab1:
    st.header("Novo Cadastro")
    with st.form("cadastro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            est = st.text_input("Estabelecimento")
            dt = st.date_input("Data", value=date.today())
            br = st.text_input("Bairro")
            pg = st.selectbox("Pagamento", ["Pix", "Cartão", "Dinheiro", "Boleto"])
        with c2:
            prod = st.text_input("Produto")
            qtd = st.number_input("Quantidade", min_value=1)
            val = st.number_input("Valor Unitário", min_value=0.01)
            com = st.number_input("Comissão %", value=10.0)
        
        total = qtd * val
        v_com = total * (com / 100)
        
        if st.form_submit_button("Salvar Venda"):
            data = {
                "estabelecimento": est, "data_venda": dt.isoformat(), "bairro": br,
                "forma_pagamento": pg, "produto": prod, "quantidade": float(qtd),
                "valor_produto": float(val), "total_venda": float(total),
                "comissao_percentual": float(com), "valor_comissao": float(v_com), "status": "ativa"
            }
            supabase.table('vendas').insert(data).execute()
            st.success("Venda salva!")

# --- ABA EDIÇÃO/EXCLUSÃO ---
with tab2:
    st.header("Gerenciar Registros")
    df_atual = load_data()
    if not df_atual.empty:
        # Configuração das colunas
        config = {
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "data_venda": st.column_config.DateColumn("Data"),
            "total_venda": st.column_config.NumberColumn("Total (R$)", format="%.2f")
        }
        
        edited_df = st.data_editor(df_atual, num_rows="dynamic", column_config=config, use_container_width=True)

        if st.button("Sincronizar Banco de Dados"):
            # Deletar
            orig_ids = set(df_atual['id'].tolist())
            edit_ids = set(edited_df['id'].dropna().tolist())
            for rid in (orig_ids - edit_ids):
                supabase.table('vendas').delete().eq('id', rid).execute()
            
            # Atualizar/Inserir
                for _, row in edited_df.iterrows():
                    row_dict = row.to_dict()
                    if pd.isna(row['id']):
                        row_dict.pop('id')
                        supabase.table('vendas').insert(row_dict).execute()
                    else:
                        id_up = row_dict.pop('id')
                        supabase.table('vendas').update(row_dict).eq('id', id_up).execute()
            st.success("Sincronizado!")
            st.rerun()

# --- ABA RELATÓRIOS ---
with tab3:
    st.header("Análise de Dados")
    df_rel = load_data()
    if not df_rel.empty:
        c1, c2 = st.columns(2)
        d_ini = c1.date_input("Início", value=df_rel['data_venda'].min())
        d_fim = c2.date_input("Fim", value=date.today())
        
        df_f = df_rel[(df_rel['data_venda'] >= d_ini) & (df_rel['data_venda'] <= d_fim)]
        
        st.metric("Faturamento no Período", f"R$ {df_f['total_venda'].sum():.2f}")
        fig = px.bar(df_f, x="data_venda", y="total_venda", color="estabelecimento", title="Vendas por Dia")
        st.plotly_chart(fig, use_container_width=True)