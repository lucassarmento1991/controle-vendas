import streamlit as st
import pandas as pd
import plotly.express as px
import supabase
from supabase import create_client, Client
import hashlib
import traceback
from datetime import datetime, date

@st.cache_resource
def init_supabase():
    try:
        # Try root level secrets
        url = st.secrets["SUPABASE_URL"].strip()
        key = st.secrets["SUPABASE_KEY"].strip()
    except KeyError:
        try:
            # Try [supabase] section
            url = st.secrets.supabase.url.strip()
            key = st.secrets.supabase.key.strip()
        except (KeyError, AttributeError):
            st.error("Configurações do Supabase não encontradas em secrets.toml (raiz ou [supabase]).")
            st.stop()
    return create_client(url, key)

def login_user(client: Client, username: str, password: str):
    try:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        response = client.table('usuarios').select('*').eq('username', username).eq('password_hash', hashed_pw).execute()
        data = response.data
        if data:
            return data[0]
        return None
    except Exception as e:
        st.error(f"Erro no login: {str(e)}")
        st.error(traceback.format_exc())
        return None

st.set_page_config(page_title="Gerenciador de Vendas - Lucas", layout="wide")

if 'user' not in st.session_state:
    st.session_state.user = None
    st.session_state.client = None

st.session_state.client = init_supabase()

if st.session_state.user is None:
    st.title("🔐 Faça Login")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://via.placeholder.com/150x150?text=Logo", use_column_width=True)
    with col2:
        username = st.text_input("username", placeholder="seu@email.com")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary"):
            if username and password:
                user = login_user(st.session_state.client, username, password)
                if user:
                    st.session_state.user = user
                    st.success(f"Bem-vindo, {user.get('nome', user.get('username', 'Usuário'))}!")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
            else:
                st.warning("Preencha username e senha.")
