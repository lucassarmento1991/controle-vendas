import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from datetime import date
from supabase import create_client, Client

st.set_page_config(page_title='Gerenciador de Vendas', layout='wide')

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

expected_columns = ['id', 'estabelecimento', 'data_venda', 'bairro', 'forma_pagamento', 'produto', 'quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao', 'status']

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title('Login')
    with st.form('login_form'):
        username = st.text_input('Usuário').strip()
        password = st.text_input('Senha', type='password')
        submit = st.form_submit_button('Entrar')
        if submit:
            hashed_pw = hash_password(password)
            response = supabase.table('users').select('*').eq('username', username).eq('password_hash', hashed_pw).execute()
            if response.data:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success('Login realizado com sucesso!')
                st.rerun()
            else:
                st.error('Credenciais inválidas.')
    st.stop()

st.title('Gerenciador de Vendas')

if st.sidebar.button('Logout'):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.success(f'Logado como: {st.session_state.username}')

tab1, tab2, tab3 = st.tabs(['Cadastro', 'Gerenciar Registros', 'Relatórios'])

@st.cache_data(ttl=300)
def load_data():
    try:
        response = supabase.table('vendas').select(','.join(expected_columns)).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['data_venda'] = pd.to_datetime(df['data_venda'])
            df['id'] = df['id'].astype(int)
            df['quantidade'] = pd.to_numeric(df['quantidade'])
            df['valor_produto'] = pd.to_numeric(df['valor_produto'])
            df['total_venda'] = pd.to_numeric(df['total_venda'])
            df['comissao_percentual'] = pd.to_numeric(df['comissao_percentual'])
            df['valor_comissao'] = pd.to_numeric(df['valor_comissao'])
            df = df.sort_values('data_venda', ascending=False).reset_index(drop=True)
        if set(df.columns.tolist()) != set(expected_columns):
            st.error('Schema das colunas não está sincronizado! Verifique a tabela "vendas" no Supabase.')
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f'Erro ao carregar dados: {str(e)}')
        return pd.DataFrame()

with tab1:
    st.header('Novo Registro')
    with st.form('cadastro_form'):
        col1, col2 = st.columns(2)
        with col1:
            estabelecimento = st.text_input('Estabelecimento', key='estab_cad')
            data_venda = st.date_input('Data da Venda', value=date.today(), key='data_cad')
            bairro = st.text_input('Bairro', key='bairro_cad')
            forma_pagamento = st.selectbox('Forma de Pagamento', ['Dinheiro', 'Pix', 'Cartão', 'Boleto'], key='forma_cad')
        with col2:
            produto = st.text_input('Produto', key='prod_cad')
            quantidade = st.number_input('Quantidade', min_value=1, step=1, key='qtd_cad')
            valor_produto = st.number_input('Valor Unitário (R$)', min_value=0.01, format='%.2f', key='val_prod_cad')
            comissao_percentual = st.number_input('Comissão %', min_value=0.0, max_value=100.0, value=10.0, key='comiss_cad') / 100
        total_venda = quantidade * valor_produto
        valor_comissao = total_venda * comissao_percentual
        col_t1, col_t2 = st.columns(2)
        col_t1.info(f'**Total Venda: R$ {total_venda:.2f}**')
        col_t2.info(f'**Valor Comissão: R$ {valor_comissao:.2f}**')
        status = st.selectbox('Status', ['ativo', 'cancelado'], key='status_cad')
        submit = st.form_submit_button('Salvar Registro')
        if submit:
            data = {
                'estabelecimento': estabelecimento,
                'data_venda': data_venda.strftime('%Y-%m-%d'),
                'bairro': bairro,
                'forma_pagamento': forma_pagamento,
                'produto': produto,
                'quantidade': int(quantidade),
                'valor_produto': float(valor_produto),
                'total_venda': float(total_venda),
                'comissao_percentual': float(comissao_percentual),
                'valor_comissao': float(valor_comissao),
                'status': status
            }
            try:
                resp = supabase.table('vendas').insert(data).execute()
                if resp.data:
                    st.success('Registro salvo com sucesso!')
                    st.rerun()
                else:
                    st.error('Erro ao salvar. Verifique os dados.')
            except Exception as e:
                st.error(f'Erro no Supabase: {str(e)}')

