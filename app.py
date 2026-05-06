import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from supabase import create_client, Client
from datetime import date, datetime

# 1. INICIALIZAÇÃO RESILIENTE (Configurada para o bloco [supabase])
st.set_page_config(page_title="Controle de Vendas", layout="wide", page_icon="📊")

@st.cache_resource
def init_supabase():
    try:
        # Acesso direto ao bloco [supabase] conforme sua configuração
        url = st.secrets["supabase"]["url"].strip()
        key = st.secrets["supabase"]["key"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro de Conexão: Verifique se as chaves estão no bloco [supabase] nos Secrets. {str(e)}")
        st.stop()

supabase: Client = init_supabase()

# 2. AUTENTICAÇÃO VIA USERNAME
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Gestão de Vendas")
    with st.form("login_form"):
        # Alterado de e-mail para Username
        user_input = st.text_input("Usuário (Username)").strip()
        pass_input = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            try:
                # Busca na tabela 'usuarios' pela coluna 'username'
                res = supabase.table('usuarios').select('*').eq('username', user_input).execute()
                if res.data:
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
    st.header("Gerenciamento de Registros")
    st.warning("⚠️ Nesta aba a edição está desativada. Use o ícone de lixeira para excluir registros.")
    df_excluir = load_data()
    
    if not df_excluir.empty:
        # Todas as colunas desabilitadas para edição
        config_view = {col: st.column_config.Column(disabled=True) for col in df_excluir.columns}
        
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
            
            if ids_para_deletar:
                for rid in ids_para_deletar:
                    supabase.table('vendas').delete().eq('id', rid).execute()
                st.success(f"Registros excluídos com sucesso!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.info("Nenhuma alteração detectada.")

# --- ABA RELATÓRIOS (Filtros Expandidos) ---
with tab3:
    st.header("Análise de Dados")
    df_rel = load_data()
    
    if not df_rel.empty:
        # Painel de Filtros
        with st.expander("🔍 Filtros Avançados", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                d_ini = st.date_input("De:", value=df_rel['data_venda'].min())
                d_fim = st.date_input("Até:", value=date.today())
            with c2:
                f_est = st.multiselect("Estabelecimentos", options=df_rel['estabelecimento'].unique())
                f_bairro = st.multiselect("Bairros", options=df_rel['bairro'].unique())
            with c3:
                f_pag = st.multiselect("Formas de Pagamento", options=df_rel['forma_pagamento'].unique())

        # Aplicação dos filtros
        df_f = df_rel[(df_rel['data_venda'] >= d_ini) & (df_rel['data_venda'] <= d_fim)]
        if f_est: df_f = df_f[df_f['estabelecimento'].isin(f_est)]
        if f_bairro: df_f = df_f[df_f['bairro'].isin(f_bairro)]
        if f_pag: df_f = df_f[df_f['forma_pagamento'].isin(f_pag)]

        if not df_f.empty:
            # Métricas
            m1, m2, m3 = st.columns(3)
            m1.metric("Faturamento", f"R$ {df_f['total_venda'].sum():,.2f}")
            m2.metric("Comissões", f"R$ {df_f['valor_comissao'].sum():,.2f}")
            m3.metric("Total Vendas", len(df_f))

            # Gráficos
            fig = px.bar(df_f, x="data_venda", y="total_venda", color="estabelecimento", 
                         title="Evolução de Vendas por Período", barmode="group")
            st.plotly_chart(fig, use_container_width=True)
            
            c_g1, c_g2 = st.columns(2)
            with c_g1:
                fig_pag = px.pie(df_f, names="forma_pagamento", title="Distribuição por Pagamento")
                st.plotly_chart(fig_pag, use_container_width=True)
            with c_g2:
                fig_bairro = px.pie(df_f, names="bairro", title="Vendas por Bairro")
                st.plotly_chart(fig_bairro, use_container_width=True)
        else:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")