else:
    # Sidebar
    st.sidebar.title("Perfil")
    st.sidebar.write(f"👤 {st.session_state.user.get('nome', st.session_state.user.get('username', 'Usuário'))}")
    if st.sidebar.button("Sair"):
        st.session_state.user = None
        st.rerun()

    tab1, tab2 = st.tabs(["📊 Gerenciar Vendas", "📈 Relatórios"])

    with tab1:
        st.subheader("Gerenciar Vendas")
        if 'vendas_df' not in st.session_state:
            response = st.session_state.client.table('vendas').select('*').order('data_venda').execute()
            st.session_state.vendas_df = pd.DataFrame(response.data)

        edited_df = st.data_editor(
            st.session_state.vendas_df,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "estabelecimento": st.column_config.TextColumn("Estabelecimento"),
                "data_venda": st.column_config.DateColumn("Data Venda"),
                "bairro": st.column_config.TextColumn("Bairro"),
                "forma_pagamento": st.column_config.SelectboxColumn("Forma Pagamento", options=["Dinheiro", "Pix", "Cartão", "Boleto"]),
                "produto": st.column_config.TextColumn("Produto"),
                "quantidade": st.column_config.NumberColumn("Quantidade", min_value=0, step=1),
                "valor_produto": st.column_config.NumberColumn("Valor Produto", min_value=0.0, step=0.01, format="%.2f"),
                "total_venda": st.column_config.NumberColumn("Total Venda", min_value=0.0, step=0.01, format="%.2f"),
                "comissao_percentual": st.column_config.NumberColumn("Comissão %", min_value=0.0, max_value=100.0, step=0.1, format="%.2f%%"),
                "valor_comissao": st.column_config.NumberColumn("Valor Comissão", min_value=0.0, step=0.01, format="%.2f"),
                "status": st.column_config.SelectboxColumn("Status", options=["Pendente", "Pago", "Cancelado"]),
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
        )

        if st.button("💾 Aplicar Mudanças", type="primary"):
            try:
                original_ids = set(st.session_state.vendas_df['id'].dropna().astype(int))
                edited_ids = set(edited_df['id'].dropna().astype(int))

                # Deletes
                deleted_ids = original_ids - edited_ids
                for id_val in deleted_ids:
                    st.session_state.client.table('vendas').delete().eq('id', id_val).execute()

                # Inserts/Updates
                for _, row in edited_df.iterrows():
                    row_dict = row.to_dict()
                    id_val = row_dict.pop('id', None)
                    if pd.isna(id_val) or id_val is None:
                        # Insert
                        st.session_state.client.table('vendas').insert(row_dict).execute()
                    else:
                        # Update
                        st.session_state.client.table('vendas').update(row_dict).eq('id', id_val).execute()

                st.success("✅ Alterações salvas com sucesso!")
                # Reload data
                response = st.session_state.client.table('vendas').select('*').order('data_venda').execute()
                st.session_state.vendas_df = pd.DataFrame(response.data)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {str(e)}")
                st.error(traceback.format_exc())

    with tab2:
        st.subheader("Relatórios Avançados")
        # Load all data
        response = st.session_state.client.table('vendas').select('*').order('data_venda').execute()
        all_vendas = pd.DataFrame(response.data)
        if all_vendas.empty:
            st.info("Nenhuma venda encontrada.")
            st.stop()

        # Filters
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            data_inicio = st.date_input("Data Início", value=date.today())
        with col2:
            data_fim = st.date_input("Data Fim", value=date.today())
        with col3:
            unique_bairros = sorted(all_vendas['bairro'].dropna().unique())
            selected_bairros = st.multiselect("Bairros", options=unique_bairros)
        with col4:
            unique_produtos = sorted(all_vendas['produto'].dropna().unique())
            selected_produtos = st.multiselect("Produtos", options=unique_produtos)

        col5, col6, col7 = st.columns(3)
        with col5:
            unique_formas = sorted(all_vendas['forma_pagamento'].dropna().unique())
            selected_formas = st.multiselect("Forma Pagamento", options=unique_formas)
        with col6:
            unique_status = sorted(all_vendas['status'].dropna().unique())
            selected_status = st.multiselect("Status", options=unique_status)
        with col7:
            min_comissao = st.slider("Comissão Mínima (%)", 0.0, 100.0, 0.0)

        # Apply filters
        filtered_df = all_vendas.copy()
        if data_inicio:
            filtered_df = filtered_df[pd.to_datetime(filtered_df['data_venda']) >= pd.to_datetime(data_inicio)]
        if data_fim:
            filtered_df = filtered_df[pd.to_datetime(filtered_df['data_venda']) <= pd.to_datetime(data_fim)]
        if selected_bairros:
            filtered_df = filtered_df[filtered_df['bairro'].isin(selected_bairros)]
        if selected_produtos:
            filtered_df = filtered_df[filtered_df['produto'].isin(selected_produtos)]
        if selected_formas:
            filtered_df = filtered_df[filtered_df['forma_pagamento'].isin(selected_formas)]
        if selected_status:
            filtered_df = filtered_df[filtered_df['status'].isin(selected_status)]
        filtered_df = filtered_df[filtered_df['comissao_percentual'] >= min_comissao]

        if filtered_df.empty:
            st.warning("Nenhum dado com os filtros aplicados.")
        else:
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            total_vendas = filtered_df['total_venda'].sum()
            total_comissao = filtered_df['valor_comissao'].sum()
            qtd_vendas = len(filtered_df)
            avg_ticket = total_vendas / qtd_vendas if qtd_vendas > 0 else 0

            col1.metric("Total Vendas", f"R$ {total_vendas:,.2f}")
            col2.metric("Total Comissão", f"R$ {total_comissao:,.2f}")
            col3.metric("Qtd. Vendas", qtd_vendas)
            col4.metric("Ticket Médio", f"R$ {avg_ticket:,.2f}")

            # Charts
            col_left, col_right = st.columns(2)
            with col_left:
                vendas_por_produto = filtered_df.groupby('produto')['total_venda'].sum().reset_index()
                fig1 = px.bar(vendas_por_produto, x='produto', y='total_venda', title="Vendas por Produto")
                st.plotly_chart(fig1, use_container_width=True)

                vendas_por_bairro = filtered_df.groupby('bairro')['total_venda'].sum().reset_index()
                fig2 = px.pie(vendas_por_bairro, names='bairro', values='total_venda', title="Vendas por Bairro")
                st.plotly_chart(fig2, use_container_width=True)

            with col_right:
                vendas_por_data = filtered_df.groupby('data_venda')['total_venda'].sum().reset_index()
                fig3 = px.line(vendas_por_data, x='data_venda', y='total_venda', title="Vendas por Data")
                st.plotly_chart(fig3, use_container_width=True)

                comissao_por_status = filtered_df.groupby('status')['valor_comissao'].sum().reset_index()
                fig4 = px.bar(comissao_por_status, x='status', y='valor_comissao', title="Comissão por Status")
                st.plotly_chart(fig4, use_container_width=True)

            st.subheader("Tabela Filtrada")
            st.dataframe(filtered_df, use_container_width=True)
