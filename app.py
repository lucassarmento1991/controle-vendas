import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from supabase import create_client, Client
from datetime import date, datetime

# 1. INICIALIZAÇÃO DO SUPABASE
st.set_page_config(page_title="Controle de Vendas", layout="wide", page_icon="📊")

@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"].strip()
        key = st.secrets["supabase"]["key"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro de Conexão: Verifique os Secrets. {str(e)}")
        st.stop()

supabase: Client = init_supabase()

# 2. AUTENTICAÇÃO (Sincronizada com o seu Hash do Banco)
def hash_password(password):
    # Gera o hash SHA-256 padrão
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Gestão de Vendas")
    with st.form("login_form"):
        user_input = st.text_input("Usuário (Username)").strip()
        pass_input = st.text_input("Senha", type="password")
        
        if st.form_submit_button("Entrar", use_container_width=True):
            try:
                res = supabase.table('usuarios').select('*').eq('username', user_input).execute()
                
                if res.data:
                    # Hash informado pelo usuário como estando no banco:
                    # ad1e10c7f2d809520c2191e442ed016ed7507debeaad03d061a97ec69dc2361e
                    hash_no_banco = res.data[0]['password_hash']
                    hash_digitado = hash_password(pass_input)
                    
                    if hash_no_banco == hash_digitado:
                        st.session_state.logged_in = True
                        st.session_state.username = user_input
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                        # Debug comparativo para o administrador
                        st.info(f"Hash digitado: {hash_digitado}")
                        st.info(f"Hash no banco: {hash_no_banco}")
                else:
                    st.error("Usuário não encontrado.")
            except Exception as e:
                st.error(f"Erro de login: {str(e)}")
    st.stop()

# 3. CARREGAMENTO DE DADOS
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

# Interface Principal
st.sidebar.title(f"👤 {st.session_state.username}")
if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

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

# --- ABA GERENCIAR (Somente Exclusão) ---
with tab2:
    st.header("Exclusão de Registros")
    df_excluir = load_data()
    if not df_excluir.empty:
        config_view = {col: st.column_config.Column(disabled=True) for col in df_excluir.columns}
        edited_df = st.data_editor(df_excluir, num_rows="dynamic", column_config=config_view, use_container_width=True, hide_index=True)

        if st.button("🗑️ Confirmar Exclusões no Banco", type="primary"):
            orig_ids = set(df_excluir['id'].tolist())
            curr_ids = set(edited_df['id'].dropna().tolist())
            ids_para_deletar = orig_ids - curr_ids
            if ids_para_deletar:
                for rid in ids_para_deletar:
                    supabase.table('vendas').delete().eq('id', rid).execute()
                st.success("Excluído com sucesso!")
                st.cache_data.clear()
                st.rerun()

# --- ABA RELATÓRIOS ---
with tab3:
    st.header("Análise de Dados")
    df_rel = load_data()
    if not df_rel.empty:
        with st.expander("🔍 Filtros Avançados", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                d_ini = st.date_input("Início", value=df_rel['data_venda'].min())
                d_fim = st.date_input("Fim", value=date.today())
            with c2:
                f_est = st.multiselect("Estabelecimentos", options=sorted(df_rel['estabelecimento'].unique()))
            with c3:
                f_pg = st.multiselect("Pagamento", options=sorted(df_rel['forma_pagamento'].unique()))
        
        df_f = df_rel[(df_rel['data_venda'] >= d_ini) & (df_rel['data_venda'] <= d_fim)]
        if f_est: df_f = df_f[df_f['estabelecimento'].isin(f_est)]
        if f_pg: df_f = df_f[df_f['forma_pagamento'].isin(f_pg)]
        
        if not df_f.empty:
            m1, m2 = st.columns(2)
            m1.metric("Faturamento Total", f"R$ {df_f['total_venda'].sum():,.2f}")
            m2.metric("Comissões Totais", f"R$ {df_f['valor_comissao'].sum():,.2f}")
            st.plotly_chart(px.bar(df_f, x="data_venda", y="total_venda", color="estabelecimento", title="Vendas por Período"), use_container_width=True)