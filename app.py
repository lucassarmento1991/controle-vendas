import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from supabase import create_client, Client
from datetime import datetime, timedelta, date

@st.cache_data
def get_supabase_url_and_key():
    keys_to_try = [
        ("SUPABASE_URL", "SUPABASE_KEY"),
        ("supabase", "url", "key")
    ]
    for path in keys_to_try:
        try:
            if len(path) == 2:
                url = st.secrets[path[0]].strip()
                key = st.secrets[path[1]].strip()
            else:
                url = st.secrets[path[0]][path[1]].strip()
                key = st.secrets[path[0]][path[2]].strip()
            return url, key
        except (KeyError, TypeError, AttributeError):
            continue
    st.error("Não foi possível encontrar as credenciais do Supabase nos secrets.")
    st.stop()

url, key = get_supabase_url_and_key()
supabase: Client = create_client(url, key)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def login_user(username: str, password: str, supabase: Client) -> bool:
    hash_pw = hash_password(password)
    response = supabase.table('usuarios').select('id').eq('username', username).eq('password', hash_pw).execute()
    return bool(response.data)

def load_data(supabase: Client) -> pd.DataFrame:
    response = supabase.table('vendas').select('*').order('data_venda').execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['data_venda'] = pd.to_datetime(df['data_venda'])
        numeric_cols = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

st.title("Sistema de Gerenciamento de Vendas")

if not st.session_state.logged_in:
    st.header("Login")
    with st.form("login_form"):
        username = st.text_input("Username", key="username_input")
        password = st.text_input("Senha", type="password", key="password_input")
        col1, col2, col3 = st.columns([1,1,2])
        with col2:
            submitted = st.form_submit_button("Entrar")
        if submitted:
            if username and password:
                if login_user(username, password, supabase):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas!")
            else:
                st.error("Preencha todos os campos.")
    st.stop()

# User is logged in
st.sidebar.title(f"Olá, {st.session_state.username}!")
if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

tabs = st.tabs(["Edição", "Relatórios"])

with tabs[0]:  # Edição
    st.header("Edição de Vendas")
    df = load_data(supabase)
    if df.empty:
        st.info("Nenhum dado encontrado. Adicione uma nova venda.")
    else:
        st.dataframe(df, use_container_width=True)

        column_config = {
            "id": st.column_config.TextColumn("ID", disabled=True),
            "estabelecimento": st.column_config.TextColumn("Estabelecimento", required=True),
            "data_venda": st.column_config.DateColumn("Data da Venda", required=True),
            "bairro": st.column_config.TextColumn("Bairro"),
            "forma_pagamento": st.column_config.SelectboxColumn(
                "Forma de Pagamento",
                options=["Dinheiro", "Pix", "Cartão", "Boleto", "Outros"]
            ),
            "produto": st.column_config.TextColumn("Produto", required=True),
            "quantidade": st.column_config.NumberColumn("Quantidade", min_value=1, required=True),
            "valor_produto": st.column_config.NumberColumn("Valor do Produto", min_value=0.01, step=0.01, required=True),
            "total_venda": st.column_config.NumberColumn("Total da Venda", step=0.01),
            "comissao_percentual": st.column_config.NumberColumn("Comissão %", min_value=0.0, max_value=100.0, format="%.2f%%"),
            "valor_comissao": st.column_config.NumberColumn("Valor da Comissão", step=0.01),
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=["Pendente", "Confirmado", "Cancelado"],
                required=True
            ),
        }

        edited_df = st.data_editor(
            df,
            column_config=column_config,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=False,
            key="data_editor"
        )

        if st.button("Salvar Alterações", type="primary"):
            if not edited_df.empty:
                original_ids = set(df['id'].astype(str).tolist())
                edited_ids = set(edited_df['id'].dropna().astype(str).tolist())

                # Deletes
                for id_to_del in original_ids - edited_ids:
                    supabase.table('vendas').delete().eq('id', id_to_del).execute()

                # Inserts and Updates
                for _, row in edited_df.iterrows():
                    row_dict = row.drop('id').to_dict()
                    # Clean NaN
                    row_dict = {k: v for k, v in row_dict.items() if pd.notna(v)}
                    if pd.isna(row['id']):
                        # Insert
                        supabase.table('vendas').insert(row_dict).execute()
                    else:
                        # Update
                        supabase.table('vendas').update(row_dict).eq('id', row['id']).execute()

                st.success("Alterações salvas com sucesso!")
                st.rerun()

