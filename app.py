import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from datetime import date
from supabase import create_client

st.set_page_config(page_title="Dashboard de Vendas", layout="wide")

# Configuração de login SHA-256
ADMIN_USERNAME = "lucas"
ADMIN_PASSWORD_HASH = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"  # sha256('admin')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Estado da sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'df' not in st.session_state:
    st.session_state.df = None

# Tela de login
if not st.session_state.logged_in:
    st.title("🔐 Login")
    username = st.text_input("Usuário", placeholder="lucas")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if username == ADMIN_USERNAME and hash_password(password) == ADMIN_PASSWORD_HASH:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Credenciais inválidas!")
    st.stop()

st.title("💸 Dashboard de Vendas")
st.sidebar.title("Navegação")

# Cliente Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"].strip()
    key = st.secrets["supabase"]["key"].strip()
    return create_client(url, key)

supabase = init_supabase()

# Carregar dados
@st.cache_data(ttl=300)
def load_vendas():
    response = supabase.table('vendas').select('*').execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['data_venda'] = pd.to_datetime(df['data_venda'], errors='coerce').dt.date
        numeric_cols = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

# Abas
tab1, tab2 = st.tabs(["Listagem", "Relatórios"])

with tab1:
    st.header("Edição de Vendas")
    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn1:
        st.info(f"\u{len(st.session_state.df or load_vendas())} vendas carregadas.")
    with col_btn2:
        if st.button("Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

    df = load_vendas()
    st.session_state.df = df

    if df.empty:
        st.warning("Nenhuma venda encontrada no banco.")
    else:
        column_config = {
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "data_venda": st.column_config.DateColumn("Data da Venda", format="DD/MM/YYYY"),
            "estabelecimento": st.column_config.TextColumn("Estabelecimento"),
            "bairro": st.column_config.TextColumn("Bairro"),
            "forma_pagamento": st.column_config.TextColumn("Forma de Pagamento"),
            "produto": st.column_config.TextColumn("Produto"),
            "quantidade": st.column_config.NumberColumn("Quantidade", min_value=0, step=1),
            "valor_produto": st.column_config.NumberColumn("Valor Unit.", format="R$ %.2f"),
            "total_venda": st.column_config.NumberColumn("Total Venda", format="R$ %.2f"),
            "comissao_percentual": st.column_config.NumberColumn("Comissão %", format="%.1f", min_value=0, max_value=100),
            "valor_comissao": st.column_config.NumberColumn("Valor Comissão", format="R$ %.2f"),
            "status": st.column_config.SelectboxColumn("Status", options=["Pendente", "Pago", "Cancelado", "Faturado"]),
        }

        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            column_config=column_config,
            use_container_width=True,
            hide_index=False,
        )

        if st.button("💾 Salvar Alterações", type="primary"):
            success_count = 0
            error_count = 0
            for _, row in edited_df.iterrows():
                row_dict = row.to_dict()
                # Converter data_venda para string
                if 'data_venda' in row_dict and pd.notna(row_dict['data_venda']):
                    row_dict['data_venda'] = row_dict['data_venda'].strftime('%Y-%m-%d')
                id_val = row_dict.get('id')
                try:
                    if pd.isna(id_val):
                        # Nova venda
                        row_dict.pop('id', None)
                        supabase.table('vendas').insert(row_dict).execute()
                    else:
                        # Atualizar
                        supabase.table('vendas').update(row_dict).eq('id', id_val).execute()
                    success_count += 1
                except Exception as e:
                    st.error(f"Erro na linha ID {id_val}: {str(e)}")
                    error_count += 1
            st.cache_data.clear()
            if error_count == 0:
                st.success(f"✅ {success_count} alterações salvas!")
            else:
                st.warning(f"Salvas {success_count}, erros: {error_count}")
            st.rerun()

with tab2:
    st.header("Relatórios com Filtros")

    df = st.session_state.df or load_vendas()

    # Filtros na sidebar
    with st.sidebar:
        st.header("🔍 Filtros")
        if not df.empty:
            min_date = df['data_venda'].min()
            max_date = df['data_venda'].max()
            data_inicio = st.date_input("Data Início", value=min_date, min_value=min_date, max_value=max_date)
            data_fim = st.date_input("Data Fim", value=max_date, min_value=min_date, max_value=max_date)

            est_unique = sorted(df['estabelecimento'].dropna().unique())
            estabelecimentos = st.multiselect("Estabelecimento", est_unique, default=est_unique)

            bairro_unique = sorted(df['bairro'].dropna().unique())
            bairros = st.multiselect("Bairro", bairro_unique, default=bairro_unique)

            forma_unique = sorted(df['forma_pagamento'].dropna().unique())
            formas = st.multiselect("Forma Pagamento", forma_unique, default=forma_unique)
        else:
            st.info("Carregue dados na aba Listagem.")
            data_inicio = data_fim = date.today()
            estabelecimentos = bairros = formas = []

    # Aplicar filtros
    filtered_df = df[(df['data_venda'] >= data_inicio) & (df['data_venda'] <= data_fim)].copy()
    if estabelecimentos:
        filtered_df = filtered_df[filtered_df['estabelecimento'].isin(estabelecimentos)]
    if bairros:
        filtered_df = filtered_df[filtered_df['bairro'].isin(bairros)]
    if formas:
        filtered_df = filtered_df[filtered_df['forma_pagamento'].isin(formas)]

    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    total_faturamento = filtered_df['total_venda'].sum()
    total_comissao = filtered_df['valor_comissao'].sum()
    qtd_vendas = len(filtered_df)
    ticket_medio = total_faturamento / qtd_vendas if qtd_vendas > 0 else 0

    with col1:
        st.metric("Faturamento", f"R$ {total_faturamento:,.2f}")
    with col2:
        st.metric("Comissão", f"R$ {total_comissao:,.2f}")
    with col3:
        st.metric("Vendas", qtd_vendas)
    with col4:
        st.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")

    # Tabela filtrada
    st.subheader("Tabela Filtrada")
    st.dataframe(filtered_df, use_container_width=True, hide_index=False)

    # Gráficos Plotly
    if not filtered_df.empty:
        st.subheader("Gráficos")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_est = px.bar(
                filtered_df.groupby('estabelecimento')['total_venda'].sum().reset_index(),
                x='estabelecimento', y='total_venda',
                title="Faturamento por Estabelecimento"
            )
            st.plotly_chart(fig_est, use_container_width=True)

        with col_g2:
            fig_forma = px.pie(
                filtered_df, names='forma_pagamento', values='total_venda',
                title="Distribuição por Forma de Pagamento"
            )
            st.plotly_chart(fig_forma, use_container_width=True)

        col_g3, col_g4 = st.columns(2)
        with col_g3:
            daily_sales = filtered_df.groupby('data_venda')['total_venda'].sum().reset_index()
            fig_daily = px.line(daily_sales, x='data_venda', y='total_venda', title="Evolução Diária")
            st.plotly_chart(fig_daily, use_container_width=True)

        with col_g4:
            fig_bairro = px.bar(
                filtered_df.groupby('bairro')['total_venda'].sum().reset_index(),
                x='bairro', y='total_venda',
                title="Faturamento por Bairro"
            )
            st.plotly_chart(fig_bairro, use_container_width=True)
    else:
        st.info("Aplique filtros para ver gráficos.")