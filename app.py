import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from supabase import create_client, Client
import datetime

@st.cache_resource
def init_supabase():
    if 'supabase' in st.secrets:
        supabase_secrets = st.secrets['supabase']
        supabase_url = supabase_secrets.get('SUPABASE_URL', '').strip()
        supabase_key = supabase_secrets.get('SUPABASE_KEY', '').strip()
    else:
        supabase_url = st.secrets.get('SUPABASE_URL', '').strip()
        supabase_key = st.secrets.get('SUPABASE_KEY', '').strip()

    if not supabase_url or not supabase_key:
        st.error("Supabase credentials not found in secrets.")
        st.stop()

    return create_client(supabase_url, supabase_key)

# Initialize session state
if 'client' not in st.session_state:
    st.session_state.client = init_supabase()
client: Client = st.session_state.client

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

st.title("Sistema de Controle de Vendas V3.3 (Resili\u00eancia de Secrets e CRUD Est\u00e1vel)")

if not st.session_state.logged_in:
    st.header("Login")
    col1, col2 = st.columns([3, 1])
    with col1:
        username = st.text_input("Usu\u00e1rio", key="login_user")
    with col2:
        password = st.text_input("Senha", type="password", key="login_pass")
    if st.button("Entrar"):
        if username and password:
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            response = client.table('usuarios').select('*').eq('usuario', username).eq('senha', hashed_pw).execute()
            if response.data:
                st.session_state.logged_in = True
                st.session_state.user = username
                st.rerun()
        else:
            st.error("Preencha usu\u00e1rio e senha.")
    st.stop()

# Logout
col1, col2 = st.columns([1, 8])
with col1:
    if st.button("Logout"):
        del st.session_state['logged_in']
        del st.session_state['user']
        st.rerun()

@st.cache_data(ttl=60)
def load_data():
    response = client.table('vendas').select('*').order('data_venda', desc=True).execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['data_venda'] = pd.to_datetime(df['data_venda'], errors='coerce')
    return df

tab1, tab2 = st.tabs(["Edi\u00e7\u00e3o", "Relat\u00f3rios"])

with tab1:
    st.header("CRUD de Vendas")
    df = load_data()

    column_config = {
        "id": st.column_config.TextColumn("ID", disabled=True, width="medium"),
        "estabelecimento": st.column_config.TextColumn("Estabelecimento", width="medium"),
        "data_venda": st.column_config.DateColumn("Data da Venda"),
        "bairro": st.column_config.TextColumn("Bairro"),
        "forma_pagamento": st.column_config.TextColumn("Forma de Pagamento"),
        "produto": st.column_config.TextColumn("Produto"),
        "quantidade": st.column_config.NumberColumn("Quantidade", min_value=0, step=1, format="%.0f"),
        "valor_produto": st.column_config.NumberColumn("Valor Produto", min_value=0.0, step=0.01, format="%.2f"),
        "total_venda": st.column_config.NumberColumn("Total Venda", min_value=0.0, step=0.01, format="%.2f"),
        "comissao_percentual": st.column_config.NumberColumn("Comiss\u00e3o %", min_value=0.0, step=0.1, format="%.1f"),
        "valor_comissao": st.column_config.NumberColumn("Valor Comiss\u00e3o", min_value=0.0, step=0.01, format="%.2f"),
        "status": st.column_config.TextColumn("Status"),
    }

    edited_df = st.data_editor(
        df,
        column_config=column_config,
        use_container_width=True,
        hide_index=False,
        key="data_editor"
    )

    if st.button("Salvar Altera\u00e7\u00f5es"):
        orig_ids = set(df['id'].dropna().astype(str))
        curr_ids = set(edited_df['id'].dropna().astype(str))
        deleted_ids = orig_ids - curr_ids

        # Delete
        if deleted_ids:
            client.table('vendas').delete().in_('id', list(deleted_ids)).execute()

        # Added (id NaN)
        added_df = edited_df[edited_df['id'].isna()]
        if not added_df.empty:
            for _, row in added_df.iterrows():
                data = row.drop('id').to_dict()
                if pd.notna(data['data_venda']):
                    data['data_venda'] = pd.Timestamp(data['data_venda']).isoformat()
                else:
                    data['data_venda'] = None
                client.table('vendas').insert(data).execute()

        # Updated/Upsert
        updated_df = edited_df[~edited_df['id'].isna()]
        if not updated_df.empty:
            data_list = []
            for _, row in updated_df.iterrows():
                data = row.to_dict()
                if pd.notna(data['data_venda']):
                    data['data_venda'] = pd.Timestamp(data['data_venda']).isoformat()
                else:
                    data['data_venda'] = None
                data_list.append(data)
            client.table('vendas').upsert(data_list, on_conflict='id').execute()

        st.success("Altera\u00e7\u00f5es salvas com sucesso!")
        st.rerun()

