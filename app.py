import streamlit as st
import pandas as pd
from supabase import create_client, Client
import hashlib
import plotly.express as px
from datetime import date

# Supabase configuration
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Login page
if not st.session_state.logged_in:
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Entrar"):
        # Hardcoded for Lucas: username='lucas', password='123456' (SHA-256: 8d969eef6ecad3c29a3a629269e907e57dc0036a3d966d3b71233de39b56269a)
        expected_hash = "8d969eef6ecad3c29a3a629269e907e57dc0036a3d966d3b71233de39b56269a"
        if username == "lucas" and hash_password(password) == expected_hash:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Credenciais inválidas")
else:
    # Sidebar for user info and logout
    with st.sidebar:
        st.write(f"Usuário: {st.session_state.username}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()

    st.title("Gestão de Vendas")

    tab1, tab2 = st.tabs(["Vendas", "Relatórios"])

    with tab1:
        @st.cache_data
        def load_vendas():
            response = supabase.table("vendas").select("*").execute()
            return response.data

        vendas_data = load_vendas()
        if vendas_data:
            df = pd.DataFrame(vendas_data)
            if 'id' in df.columns:
                ids_para_deletar = st.multiselect("Selecione IDs para excluir", df['id'].tolist())
                
                if st.button('Confirmar Exclusões') and ids_para_deletar:
                    for rid in ids_para_deletar:
                        supabase.table("vendas").delete().eq("id", rid).execute()
                    st.cache_data.clear()
                    st.success(f"{len(ids_para_deletar)} vendas excluídas com sucesso!")
                    st.rerun()
                
                st.dataframe(df)
            else:
                st.warning("Coluna 'id' não encontrada na tabela.")
                st.dataframe(df)
        else:
            st.info("Nenhuma venda encontrada.")

    with tab2:
        @st.cache_data
        def load_vendas_reports():
            response = supabase.table("vendas").select("*").execute()
            return response.data

        vendas_data = load_vendas_reports()
        if vendas_data:
            df = pd.DataFrame(vendas_data)
            df['data_venda'] = pd.to_datetime(df['data_venda'])

            # Filters
            col1, col2 = st.columns(2)
            with col1:
                min_date = df['data_venda'].min().date()
                max_date = df['data_venda'].max().date()
                data_inicio = st.date_input("Data Início", value=min_date, min_value=min_date, max_value=max_date)
            with col2:
                data_fim = st.date_input("Data Fim", value=max_date, min_value=min_date, max_value=max_date)

            col1, col2, col3 = st.columns(3)
            with col1:
                estabelecimentos = st.multiselect("Estabelecimento", options=sorted(df['estabelecimento'].unique()))
            with col2:
                forma_pagamentos = st.multiselect("Forma Pagamento", options=sorted(df['forma_pagamento'].unique()))
            with col3:
                bairros = st.multiselect("Bairro", options=sorted(df['bairro'].unique()))

            # Apply filters
            mask = (
                (df['data_venda'].dt.date >= data_inicio) & 
                (df['data_venda'].dt.date <= data_fim)
            )
            if len(estabelecimentos) > 0:
                mask &= df['estabelecimento'].isin(estabelecimentos)
            if len(forma_pagamentos) > 0:
                mask &= df['forma_pagamento'].isin(forma_pagamentos)
            if len(bairros) > 0:
                mask &= df['bairro'].isin(bairros)

            filtered_df = df[mask].copy()

            if not filtered_df.empty:
                # Metrics
                col1, col2, col3, col4 = st.columns(4)
                total_vendas = filtered_df['total_venda'].sum()
                total_comissao = filtered_df['valor_comissao'].sum()
                qtd_vendas = len(filtered_df)
                avg_venda = filtered_df['total_venda'].mean()

                col1.metric("Total Vendas", f"R$ {total_vendas:,.2f}")
                col2.metric("Total Comissão", f"R$ {total_comissao:,.2f}")
                col3.metric("Qtd. Vendas", qtd_vendas)
                col4.metric("Média Venda", f"R$ {avg_venda:,.2f}")

                # Charts
                vendas_por_est = filtered_df.groupby('estabelecimento')['total_venda'].sum().reset_index()
                fig1 = px.bar(vendas_por_est, x='estabelecimento', y='total_venda', title="Vendas por Estabelecimento")
                st.plotly_chart(fig1, use_container_width=True)

                pagto_dist = filtered_df['forma_pagamento'].value_counts().reset_index()
                pagto_dist.columns = ['forma_pagamento', 'count']
                fig2 = px.pie(pagto_dist, names='forma_pagamento', values='count', title="Distribuição por Forma de Pagamento")
                st.plotly_chart(fig2, use_container_width=True)

                # Additional chart: Vendas por Bairro
                vendas_por_bairro = filtered_df.groupby('bairro')['total_venda'].sum().reset_index()
                fig3 = px.bar(vendas_por_bairro, x='bairro', y='total_venda', title="Vendas por Bairro")
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("Nenhum dado encontrado com os filtros aplicados.")
        else:
            st.info("Nenhuma venda encontrada.")