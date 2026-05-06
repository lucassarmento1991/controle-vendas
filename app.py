import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hashlib
from supabase import create_client, Client
from datetime import date, datetime
import numpy as np

# Initialize Supabase
supabase_config = st.secrets.get('supabase', {})
url = supabase_config.get('url', '').strip()
key = supabase_config.get('key', '').strip()
supabase: Client = create_client(url, key)

# Session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

# Login
if not st.session_state.logged_in:
    st.title('Login')
    with st.form('login_form'):
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        submitted = st.form_submit_button('Entrar')
        if submitted:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            result = supabase.table('usuarios').select('username').eq('username', username).eq('password_hash', password_hash).execute()
            if result.data:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success('Login realizado com sucesso!')
                st.rerun()
    st.stop()

# Logout button
st.sidebar.title(f'Bem-vindo, {st.session_state.username}')
if st.sidebar.button('Logout'):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

@st.cache_data
def load_data():
    result = supabase.table('vendas').select('*').order('data_venda', desc=True).execute()
    if not result.data:
        return pd.DataFrame()
    df = pd.DataFrame(result.data)
    if 'id' in df.columns:
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
    if 'data_venda' in df.columns:
        df['data_venda'] = pd.to_datetime(df['data_venda'], errors='coerce').dt.date
    numeric_cols = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    required_cols = ['estabelecimento', 'data_venda', 'bairro', 'forma_pagamento', 'produto', 'quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao', 'status']
    for col in required_cols:
        if col not in df.columns:
            df[col] = np.nan
    return df

st.title('Gerenciador de Vendas')

# Tabs
tab1, tab2 = st.tabs(['Edição', 'Relatórios'])

with tab1:
    st.header('Editar Vendas')
    df_original = load_data()
    if df_original.empty:
        st.info('Nenhum dado encontrado.')
    else:
        column_config = {
            'id': st.column_config.NumberColumn('ID', disabled=True),
            'data_venda': st.column_config.DateColumn('Data da Venda'),
            'quantidade': st.column_config.NumberColumn('Quantidade', min_value=0, step=1),
            'valor_produto': st.column_config.NumberColumn('Valor Produto', min_value=0.0, step=0.01, format='%.2f'),
            'total_venda': st.column_config.NumberColumn('Total Venda', min_value=0.0, step=0.01, format='%.2f'),
            'comissao_percentual': st.column_config.NumberColumn('Comissão %', min_value=0.0, max_value=100.0, step=0.1, format='%.1f'),
            'valor_comissao': st.column_config.NumberColumn('Valor Comissão', min_value=0.0, step=0.01, format='%.2f'),
            'status': st.column_config.SelectboxColumn('Status', options=['Pendente', 'Aprovado', 'Cancelado'])
        }
        edited_df = st.data_editor(
            df_original,
            column_config=column_config,
            num_rows='dynamic',
            use_container_width=True,
            hide_index=False,
            key='data_editor'
        )

        if st.button('Salvar Alterações', type='primary'):
            if not edited_df.empty:
                original_ids = set(df_original['id'].dropna().astype(int).astype(str))
                edited_ids = set(edited_df['id'].dropna().astype(int).astype(str))

                # Deletions
                deleted_ids = original_ids - edited_ids
                for rid in deleted_ids:
                    supabase.table('vendas').delete().eq('id', int(rid)).execute()

                # Inserts and Updates
                for _, row in edited_df.iterrows():
                    row_dict = row.to_dict()
                    row_id = row_dict.pop('id', None)
                    if pd.isna(row_id) or row_id == 0:
                        # Insert
                        supabase.table('vendas').insert(row_dict).execute()
                    else:
                        # Update
                        supabase.table('vendas').update(row_dict).eq('id', int(row_id)).execute()

                st.success('Alterações salvas com sucesso!')
                st.cache_data.clear()
                st.rerun()

with tab2:
    st.header('Relatórios Avançados')
    df = load_data()
    if df.empty:
        st.info('Nenhum dado para relatórios.')
    else:
        col1, col2 = st.columns(2)
        with col1:
            min_date = df['data_venda'].min().date()
            max_date = df['data_venda'].max().date()
            date_start = st.date_input('Data Início', value=min_date, min_value=min_date, max_value=max_date)
            date_end = st.date_input('Data Fim', value=max_date, min_value=min_date, max_value=max_date)
        with col2:
            pass  # for balance

        col1, col2, col3, col4 = st.columns(4)
        est_opts = sorted(df['estabelecimento'].dropna().unique())
        selected_est = st.multiselect('Estabelecimento', est_opts, default=est_opts, key='est')

        bairro_opts = sorted(df['bairro'].dropna().unique())
        selected_bairro = st.multiselect('Bairro', bairro_opts, default=bairro_opts, key='bairro')

        pag_opts = sorted(df['forma_pagamento'].dropna().unique())
        selected_pag = st.multiselect('Forma Pagamento', pag_opts, default=pag_opts, key='pag')

        prod_opts = sorted(df['produto'].dropna().unique())
        selected_prod = st.multiselect('Produto', prod_opts, default=prod_opts, key='prod')

        # Filter data
        filtered = df[(
            (df['data_venda'] >= date_start) &
            (df['data_venda'] <= date_end)
        )].copy()

        if selected_est:
            filtered = filtered[filtered['estabelecimento'].isin(selected_est)]
        if selected_bairro:
            filtered = filtered[filtered['bairro'].isin(selected_bairro)]
        if selected_pag:
            filtered = filtered[filtered['forma_pagamento'].isin(selected_pag)]
        if selected_prod:
            filtered = filtered[filtered['produto'].isin(selected_prod)]

        if filtered.empty:
            st.info('Nenhum dado com os filtros aplicados.')
        else:
            col_a, col_b, col_c = st.columns(3)
            total_faturamento = filtered['total_venda'].sum()
            total_comissao = filtered['valor_comissao'].sum()
            qtd_vendas = len(filtered)

            with col_a:
                st.metric('Faturamento Total', f'R$ {total_faturamento:,.2f}')
            with col_b:
                st.metric('Comissão Total', f'R$ {total_comissao:,.2f}')
            with col_c:
                st.metric('Qtd Vendas', qtd_vendas)

            # Charts
            col1, col2 = st.columns(2)
            with col1:
                fat_por_est = filtered.groupby('estabelecimento')['total_venda'].sum().reset_index()
                fig_bar = px.bar(fat_por_est, x='estabelecimento', y='total_venda', title='Faturamento por Estabelecimento')
                st.plotly_chart(fig_bar, use_container_width=True)

            with col2:
                fat_por_data = filtered.groupby('data_venda')['total_venda'].sum().reset_index()
                fig_line = px.line(fat_por_data, x='data_venda', y='total_venda', title='Faturamento por Data')
                st.plotly_chart(fig_line, use_container_width=True)

            col3, col4 = st.columns(2)
            with col3:
                pag_group = filtered.groupby('forma_pagamento')['total_venda'].sum().reset_index()
                fig_pie = px.pie(pag_group, names='forma_pagamento', values='total_venda', title='Faturamento por Forma de Pagamento')
                st.plotly_chart(fig_pie, use_container_width=True)

            with col4:
                prod_group = filtered.groupby('produto')['quantidade'].sum().reset_index()
                fig_prod = px.bar(prod_group, x='produto', y='quantidade', title='Quantidade por Produto')
                st.plotly_chart(fig_prod, use_container_width=True)