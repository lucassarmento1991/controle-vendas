import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib
from datetime import datetime

st.set_page_config(page_title="Sistema de Controle de Vendas", layout="wide")

@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"].strip()
        key = st.secrets["SUPABASE_KEY"].strip()
        if not url or not key:
            st.error("Configura\u00e7\u00e3o do Supabase ausente.")
            st.stop()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao inicializar Supabase: {str(e)}")
        st.stop()

supabase: Client = init_supabase()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("Login")
    username = st.text_input("Usu\u00e1rio")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if username and password:
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            response = (supabase
                        .table('usuarios')
                        .select('id')
                        .eq('username', username)
                        .eq('password_hash', hashed_pw)
                        .single()
                        .execute())
            if response.data:
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("Credenciais inv\u00e1lidas!")
        else:
            st.warning("Preencha usu\u00e1rio e senha.")
else:
    st.sidebar.title("Menu")
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.title("Sistema Completo de Controle de Vendas com Supabase")

    tab1, tab2 = st.tabs(["Edi\u00e7\u00e3o", "Relat\u00f3rios"])

    with tab1:
        st.header("Gerenciar Vendas")

        @st.cache_data(ttl=300)
        def load_vendas():
            response = supabase.table('vendas').select('*').execute()
            if response.data:
                df = pd.DataFrame(response.data)
                if 'data_venda' in df.columns:
                    df['data_venda'] = pd.to_datetime(df['data_venda'])
                return df
            return pd.DataFrame()

        df = load_vendas()

        if df.empty:
            st.warning("Nenhuma venda encontrada.")
        else:
            col_config = {
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "data_venda": st.column_config.DateColumn("Data da Venda"),
                "estabelecimento": st.column_config.TextColumn("Estabelecimento"),
                "bairro": st.column_config.TextColumn("Bairro"),
                "forma_pagamento": st.column_config.TextColumn("Forma de Pagamento"),
                "produto": st.column_config.TextColumn("Produto"),
                "quantidade": st.column_config.NumberColumn("Quantidade"),
                "valor_produto": st.column_config.NumberColumn("Valor Produto"),
                "total_venda": st.column_config.NumberColumn("Total Venda"),
                "comissao_percentual": st.column_config.NumberColumn("Comiss\u00e3o %"),
                "valor_comissao": st.column_config.NumberColumn("Valor Comiss\u00e3o"),
                "status": st.column_config.SelectboxColumn("Status", options=["Pendente", "Pago", "Cancelado"]),
            }

            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config=col_config,
                use_container_width=True,
                hide_index=True,
            )

            if st.button("Salvar Altera\u00e7\u00f5es", type="primary"):
                success_count = 0
                # Added rows
                added_mask = edited_df['id'].isna()
                added_rows = edited_df[added_mask].drop(columns=['id']).to_dict('records')
                for row in added_rows:
                    if 'data_venda' in row and pd.notna(row['data_venda']):
                        row['data_venda'] = row['data_venda'].isoformat()
                    res = supabase.table('vendas').insert(row).execute()
                    if res.data:
                        success_count += 1
                # Deleted
                original_ids = set(df['id'].dropna().unique())
                current_ids = set(edited_df[~added_mask]['id'].dropna().unique())
                deleted_ids = original_ids - current_ids
                for del_id in deleted_ids:
                    res = supabase.table('vendas').delete().eq('id', del_id).execute()
                    if res.count > 0:
                        success_count += 1
                # Updates
                modified_df = edited_df[~added_mask]
                for _, row in modified_df.iterrows():
                    if pd.isna(row['id']):
                        continue
                    row_dict = row.to_dict()
                    if 'data_venda' in row_dict and pd.notna(row_dict['data_venda']):
                        row_dict['data_venda'] = row_dict['data_venda'].isoformat()
                    res = supabase.table('vendas').update(row_dict).eq('id', row['id']).execute()
                    if res.count > 0:
                        success_count += 1
                st.success(f"{success_count} altera\u00e7\u00f5es salvas com sucesso!")
                st.cache_data.clear()
                st.rerun()

    with tab2:
        st.header("Relat\u00f3rios Filtrados")

        @st.cache_data(ttl=300)
        def load_vendas_reports():
            response = supabase.table('vendas').select('*').execute()
            if response.data:
                df = pd.DataFrame(response.data)
                if 'data_venda' in df.columns:
                    df['data_venda'] = pd.to_datetime(df['data_venda'])
                return df
            return pd.DataFrame()

        df_reports = load_vendas_reports()

        if df_reports.empty:
            st.info("Nenhum dado para relat\u00f3rios.")
        else:
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                min_date = df_reports['data_venda'].min().date() if 'data_venda' in df_reports and not df_reports['data_venda'].isna().all() else datetime.now().date()
                data_inicio = st.date_input("Data In\u00edcio", value=min_date)
            with col2:
                max_date = df_reports['data_venda'].max().date() if 'data_venda' in df_reports and not df_reports['data_venda'].isna().all() else datetime.now().date()
                data_fim = st.date_input("Data Fim", value=max_date)
            with col3:
                est_options = ['Todos'] + sorted(df_reports['estabelecimento'].dropna().unique())
                estabelecimento = st.selectbox("Estabelecimento", est_options)
            with col4:
                bairro_options = ['Todos'] + sorted(df_reports['bairro'].dropna().unique())
                bairro = st.selectbox("Bairro", bairro_options)
            with col5:
                pag_options = ['Todos'] + sorted(df_reports['forma_pagamento'].dropna().unique())
                forma_pagamento = st.selectbox("Forma Pagamento", pag_options)

            prod_options = ['Todos'] + sorted(df_reports['produto'].dropna().unique())
            produto = st.selectbox("Produto", prod_options)

            filtered_df = df_reports[(df_reports['data_venda'].dt.date >= data_inicio) &
                                     (df_reports['data_venda'].dt.date <= data_fim)].copy()

            if estabelecimento != 'Todos':
                filtered_df = filtered_df[filtered_df['estabelecimento'] == estabelecimento]
            if bairro != 'Todos':
                filtered_df = filtered_df[filtered_df['bairro'] == bairro]
            if forma_pagamento != 'Todos':
                filtered_df = filtered_df[filtered_df['forma_pagamento'] == forma_pagamento]
            if produto != 'Todos':
                filtered_df = filtered_df[filtered_df['produto'] == produto]

            col_a, col_b, col_c = st.columns(3)
            total_vendas = filtered_df['total_venda'].sum()
            total_comissao = filtered_df['valor_comissao'].sum()
            qtd_vendas = len(filtered_df)

            with col_a:
                st.metric("Total Vendas", f"R$ {total_vendas:,.2f}")
            with col_b:
                st.metric("Total Comiss\u00e3o", f"R$ {total_comissao:,.2f}")
            with col_c:
                st.metric("Qtd. Vendas", qtd_vendas)

            st.subheader("Dados Filtrados")
            st.dataframe(filtered_df[['data_venda', 'estabelecimento', 'bairro', 'forma_pagamento', 'produto', 'total_venda', 'status']], use_container_width=True)

            st.subheader("Gr\u00e1ficos Din\u00e2micos")
            if not filtered_df.empty:
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    fig_pie = px.pie(filtered_df, names='produto', values='total_venda', title='Distribui\u00e7\u00e3o por Produto')
                    st.plotly_chart(fig_pie, use_container_width=True)
                with col_g2:
                    fig_bar = px.bar(filtered_df, x='estabelecimento', y='total_venda', title='Vendas por Estabelecimento')
                    st.plotly_chart(fig_bar, use_container_width=True)

                col_g3, col_g4 = st.columns(2)
                with col_g3:
                    daily_sales = filtered_df.groupby(filtered_df['data_venda'].dt.date)['total_venda'].sum().reset_index()
                    fig_line = px.line(daily_sales, x='data_venda', y='total_venda', title='Vendas por Data')
                    st.plotly_chart(fig_line, use_container_width=True)
                with col_g4:
                    fig_scatter = px.scatter(filtered_df, x='quantidade', y='total_venda', color='produto', title='Quantidade vs Total Venda')
                    st.plotly_chart(fig_scatter, use_container_width=True)