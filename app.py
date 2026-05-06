import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from supabase import create_client, Client
from datetime import datetime

st.set_page_config(page_title="Controle de Vendas", layout="wide")

@st.cache_resource
def init_supabase():
    try:
        supabase_config = st.secrets['supabase']
        url = supabase_config.get('url')
        key = supabase_config.get('key')
        if url and key:
            return create_client(url, key)
        else:
            st.error("Configurações do Supabase não encontradas em secrets.")
            return None
    except Exception as e:
        st.error(f"Erro ao inicializar Supabase: {str(e)}")
        return None

supabase: Client = init_supabase()
if not supabase:
    st.stop()

def load_vendas():
    response = supabase.table('vendas').select('*').order('data_venda').execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['data_venda'] = pd.to_datetime(df['data_venda'])
        for col in ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

st.title("🛒 Controle de Vendas")

if not st.session_state.logged_in:
    st.subheader("Login")
    with st.form("login_form"):
        username = st.text_input("Usuário", placeholder="paodequeijo")
        password = st.text_input("Senha", type="password", placeholder="vendas2026")
        col1, col2 = st.columns([4,1])
        with col2:
            login_button = st.form_submit_button("Entrar", use_container_width=True)
        if login_button:
            if username:
                response = supabase.table('users').select('password_hash').eq('username', username).execute()
                user_data = response.data
                if user_data:
                    stored_hash = user_data[0]['password_hash']
                    input_hash = hashlib.sha256(password.strip().encode('utf-8')).hexdigest()
                    if input_hash == stored_hash:
                        st.session_state.logged_in = True
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                        st.error(f"Debug - Hash gerado: {input_hash}")
                else:
                    st.error("Usuário não encontrado.")
            else:
                st.error("Informe o usuário.")
else:
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    tab1, tab2 = st.tabs(["Gerenciar Registros", "Relatórios"])

    with tab1:
        st.subheader("Gerenciar Registros (Apenas Exclusão)")
        df = load_vendas()
        if df.empty:
            st.info("Nenhum registro encontrado.")
        else:
            column_config = {
                "id": st.column_config.TextColumn("ID", disabled=False),
                "estabelecimento": st.column_config.TextColumn("Estabelecimento"),
                "data_venda": st.column_config.DateColumn("Data da Venda"),
                "bairro": st.column_config.TextColumn("Bairro"),
                "forma_pagamento": st.column_config.TextColumn("Forma de Pagamento"),
                "produto": st.column_config.TextColumn("Produto"),
                "quantidade": st.column_config.NumberColumn("Quantidade", format="%.0f"),
                "valor_produto": st.column_config.NumberColumn("Valor Produto", format="%.2f"),
                "total_venda": st.column_config.NumberColumn("Total Venda", format="%.2f"),
                "comissao_percentual": st.column_config.NumberColumn("Comissão %", format="%.2f"),
                "valor_comissao": st.column_config.NumberColumn("Valor Comissão", format="%.2f"),
                "status": st.column_config.TextColumn("Status"),
            }
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config=column_config,
                hide_index=False,
                use_container_width=True,
                key="data_editor",
            )
            if st.button("Confirmar Exclusões", type="primary"):
                original_ids = set(df['id'].astype(str))
                current_ids = set(edited_df['id'].dropna().astype(str))
                to_delete = original_ids - current_ids
                deleted_count = 0
                for id_str in to_delete:
                    resp = supabase.table('vendas').delete().eq('id', id_str).execute()
                    if len(resp.data) > 0:
                        deleted_count += 1
                if deleted_count > 0:
                    st.success(f"{deleted_count} registro(s) excluído(s) com sucesso!")
                    st.rerun()
                else:
                    st.info("Nenhuma exclusão realizada.")

    with tab2:
        st.subheader("Relatórios")
        df = load_vendas()
        if df.empty:
            st.info("Nenhum dado para relatórios.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                unique_estabs = sorted(df['estabelecimento'].dropna().unique())
                selected_estabs = st.multiselect("Estabelecimento", options=unique_estabs, default=unique_estabs)
            with col2:
                unique_bairros = sorted(df['bairro'].dropna().unique())
                selected_bairros = st.multiselect("Bairro", options=unique_bairros, default=unique_bairros)
            with col3:
                unique_formas = sorted(df['forma_pagamento'].dropna().unique())
                selected_formas = st.multiselect("Forma de Pagamento", options=unique_formas, default=unique_formas)
            with col4:
                min_date = df['data_venda'].min().date()
                max_date = df['data_venda'].max().date()
                selected_dates = st.date_input("Período", value=(min_date, max_date), min_value=min_date, max_value=max_date)

            if len(selected_dates) == 2:
                mask = (
                    df['estabelecimento'].isin(selected_estabs) &
                    df['bairro'].isin(selected_bairros) &
                    df['forma_pagamento'].isin(selected_formas) &
                    (df['data_venda'].dt.date >= selected_dates[0]) &
                    (df['data_venda'].dt.date <= selected_dates[1])
                )
                filtered_df = df[mask]

                if not filtered_df.empty:
                    total_vendas = filtered_df['total_venda'].sum()
                    total_comissao = filtered_df['valor_comissao'].sum()
                    qtd_registros = len(filtered_df)

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Vendas", f"R$ {total_vendas:,.2f}")
                    c2.metric("Total Comissão", f"R$ {total_comissao:,.2f}")
                    c3.metric("Registros", qtd_registros)

                    col1, col2 = st.columns(2)
                    with col1:
                        vendas_por_estab = filtered_df.groupby('estabelecimento')['total_venda'].sum().reset_index()
                        fig_bar = px.bar(vendas_por_estab, x='estabelecimento', y='total_venda',
                                         title="Vendas por Estabelecimento")
                        st.plotly_chart(fig_bar, use_container_width=True)
                    with col2:
                        fig_pie = px.pie(filtered_df, names='forma_pagamento', values='total_venda',
                                         title="Distribuição por Forma de Pagamento")
                        st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("Nenhum registro encontrado com os filtros selecionados.")
            else:
                st.info("Selecione o período para visualizar os relatórios.")