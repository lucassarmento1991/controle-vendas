import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib
from datetime import date

st.set_page_config(page_title="App Vendas", page_icon="📊", layout="wide")

# Config Supabase
url = st.secrets["SUPABASE_URL"].strip()
key = st.secrets["SUPABASE_KEY"].strip()
supabase: Client = create_client(url, key)

# Colunas padronizadas
required_columns = [
    'id', 'estabelecimento', 'data_venda', 'bairro', 'forma_pagamento',
    'produto', 'quantidade', 'valor_produto', 'total_venda',
    'comissao_percentual', 'valor_comissao', 'status'
]

@st.cache_data(ttl=600)
def load_data():
    response = supabase.table("vendas").select("*").order("data_venda", desc=True).execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['data_venda'] = pd.to_datetime(df['data_venda'], errors='coerce').dt.date
    # Garantir colunas
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    df = df.reindex(columns=required_columns, fill_value=None)
    return df

# Login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if username and password:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            users = st.secrets.get("USERS", {})
            if username in users and users[username] == hashed_password:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Credenciais inválidas!")
    st.stop()

st.title("📊 App de Vendas - Lucas")

# Logout
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.rerun()

# Tabs
tab1, tab2 = st.tabs(["✏️ Edição", "📈 Relatórios"])

with tab1:
    st.subheader("Editar Vendas")
    df = load_data()

    column_config = {
        "id": st.column_config.NumberColumn("ID", disabled=True, required=False),
        "data_venda": st.column_config.DateColumn("Data da Venda", required=True),
        "estabelecimento": st.column_config.TextColumn("Estabelecimento", required=True),
        "bairro": st.column_config.TextColumn("Bairro"),
        "forma_pagamento": st.column_config.TextColumn("Forma de Pagamento"),
        "produto": st.column_config.TextColumn("Produto", required=True),
        "quantidade": st.column_config.NumberColumn("Quantidade", min_value=0, required=True),
        "valor_produto": st.column_config.NumberColumn("Valor Produto", min_value=0),
        "total_venda": st.column_config.NumberColumn("Total Venda", min_value=0),
        "comissao_percentual": st.column_config.NumberColumn("Comissão %", min_value=0, max_value=100, format="%.2f%%"),
        "valor_comissao": st.column_config.NumberColumn("Valor Comissão", min_value=0),
        "status": st.column_config.SelectboxColumn("Status", options=["Pendente", "Pago", "Cancelado"], required=True)
    }

    edited_df = st.data_editor(
        df,
        column_config=column_config,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=False
    )

    if st.button("💾 Salvar Alterações", type="primary"):
        # Detectar linhas removidas
        old_ids = {str(int(id)) for id in df['id'].dropna() if pd.notna(id)}
        new_ids = {str(int(id)) for id in edited_df['id'].dropna() if pd.notna(id)}
        removed_ids = old_ids - new_ids
        for rid in removed_ids:
            supabase.table("vendas").delete().eq("id", int(rid)).execute()

        # Inserts (id NaN)
        new_rows = edited_df[edited_df['id'].isna()]
        for _, row in new_rows.iterrows():
            insert_data = row.drop('id').to_dict()
            insert_data['data_venda'] = row['data_venda'].isoformat()
            insert_data = {k: None if pd.isna(v) else v for k, v in insert_data.items()}
            supabase.table("vendas").insert(insert_data).execute()

        # Updates (id not NaN)
        update_rows = edited_df[edited_df['id'].notna()]
        for _, row in update_rows.iterrows():
            update_data = row.drop('id').to_dict()
            update_data['data_venda'] = row['data_venda'].isoformat()
            update_data = {k: None if pd.isna(v) else v for k, v in update_data.items()}
            supabase.table("vendas").update(update_data).eq("id", int(row['id'])).execute()

        st.success("✅ Alterações salvas com sucesso!")
        st.rerun()

with tab2:
    st.subheader("Relatórios")
    df = load_data()
    if df.empty:
        st.info("Nenhum dado disponível.")
        st.stop()

    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        min_date = df['data_venda'].min()
        max_date = df['data_venda'].max()
        data_inicio = st.date_input("Data Início", value=min_date, min_value=min_date, max_value=max_date)
        data_fim = st.date_input("Data Fim", value=max_date, min_value=min_date, max_value=max_date)

    col3, col4 = st.columns(2)
    with col3:
        estab_opts = sorted(df['estabelecimento'].dropna().unique())
        estabelecimentos = st.multiselect("Estabelecimento", options=estab_opts, default=estab_opts)

        bairro_opts = sorted(df['bairro'].dropna().unique())
        bairros = st.multiselect("Bairro", options=bairro_opts, default=bairro_opts)

    with col4:
        forma_opts = sorted(df['forma_pagamento'].dropna().unique())
        formas_pag = st.multiselect("Forma de Pagamento", options=forma_opts, default=forma_opts)

        prod_opts = sorted(df['produto'].dropna().unique())
        produtos = st.multiselect("Produto", options=prod_opts, default=prod_opts)

    # Aplicar filtros
    mask = (
        (df['data_venda'] >= data_inicio) &
        (df['data_venda'] <= data_fim) &
        (df['estabelecimento'].isin(estabelecimentos)) &
        (df['bairro'].isin(bairros)) &
        (df['forma_pagamento'].isin(formas_pag)) &
        (df['produto'].isin(produtos))
    )
    filtered_df = df[mask].copy()

    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    total_vendas = filtered_df['total_venda'].sum()
    total_comissao = filtered_df['valor_comissao'].sum()
    qtd_vendas = len(filtered_df)
    total_qtd = filtered_df['quantidade'].sum()

    col1.metric("💰 Total Vendas", f"R$ {total_vendas:,.2f}")
    col2.metric("💵 Total Comissões", f"R$ {total_comissao:,.2f}")
    col3.metric("📦 Qtd. Vendas", qtd_vendas)
    col4.metric("📊 Qtd. Produtos", int(total_qtd))

    st.markdown("---")

    # Tabela
    st.subheader("Dados Filtrados")
    st.dataframe(filtered_df, use_container_width=True)

    st.markdown("---")

    # Gráficos
    st.subheader("Gráficos")
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        fig1 = px.bar(filtered_df, x="produto", y="total_venda", color="estabelecimento",
                      title="Vendas por Produto")
        st.plotly_chart(fig1, use_container_width=True)

    with col_g2:
        vendas_por_data = filtered_df.groupby('data_venda')['total_venda'].sum().reset_index()
        fig2 = px.line(vendas_por_data, x='data_venda', y='total_venda', title="Vendas por Data")
        st.plotly_chart(fig2, use_container_width=True)

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        fig3 = px.pie(filtered_df, names="forma_pagamento", values="total_venda",
                      title="Distribuição por Forma de Pagamento")
        st.plotly_chart(fig3, use_container_width=True)

    with col_g4:
        fig4 = px.pie(filtered_df, names="estabelecimento", values="total_venda",
                      title="Distribuição por Estabelecimento")
        st.plotly_chart(fig4, use_container_width=True)