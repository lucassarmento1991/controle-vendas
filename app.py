import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
import hashlib
from datetime import date, timedelta
import numpy as np

@st.cache_data
def load_vendas(supabase, cache_buster=0):
    response = supabase.table('vendas').select('*').order('id', desc=False).execute()
    if not response.data:
        return pd.DataFrame()
    df = pd.DataFrame(response.data)
    float_cols = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    if 'data_venda' in df.columns:
        df['data_venda'] = pd.to_datetime(df['data_venda'], errors='coerce')
    if 'id' in df.columns:
        df['id'] = pd.to_numeric(df['id'], errors='coerce').astype('Int64')
    return df

def get_supabase():
    def get_secret(key):
        try:
            return st.secrets['supabase'][key].strip()
        except (KeyError, TypeError):
            try:
                return st.secrets[key].strip()
            except (KeyError, AttributeError):
                st.error(f'Secret {key} not found.')
                st.stop()
    url = get_secret('url')
    key = get_secret('key')
    return create_client(url, key)

def perform_login(supabase):
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if not st.session_state.logged_in:
        st.title('Login')
        with st.form('login_form'):
            username = st.text_input('Username')
            password = st.text_input('Password', type='password')
            if st.form_submit_button('Entrar'):
                if username and password:
                    pw_hash = hashlib.sha256(password.encode()).hexdigest()
                    response = supabase.table('usuarios').select('password_hash').eq('username', username).execute()
                    if response.data and response.data[0]['password_hash'] == pw_hash:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.success('Login realizado com sucesso!')
                        st.rerun()
                    else:
                        st.error('Usuário ou senha inválidos.')
                else:
                    st.error('Preencha todos os campos.')
        st.stop()
    else:
        col1, col2 = st.columns([4,1])
        with col2:
            if st.button('Logout'):
                st.session_state.logged_in = False
                st.session_state.username = None
                st.rerun()
        with col1:
            st.info(f'Bem-vindo, {st.session_state.username}!')

st.set_page_config(page_title='Controle de Vendas', layout='wide')

supabase = get_supabase()
perform_login(supabase)

if 'cache_buster' not in st.session_state:
    st.session_state.cache_buster = 0

df = load_vendas(supabase, st.session_state.cache_buster)

st.title('Sistema de Controle de Vendas')

tab1, tab2, tab3 = st.tabs(['📝 Cadastro', '✏️ Edição em Massa', '📊 Relatórios'])

with tab1:
    st.header('Novo Cadastro')
    with st.form('cadastro_form'):
        col1, col2 = st.columns(2)
        estabelecimento = col1.text_input('Estabelecimento')
        data_venda = col1.date_input('Data da Venda', value=date.today())
        bairro = col2.text_input('Bairro')
        forma_pagamento = col2.selectbox('Forma de Pagamento', ['Dinheiro', 'Pix', 'Cartão'])
        produto = st.text_input('Produto')
        col3, col4, col5 = st.columns(3)
        quantidade = col3.number_input('Quantidade', min_value=0.0, format='%.2f')
        valor_produto = col4.number_input('Valor do Produto', min_value=0.0, format='%.2f')
        comissao_percentual = col5.number_input('Comissão %', min_value=0.0, max_value=100.0, value=5.0, format='%.2f')
        total_venda = quantidade * valor_produto
        valor_comissao = total_venda * (comissao_percentual / 100.0)
        col6, col7 = st.columns(2)
        col6.metric('Total da Venda', f'R$ {total_venda:.2f}')
        col7.metric('Valor da Comissão', f'R$ {valor_comissao:.2f}')
        status = st.selectbox('Status', ['ativo', 'cancelado'])
        submitted = st.form_submit_button('Cadastrar Venda')
        if submitted:
            if all([estabelecimento, bairro, produto]):
                data = {
                    'estabelecimento': estabelecimento,
                    'data_venda': data_venda.strftime('%Y-%m-%d'),
                    'bairro': bairro,
                    'forma_pagamento': forma_pagamento,
                    'produto': produto,
                    'quantidade': float(quantidade),
                    'valor_produto': float(valor_produto),
                    'total_venda': float(total_venda),
                    'comissao_percentual': float(comissao_percentual),
                    'valor_comissao': float(valor_comissao),
                    'status': status
                }
                supabase.table('vendas').insert(data).execute()
                st.session_state.cache_buster += 1
                st.success('Venda cadastrada com sucesso!')
                st.rerun()
            else:
                st.error('Preencha todos os campos obrigatórios.')