with tab2:
    st.header('Gerenciar Registros')
    st.info('📝 Use os ícones de lixeira (🗑️) ao lado de cada linha para excluir registros. Não é possível editar ou adicionar aqui.')
    df = load_data()
    if df.empty:
        st.warning('Nenhum registro encontrado.')
    else:
        column_config = {col: st.column_config.Column(disabled=True, width='medium') for col in df.columns}
        edited_df = st.data_editor(
            df,
            column_config=column_config,
            num_rows='dynamic',
            use_container_width=True,
            hide_index=True,
            key='data_editor'
        )
        if st.button('Aplicar Exclusões', type='primary'):
            original_ids = set(df['id'])
            new_ids = set(edited_df['id'].dropna().astype(int))
            deleted_ids = original_ids - new_ids
            if deleted_ids:
                success_count = 0
                for record_id in deleted_ids:
                    try:
                        supabase.table('vendas').delete().eq('id', record_id).execute()
                        success_count += 1
                    except:
                        pass
                st.success(f'{success_count} registro(s) excluído(s) com sucesso!')
                st.rerun()
            else:
                st.info('Nenhuma exclusão foi detectada.')

with tab3:
    st.header('Relatórios e Métricas')
    df = load_data()
    if df.empty:
        st.warning('Nenhum dado disponível para relatórios.')
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            start_date = st.date_input('Data Início', value=df['data_venda'].min().date(), key='start_rep')
            end_date = st.date_input('Data Fim', value=df['data_venda'].max().date(), key='end_rep')
        with col_f2:
            pass  # Filters below
        col_f3, col_f4, col_f5 = st.columns(3)
        with col_f3:
            estabelecimentos = sorted(df['estabelecimento'].dropna().unique().tolist())
            sel_est = st.multiselect('Estabelecimento', estabelecimentos, default=estabelecimentos, key='est_rep')
        with col_f4:
            formas = sorted(df['forma_pagamento'].dropna().unique().tolist())
            sel_forma = st.multiselect('Forma Pagamento', formas, default=formas, key='forma_rep')
        with col_f5:
            bairros = sorted(df['bairro'].dropna().unique().tolist())
            sel_bairro = st.multiselect('Bairro', bairros, default=bairros, key='bairro_rep')

        filtered_df = df[
            (df['data_venda'].dt.date >= start_date) &
            (df['data_venda'].dt.date <= end_date)
        ].copy()

        if sel_est:
            filtered_df = filtered_df[filtered_df['estabelecimento'].isin(sel_est)]
        if sel_forma:
            filtered_df = filtered_df[filtered_df['forma_pagamento'].isin(sel_forma)]
        if sel_bairro:
            filtered_df = filtered_df[filtered_df['bairro'].isin(sel_bairro)]

        if filtered_df.empty:
            st.warning('Nenhum registro encontrado com os filtros aplicados.')
        else:
            total_vendas = filtered_df['total_venda'].sum()
            total_comissao = filtered_df['valor_comissao'].sum()
            qtd_registros = len(filtered_df)
            avg_comissao = total_comissao / qtd_registros if qtd_registros > 0 else 0

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric('Total Vendas', f'R$ {total_vendas:,.2f}')
            with col_m2:
                st.metric('Total Comissão', f'R$ {total_comissao:,.2f}')
            with col_m3:
                st.metric('Qtd. Registros', qtd_registros)
            with col_m4:
                st.metric('Avg. Comissão/Reg.', f'R$ {avg_comissao:,.2f}')

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                vendas_est = filtered_df.groupby('estabelecimento')['total_venda'].sum().reset_index()
                fig1 = px.bar(vendas_est, x='estabelecimento', y='total_venda',
                              title='Vendas por Estabelecimento',
                              color='total_venda')
                st.plotly_chart(fig1, use_container_width=True)
            with col_g2:
                fig2 = px.pie(filtered_df, names='forma_pagamento', values='total_venda',
                              title='Distribuição por Forma de Pagamento')
                st.plotly_chart(fig2, use_container_width=True)

            col_g3, col_g4 = st.columns(2)
            with col_g3:
                vendas_dia = filtered_df.groupby(filtered_df['data_venda'].dt.date)['total_venda'].sum().reset_index()
                vendas_dia.columns = ['data', 'total']
                fig3 = px.line(vendas_dia, x='data', y='total', title='Vendas por Dia')
                st.plotly_chart(fig3, use_container_width=True)
            with col_g4:
                vendas_bairro = filtered_df.groupby('bairro')['total_venda'].sum().reset_index()
                fig4 = px.bar(vendas_bairro, x='bairro', y='total_venda',
                              title='Vendas por Bairro',
                              color='total_venda')
                st.plotly_chart(fig4, use_container_width=True)