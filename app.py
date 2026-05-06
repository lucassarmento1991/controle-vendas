import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from supabase import create_client, Client
from datetime import date

# 1. INICIALIZAÇÃO E GOVERNANÇA DE ACESSO
st.set_page_config(page_title="Controle de Vendas", layout="wide", page_icon="📊")

@st.cache_resource
def init_supabase():
    try:
        # Busca resiliente nos Secrets
        if "supabase" in st.secrets:
            url = st.secrets["supabase"]["url"].strip()
            key = st.secrets["supabase"]["key"].strip()
        else:
            url = st.secrets["SUPABASE_URL"].strip()
            key = st.secrets["SUPABASE_KEY"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro de Conexão: {str(e)}")
        st.stop()

supabase: Client = init_supabase()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 2. CONTROLE DE SESSÃO
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acesso Restrito")
    with st.form("login"):
        user = st.text_input("Usuário").strip()
        pw = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            try:
                # Sincronizado com tabela 'usuarios' e coluna 'username'
                res = supabase.table('usuarios').select('*').eq('username', user).execute()
                if res.data and res.data[0]['password_hash'] == hash_password(pw):
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")
            except Exception as e:
                st.error(f"Erro de Autenticação: {str(e)}")
    st.stop()

# 3. INTERFACE PRINCIPAL
st.sidebar.success(f"Logado como: {user if 'user' in locals() else 'Admin'}")
if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📝 Cadastro", "✏️ Edição em Massa", "📈 Relatórios"])

# Função de carregamento centralizada
def load_vendas():
    res = supabase.table('vendas').select('*').order('data_venda', desc=True).execute()
    return pd.DataFrame(res.data)

# --- ABA 1: CADASTRO ---
with tab1:
    st.header("Novo Registro de Venda")
    with st.form("form_cadastro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            est = st.text_input("Estabelecimento")
            dt = st.date_input("Data da Venda", value=date.today())
            br = st.text_input("Bairro")
            pg = st.selectbox("Forma de Pagamento", ["Pix", "Cartão", "Dinheiro", "Boleto"])
        with c2:
            prod = st.text_input("Produto")
            qtd = st.number_input("Quantidade", min_value=1, step=1)
            val = st.number_input("Valor Unitário (R$)", min_value=0.01, format="%.2f")
            com_p = st.number_input("Comissão (%)", min_value=0.0, max_value=100.0, value=10.0)

        total = qtd * val
        v_com = total * (com_p / 100)
        
        if st.form_submit_button("💾 Salvar no Banco", use_container_width=True):
            data = {
                "estabelecimento": est, "data_venda": dt.isoformat(), "bairro": br,
                "forma_pagamento": pg, "produto": prod, "quantidade": float(qtd),
                "valor_produto": float(val), "total_venda": float(total),
                "comissao_percentual": float(com_p), "valor_comissao": float(v_com),
                "status": "ativa"
            }
            supabase.table('vendas').insert(data).execute()
            st.success("Venda cadastrada!")

# --- ABA 2: EDIÇÃO E EXCLUSÃO EM MASSA ---
with tab2:
    st.header("Gerenciamento de Registros")
    st.info("💡 Edite as células diretamente ou selecione uma linha e aperte 'Delete' no teclado para excluir.")
    
    df_atual = load_vendas()
    if not df_atual.empty:
        # Configuração das colunas para o editor
        config = {
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "data_venda": st.column_config.DateColumn("Data"),
            "total_venda": st.column_config.NumberColumn("Total (R$)", format="%.2f"),
            "status": st.column_config.SelectboxColumn("Status", options=["ativa", "cancelada", "pendente"])
        }
        
        # Editor de Dados (CRUD em Massa)
        edited_df = st.data_editor(df_atual, num_rows="dynamic", column_config=config, use_container_width=True, key="vendas_editor")

        if st.button("🚀 Sincronizar Alterações com Supabase"):
            # 1. Detectar Exclusões (IDs que sumiram)
            ids_originais = set(df_atual['id'].tolist())
            ids_editados = set(edited_df['id'].dropna().tolist())
            ids_para_deletar = ids_originais - ids_editados
            
            for id_del in ids_para_deletar:
                supabase.table('vendas').delete().eq('id', id_del).execute()
            
            # 2. Detectar Updates e Inserts
            for _, row in edited_df.iterrows():
                row_data = row.to_dict()
                # Converte datas para string para o Supabase
                if isinstance(row_data['data_venda'], (date, datetime)):
                    row_data['data_venda'] = row_data['data_venda'].isoformat()
                
                if pd.isna(row['id']): # Nova linha (Insert)
                    row_data.pop('id')
                    supabase.table('vendas').insert(row_data).execute()
                else: # Linha existente (Update)
                    id_up = row_data.pop('id')
                    supabase.table('vendas').update(row_data).eq('id', id_up).execute()
            
            st.success("✅ Banco de dados sincronizado com sucesso!")
            st.rerun()

# --- ABA 3: RELATÓRIOS E FILTROS ---
with tab3:
    st.header("Relatórios Analíticos")
    df_rel = load_vendas()
    
    if not df_rel.empty:
        # Filtros Dinâmicos
        c1, c2, c3 = st.columns(3)
        with c1:
            d_ini = st.date_input("Início", value=df_rel['data_venda'].min())
        with c2:
            d_fim = st.date_input("Fim", value=date.today())
        with c3:
            filtro_est = st.multiselect("Estabelecimentos", options=df_rel['estabelecimento'].unique())

        # Aplicação dos Filtros
        df_f = df_rel[(df_rel['data_venda'].dt.date >= d_ini) & (df_rel['data_venda'].dt.date <= d_fim)]
        if filtro_est:
            df_f = df_f[df_f['estabelecimento'].isin(filtro_est)]

        # Métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento", f"R$ {df_f['total_venda'].sum():.2f}")
        m2.metric("Comissões", f"R$ {df_f['valor_comissao'].sum():.2f}")
        m3.metric("Qtd. Vendas", len(df_f))

        # Gráficos
        fig = px.bar(df_f, x="data_venda", y="total_venda", color="bairro", title="Evolução de Vendas por Bairro")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aguardando dados para gerar relatórios.")