with tab2:
    st.header("Relat\u00f3rios")
    df_report = load_data()
    if df_report.empty:
        st.info("Nenhum registro de vendas encontrado.")
        st.stop()

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        unique_estabs = sorted(df_report['estabelecimento'].unique())
        estabs = st.multiselect("Estabelecimento", options=unique_estabs)
    with col2:
        unique_bairros = sorted(df_report['bairro'].dropna().unique())
        bairros = st.multiselect("Bairro", options=unique_bairros)
    with col3:
        unique_status = sorted(df_report['status'].unique())
        status_filter = st.multiselect("Status", options=unique_status)

    col1, col2 = st.columns(2)
    min_date = df_report['data_venda'].min().date()
    max_date = df_report['data_venda'].max().date()
    with col1:
        data_ini = st.date_input("Data Inicial", value=min_date, min_value=min_date, max_value=max_date)
    with col2:
        data_fim = st.date_input("Data Final", value=max_date, min_value=min_date, max_value=max_date)

    df_filt = df_report.copy()
    if estabs:
        df_filt = df_filt[df_filt['estabelecimento'].isin(estabs)]
    if bairros:
        df_filt = df_filt[df_filt['bairro'].isin(bairros)]
    if status_filter:
        df_filt = df_filt[df_filt['status'].isin(status_filter)]
    df_filt = df_filt[(df_filt['data_venda'].dt.date >= data_ini) & (df_filt['data_venda'].dt.date <= data_fim)]

    if df_filt.empty:
        st.info("Nenhum dado com os filtros selecionados.")
        st.stop()

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    total_vendas = df_filt['total_venda'].sum()
    total_comissao = df_filt['valor_comissao'].sum()
    qtd_vendas = len(df_filt)
    qtd_produtos = df_filt['quantidade'].sum()

    with col1:
        st.metric("Total Vendas", f"R$ {total_vendas:,.2f}")
    with col2:
        st.metric("Total Comiss\u00f5es", f"R$ {total_comissao:,.2f}")
    with col3:
        st.metric("Qtd. Vendas", qtd_vendas)
    with col4:
        st.metric("Qtd. Produtos", f"{qtd_produtos:,.0f}")

    # Charts
    st.subheader("Vendas por Estabelecimento")
    vendas_estab = df_filt.groupby('estabelecimento')['total_venda'].sum().reset_index()
    fig1 = px.bar(vendas_estab, x='estabelecimento', y='total_venda', title="Total de Vendas por Estabelecimento")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Distribui\u00e7\u00e3o por Forma de Pagamento")
    fig2 = px.pie(df_filt, names='forma_pagamento', values='total_venda', title="Vendas por Forma de Pagamento")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Vendas ao Longo do Tempo")
    daily_sales = df_filt.groupby(df_filt['data_venda'].dt.date)['total_venda'].sum().sort_index().reset_index()
    daily_sales.columns = ['data_venda', 'total_venda']
    fig3 = px.line(daily_sales, x='data_venda', y='total_venda', title="Vendas Di\u00e1rias")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Top 10 Produtos")
    top_produtos = df_filt.groupby('produto')['total_venda'].sum().sort_values(ascending=False).head(10).reset_index()
    fig4 = px.bar(top_produtos, x='produto', y='total_venda', title="Top 10 Produtos por Valor de Venda")
    st.plotly_chart(fig4, use_container_width=True)

    st.subheader("Comiss\u00f5es por Estabelecimento")
    comissao_estab = df_filt.groupby('estabelecimento')['valor_comissao'].sum().reset_index()
    fig5 = px.bar(comissao_estab, x='estabelecimento', y='valor_comissao', title="Comiss\u00f5es por Estabelecimento")
    st.plotly_chart(fig5, use_container_width=True)