with tab2:
    st.header('Edição em Massa')
    if df.empty:
        st.info('Nenhum dado encontrado. Cadastre vendas primeiro.')
    else:
        column_config = {
            'id': st.column_config.NumberColumn('ID', disabled=True, format='%.0f'),
            'data_venda': st.column_config.DateColumn('Data Venda'),
            'quantidade': st.column_config.NumberColumn('Quantidade', format='%.2f'),
            'valor_produto': st.column_config.NumberColumn('Valor Produto', format='%.2f'),
            'total_venda': st.column_config.NumberColumn('Total Venda', format='%.2f'),
            'comissao_percentual': st.column_config.NumberColumn('Comissão %', format='%.2f'),
            'valor_comissao': st.column_config.NumberColumn('Valor Comissão', format='%.2f'),
            'status': st.column_config.SelectboxColumn('Status', options=['ativo', 'cancelado'])
        }
        edited_df = st.data_editor(
            df,
            num_rows='dynamic',
            column_config=column_config,
            use_container_width=True,
            hide_index=False
        )
        if st.button('🔄 Sincronizar Alterações', type='primary'):
            edited_df['id'] = pd.to_numeric(edited_df['id'], errors='coerce').astype('Int64')
            original_ids = set(df['id'].dropna().unique())
            edited_ids = set(edited_df.dropna(subset=['id'])['id'].dropna().unique())
            # Deletar IDs que sumiram
            to_delete = original_ids - edited_ids
            for vid in to_delete:
                supabase.table('vendas').delete().eq('id', int(vid)).execute()
            # Atualizar existentes
            for _, row in edited_df.dropna(subset=['id']).iterrows():
                payload = row.drop('id').to_dict()
                float_cols = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
                for fcol in float_cols:
                    if fcol in payload:
                        payload[fcol] = float(payload[fcol])
                if 'data_venda' in payload and pd.notna(payload['data_venda']):
                    payload['data_venda'] = payload['data_venda'].strftime('%Y-%m-%d')
                supabase.table('vendas').update(payload).eq('id', int(row['id'])).execute()
            # Inserir novos
            new_rows = edited_df[edited_df['id'].isna()]
            for _, row in new_rows.iterrows():
                payload = row.drop('id').to_dict()
                float_cols = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
                for fcol in float_cols:
                    if fcol in payload:
                        payload[fcol] = float(payload[fcol])
                if 'data_venda' in payload and pd.notna(payload['data_venda']):
                    payload['data_venda'] = payload['data_venda'].strftime('%Y-%m-%d')
                supabase.table('vendas').insert(payload).execute()
            st.session_state.cache_buster += 1
            st.success('Dados sincronizados com sucesso!')
            st.rerun()

with tab3:
    st.header('Relatórios')
    if df.empty:
        st.info('Nenhum dado para relatórios.')
    else:
        col1, col2, col3, col4, col5 = st.columns(5)
        data_ini = col1.date_input('Data Início', value=(pd.Timestamp.now() - pd.Timedelta(days=30)).date())
        data_fim = col2.date_input('Data Fim', value=pd.Timestamp.now().date())
        bairros = ['Todos'] + sorted(df['bairro'].dropna().unique())
        bairro_f = col3.selectbox('Bairro', bairros)
        formas = ['Todos'] + sorted(df['forma_pagamento'].dropna().unique())
        forma_f = col4.selectbox('Forma de Pagamento', formas)
        produtos = ['Todos'] + sorted(df['produto'].dropna().unique())
        produto_f = col5.selectbox('Produto', produtos)
        ests = ['Todos'] + sorted(df['estabelecimento'].dropna().unique())
        estab_f = st.selectbox('Estabelecimento', ests)
        df_filtered = df[(
            (df['data_venda'] >= pd.Timestamp(data_ini)) &
            (df['data_venda'] <= pd.Timestamp(data_fim) + pd.Timedelta(days=1))
        )].copy()
        if bairro_f != 'Todos':
            df_filtered = df_filtered[df_filtered['bairro'] == bairro_f]
        if forma_f != 'Todos':
            df_filtered = df_filtered[df_filtered['forma_pagamento'] == forma_f]
        if produto_f != 'Todos':
            df_filtered = df_filtered[df_filtered['produto'] == produto_f]
        if estab_f != 'Todos':
            df_filtered = df_filtered[df_filtered['estabelecimento'] == estab_f]
        col_m1, col_m2, col_m3 = st.columns(3)
        total_fat = df_filtered['total_venda'].sum()
        total_com = df_filtered['valor_comissao'].sum()
        qtd_vendas = len(df_filtered)
        col_m1.metric('Faturamento Total', f'R$ {total_fat:.2f}')
        col_m2.metric('Total de Comissões', f'R$ {total_com:.2f}')
        col_m3.metric('Quantidade de Vendas', qtd_vendas)
        if not df_filtered.empty:
            daily_sales = df_filtered.groupby('data_venda')['total_venda'].sum().reset_index()
            fig_evol = px.line(daily_sales, x='data_venda', y='total_venda', title='Evolução de Vendas')
            st.plotly_chart(fig_evol, use_container_width=True)
            prod_sales = df_filtered.groupby('produto')['total_venda'].sum().reset_index().sort_values('total_venda', ascending=False)
            fig_dist = px.bar(prod_sales, x='produto', y='total_venda', title='Distribuição por Produto')
            st.plotly_chart(fig_dist, use_container_width=True)