with tabs[1]:  # Relatórios
    st.header("Relatórios")
    df = load_data(supabase)
    if df.empty:
        st.info("Nenhum dado para relatórios.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data Início", value=(datetime.now().date() - timedelta(days=30)))
        with col2:
            data_fim = st.date_input("Data Fim", value=datetime.now().date())

        col3, col4 = st.columns(2)
        with col3:
            estabelecimentos = st.multiselect(
                "Estabelecimento",
                options=sorted(df['estabelecimento'].dropna().unique())
            )
            bairros = st.multiselect(
                "Bairro",
                options=sorted(df['bairro'].dropna().unique())
            )
        with col4:
            forma_pagamento_opts = st.multiselect(
                "Forma Pagamento",
                options=sorted(df['forma_pagamento'].dropna().unique())
            )
            produtos = st.multiselect(
                "Produto",
                options=sorted(df['produto'].dropna().unique())
            )

        filtered_df = df[ (df['data_venda'].dt.date >= data_inicio) & (df['data_venda'].dt.date <= data_fim) ].copy()
        if estabelecimentos:
            filtered_df = filtered_df[filtered_df['estabelecimento'].isin(estabelecimentos)]
        if bairros:
            filtered_df = filtered_df[filtered_df['bairro'].isin(bairros)]
        if forma_pagamento_opts:
            filtered_df = filtered_df[filtered_df['forma_pagamento'].isin(forma_pagamento_opts)]
        if produtos:
            filtered_df = filtered_df[filtered_df['produto'].isin(produtos)]

        if filtered_df.empty:
            st.info("Nenhum dado encontrado com os filtros aplicados.")
        else:
            col1, col2, col3 = st.columns(3)
            total_vendas = filtered_df['total_venda'].sum()
            total_comissao = filtered_df['valor_comissao'].sum()
            num_vendas = len(filtered_df)
            with col1:
                st.metric("Total de Vendas", f"R$ {total_vendas:.2f}")
            with col2:
                st.metric("Total de Comissão", f"R$ {total_comissao:.2f}")
            with col3:
                st.metric("Número de Vendas", num_vendas)

            # Gráficos
            # Vendas por data
            sales_by_date = filtered_df.groupby(filtered_df['data_venda'].dt.date)['total_venda'].sum().reset_index(name='total_venda')
            sales_by_date.columns = ['data_venda', 'total_venda']
            sales_by_date['data_venda'] = pd.to_datetime(sales_by_date['data_venda'])
            fig1 = px.line(sales_by_date, x='data_venda', y='total_venda', title="Vendas por Data")
            st.plotly_chart(fig1, use_container_width=True)

            # Vendas por estabelecimento
            sales_by_est = filtered_df.groupby('estabelecimento')['total_venda'].sum().reset_index()
            fig2 = px.bar(sales_by_est, x='estabelecimento', y='total_venda', title="Vendas por Estabelecimento")
            st.plotly_chart(fig2, use_container_width=True)

            # Por forma de pagamento
            sales_by_pag = filtered_df.groupby('forma_pagamento')['total_venda'].sum().reset_index()
            fig3 = px.pie(sales_by_pag, names='forma_pagamento', values='total_venda', title="Distribuição por Forma de Pagamento")
            st.plotly_chart(fig3, use_container_width=True)

            # Vendas por bairro
            sales_by_bairro = filtered_df.groupby('bairro')['total_venda'].sum().reset_index()
            fig4 = px.bar(sales_by_bairro, x='bairro', y='total_venda', title="Vendas por Bairro")
            st.plotly_chart(fig4, use_container_width=True)

            # Comissão por produto
            comm_by_prod = filtered_df.groupby('produto')['valor_comissao'].sum().reset_index()
            fig5 = px.bar(comm_by_prod, x='produto', y='valor_comissao', title="Comissão por Produto")
            st.plotly_chart(fig5, use_container_width=True)