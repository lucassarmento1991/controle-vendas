import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from supabase import create_client
from datetime import date

st.set_page_config(page_title="App Lucas - Governanca", layout="wide")

@st.cache_data
def load_data():
    supabase = init_supabase()
    columns = 'id,estabelecimento,data_venda,bairro,forma_pagamento,produto,quantidade,valor_produto,total_venda,comissao_percentual,valor_comissao,status'
    response = supabase.table('vendas').select(columns).execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['data_venda'] = pd.to_datetime(df['data_venda'])
        df['total_venda'] = pd.to_numeric(df['total_venda'], errors='coerce')
        df['valor_comissao'] = pd.to_numeric(df['valor_comissao'], errors='coerce')
        df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce')
    return df

def init_supabase():
    try:
        url = st.secrets['SUPABASE_URL'].strip()
    except KeyError:
        try:
            url = st.secrets['supabase']['url'].strip()
        except KeyError:
            st.error("Supabase URL not found in secrets.")
            st.stop()
    try:
        key = st.secrets['SUPABASE_KEY'].strip()
    except KeyError:
        try:
            key = st.secrets['supabase']['anon_key'].strip() or st.secrets['supabase']['key'].strip()
        except KeyError:
            st.error("Supabase key not found.")
            st.stop()
    return create_client(url, key)

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def authenticate(username, password):
    supabase = init_supabase()
    hashed_pw = hash_password(password)
    response = supabase.table('usuarios').select('id').eq('username', username).eq('password_hash', hashed_pw).execute()
    return len(response.data) > 0

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login - App para Lucas (Analista de Governança)")
    username = st.text_input("Username", placeholder="paodequeijo")
    password = st.text_input("Password", type="password")
    if st.button("Entrar"):
        if authenticate(username, password):
            st.session_state.logged_in = True
            st.success("Login bem-sucedido!")
            st.rerun()
        else:
            st.error("Credenciais inválidas.")
    st.stop()

st.title("App para Lucas - Analista de Governança")

tab1, tab2 = st.tabs(["Gerenciar Registros", "Relatórios"])

with tab1:
    st.header("Gerenciar Registros (Apenas Exclusão)")
    df = load_data()
    if df.empty:
        st.warning("Nenhum dado encontrado.")
    else:
        column_config = {col: st.column_config.Column(disabled=True) for col in df.columns}
        original_df = df.copy()
        edited_df = st.data_editor(
            df,
            column_config=column_config,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=False,
        )
        if st.button("Aplicar Exclusões", type="primary"):
            supabase = init_supabase()
            original_ids = set(original_df['id'])
            edited_ids = set(edited_df['id'])
            deleted_ids = original_ids - edited_ids
            if deleted_ids:
                for id_val in deleted_ids:
                    supabase.table('vendas').delete().eq('id', id_val).execute()
                st.cache_data.clear()
                st.success(f"{len(deleted_ids)} registros excluídos com sucesso!")
                st.rerun()
            else:
                st.info("Nenhuma exclusão detectada.")

with tab2:
    st.header("Relatórios")
    df = load_data()
    if df.empty:
        st.warning("Nenhum dado para relatorios.")
    else:
        estabelecimentos = sorted(df['estabelecimento'].dropna().unique())
        formas_pagamento = sorted(df['forma_pagamento'].dropna().unique())
        bairros = sorted(df['bairro'].dropna().unique())

        col1, col2, col3 = st.columns(3)
        with col1:
            est_sel = st.multiselect("Estabelecimento", estabelecimentos, default=estabelecimentos)
        with col2:
            form_sel = st.multiselect("Forma de Pagamento", formas_pagamento, default=formas_pagamento)
        with col3:
            bai_sel = st.multiselect("Bairro", bairros, default=bairros)

        col4, col5 = st.columns(2)
        min_date = df['data_venda'].min().date()
        max_date = df['data_venda'].max().date()
        with col4:
            data_inicio = st.date_input("Data Início", value=min_date, min_value=min_date, max_value=max_date)
        with col5:
            data_fim = st.date_input("Data Fim", value=max_date, min_value=min_date, max_value=max_date)

        mask = (
            df['estabelecimento'].isin(est_sel) &
            df['forma_pagamento'].isin(form_sel) &
            df['bairro'].isin(bai_sel) &
            (df['data_venda'].dt.date >= data_inicio) &
            (df['data_venda'].dt.date <= data_fim)
        )
        filtered_df = df[mask].copy()

        if filtered_df.empty:
            st.warning("Nenhum dado corresponde aos filtros.")
        else:
            faturamento = filtered_df['total_venda'].sum()
            comissao = filtered_df['valor_comissao'].sum()
            qtd = filtered_df['quantidade'].sum()

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Faturamento", f"R$ {faturamento:,.2f}")
            col_b.metric("Comissão", f"R$ {comissao:,.2f}")
            col_c.metric("Quantidade", f"{qtd:,.0f}")

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig1 = px.bar(
                    filtered_df.groupby('estabelecimento')['total_venda'].sum().reset_index(),
                    x='estabelecimento',
                    y='total_venda',
                    title="Faturamento por Estabelecimento"
                )
                st.plotly_chart(fig1, use_container_width=True)
            with col_g2:
                fig2 = px.pie(filtered_df, names='forma_pagamento', values='total_venda', title="Distribuição por Forma de Pagamento")
                st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Faturamento por Bairro")
            fig3 = px.bar(
                filtered_df.groupby('bairro')['total_venda'].sum().reset_index(),
                x='bairro',
                y='total_venda',
                title="Faturamento por Bairro"
            )
            st.plotly_chart(fig3, use_container_width=True)