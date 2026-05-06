import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
import hashlib
import os

st.set_page_config(page_title="Sistema de Vendas", page_icon="📊", layout="wide")
st.markdown("""<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>""", unsafe_allow_html=True)

@st.cache_resource
def init_supabase():
    try:
        supabase_url = st.secrets["supabase"]["url"]
        supabase_key = st.secrets["supabase"]["key"]
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Erro ao inicializar Supabase: {str(e)}")
        st.stop()

supabase: Client = init_supabase()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login")
    with st.form("login_form"):
        username = st.text_input("Usuário", placeholder="paodequeijo")
        password = st.text_input("Senha", type="password", placeholder="vendas2026")
        col1, col2 = st.columns([4,1])
        with col2:
            submit = st.form_submit_button("Entrar", use_container_width=True)
        if submit:
            if not username or not password:
                st.error("Preencha usuário e senha.")
            else:
                try:
                    resp = supabase.table('usuarios').select('password_hash').eq('username', username.strip()).execute()
                    if resp.data:
                        stored_hash = resp.data[0]['password_hash']
                        input_hash = hashlib.sha256(password.encode()).hexdigest()
                        if input_hash == stored_hash:
                            st.session_state.logged_in = True
                            st.success("Login realizado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Senha incorreta.")
                    else:
                        st.error("Usuário não encontrado.")
                except Exception as e:
                    st.error(f"Erro no login: {str(e)}")
else:
    st.title("📊 Sistema de Vendas")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    @st.cache_data(ttl=300)
    def load_vendas():
        try:
            resp = supabase.table('vendas').select('*').order('data_venda', desc=True).execute()
            df = pd.DataFrame(resp.data)
            # Ensure correct dtypes
            df['data_venda'] = pd.to_datetime(df['data_venda'])
            df['id'] = df['id'].astype(int)
            df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce').fillna(0).astype(int)
            numeric_cols = ['valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        except Exception as e:
            st.error(f"Erro ao carregar vendas: {str(e)}")
            return pd.DataFrame()

    tab1, tab2 = st.tabs(["Gerenciar", "Relatórios"])

    with tab1:
        st.header("Gerenciar Vendas (Apenas Exclusão)")
        df_original = load_vendas()
        if df_original.empty:
            st.info("Nenhuma venda encontrada.")
        else:
            column_config = {}
            for col in df_original.columns:
                if col == 'id':
                    column_config[col] = st.column_config.NumberColumn(col, disabled=True)
                elif col == 'data_venda':
                    column_config[col] = st.column_config.DateColumn(col, disabled=True, format="YYYY-MM-DD")
                elif col in ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']:
                    column_config[col] = st.column_config.NumberColumn(col, disabled=True, format="%.2f")
                else:
                    column_config[col] = st.column_config.TextColumn(col, disabled=True)

            edited_df = st.data_editor(
                df_original,
                column_config=column_config,
                hide_index=False,
                use_column_sequence=True,
                height=600,
                key="vendas_editor"
            )

            original_ids = set(df_original['id'])
            current_ids = set(edited_df['id'])
            ids_to_delete = original_ids - current_ids

            if ids_to_delete:
                st.warning(f"🗑️ {len(ids_to_delete)} linha(s) selecionada(s) para exclusão.")
                if st.button("Confirmar Exclusões", type="primary", use_container_width=True):
                    deleted_count = 0
                    for rid in ids_to_delete:
                        resp = supabase.table('vendas').delete().eq('id', rid).execute()
                        if resp.data:
                            deleted_count += 1
                    st.cache_data.clear()
                    st.success(f"✅ {deleted_count} venda(s) excluída(s) com sucesso!")
                    st.rerun()
            else:
                st.info("Nenhuma exclusão pendente.")

    with tab2:
        st.header("Relatórios")
        df = load_vendas()
        if df.empty:
            st.info("Nenhuma venda para relatórios.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                estab_options = sorted(df['estabelecimento'].dropna().unique())
                selected_estabs = st.multiselect("Estabelecimento", options=estab_options, default=estab_options)

                forma_options = sorted(df['forma_pagamento'].dropna().unique())
                selected_formas = st.multiselect("Forma de Pagamento", options=forma_options, default=forma_options)

            with col2:
                bairro_options = sorted(df['bairro'].dropna().unique())
                selected_bairros = st.multiselect("Bairro", options=bairro_options, default=bairro_options)

                min_date = df['data_venda'].min().date()
                max_date = df['data_venda'].max().date()
                col_a, col_b = st.columns(2)
                with col_a:
                    data_inicio = st.date_input("Data Início", value=min_date, min_value=min_date, max_value=max_date)
                with col_b:
                    data_fim = st.date_input("Data Fim", value=max_date, min_value=min_date, max_value=max_date)

            df_filtered = df[
                (df['estabelecimento'].isin(selected_estabs)) &
                (df['forma_pagamento'].isin(selected_formas)) &
                (df['bairro'].isin(selected_bairros)) &
                (df['data_venda'].dt.date >= data_inicio) &
                (df['data_venda'].dt.date <= data_fim)
            ].copy()

            if df_filtered.empty:
                st.info("Nenhum dado com os filtros selecionados.")
            else:
                col1, col2, col3, col4 = st.columns(4)
                total_vendas = df_filtered['total_venda'].sum()
                total_comissao = df_filtered['valor_comissao'].sum()
                qtd_vendas = len(df_filtered)
                avg_ticket = total_vendas / qtd_vendas if qtd_vendas > 0 else 0

                col1.metric("Total Vendas", f"R$ {total_vendas:,.2f}")
                col2.metric("Total Comissão", f"R$ {total_comissao:,.2f}")
                col3.metric("Qtd. Vendas", qtd_vendas)
                col4.metric("Ticket Médio", f"R$ {avg_ticket:,.2f}")

                col1, col2 = st.columns(2)
                with col1:
                    vendas_por_data = df_filtered.groupby('data_venda')['total_venda'].sum().reset_index()
                    fig1 = px.line(vendas_por_data, x='data_venda', y='total_venda', title="Vendas por Data")
                    st.plotly_chart(fig1, use_container_width=True)

                with col2:
                    vendas_porForma = df_filtered.groupby('forma_pagamento')['total_venda'].sum().reset_index()
                    fig2 = px.pie(vendas_porForma, values='total_venda', names='forma_pagamento', title="Vendas por Forma de Pagamento")
                    st.plotly_chart(fig2, use_container_width=True)

                col3, col4 = st.columns(2)
                with col3:
                    vendas_por_estab = df_filtered.groupby('estabelecimento')['total_venda'].sum().reset_index()
                    fig3 = px.bar(vendas_por_estab, x='estabelecimento', y='total_venda', title="Vendas por Estabelecimento")
                    st.plotly_chart(fig3, use_container_width=True)

                with col4:
                    vendas_por_bairro = df_filtered.groupby('bairro')['total_venda'].sum().reset_index()
                    fig4 = px.bar(vendas_por_bairro, x='bairro', y='total_venda', title="Vendas por Bairro")
                    st.plotly_chart(fig4, use_container_width=True)