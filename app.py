import streamlit as st
import pandas as pd
from supabase import create_client, Client
import hashlib
from datetime import date

st.set_page_config(page_title="App Vendas", layout="wide")

# Carregar secrets
SUPABASE_URL = st.secrets['supabase']['url'].strip()
SUPABASE_KEY = st.secrets['supabase']['key'].strip()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Estado da sessão para login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login():
    st.title("🔑 Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        result = supabase.table('users').select('password_hash').eq('username', username).execute()
        if result.data:
            stored_hash = result.data[0]['password_hash']
            if hash_password(password) == stored_hash:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Senha incorreta!")
        else:
            st.error("Usuário não encontrado!")

if not st.session_state.logged_in:
    login()
else:
    # Sidebar
    st.sidebar.title("Menu")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["Nova Venda", "Editar Vendas", "Relatórios"])

    with tab1:
        st.header("Nova Venda")
        with st.form("nova_venda"):
            data_venda = st.date_input("Data", value=date.today())
            produto = st.text_input("Produto")
            quantidade = st.number_input("Quantidade", min_value=1, step=1)
            valor_unit = st.number_input("Valor Unitário", min_value=0.01, step=0.01, format="%.2f")
            total = quantidade * valor_unit
            st.info(f"Total: R$ {total:.2f}")
            if st.form_submit_button("Salvar"):
                data_insert = {
                    "data": data_venda.isoformat(),
                    "produto": produto,
                    "quantidade": float(quantidade),
                    "valor_unit": float(valor_unit),
                    "total": float(total),
                    "usuario": st.session_state.username
                }
                result = supabase.table('vendas').insert(data_insert).execute()
                if result.data:
                    st.success("Venda salva com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao salvar venda!")

    with tab2:
        st.header("Editar Vendas")
        vendas = supabase.table('vendas').select("*").eq('usuario', st.session_state.username).order('data').execute()
        df = pd.DataFrame(vendas.data)
        if not df.empty:
            edited_df = st.data_editor(
                df,
                column_config={
                    "data": st.column_config.DateColumn("Data"),
                    "quantidade": st.column_config.NumberColumn("Quantidade", min_value=0, step=1),
                    "valor_unit": st.column_config.NumberColumn("Valor Unit.", min_value=0.0, step=0.01, format="%.2f"),
                    "total": st.column_config.NumberColumn("Total", format="%.2f"),
                },
                num_rows="dynamic",
                use_container_width=True,
                hide_index=False
            )
            if st.button("Salvar Alterações"):
                for idx, row in edited_df.iterrows():
                    update_data = {
                        "data": row['data'].isoformat() if hasattr(row['data'], 'isoformat') else str(row['data']),
                        "produto": row['produto'],
                        "quantidade": float(row['quantidade']),
                        "valor_unit": float(row['valor_unit']),
                        "total": float(row['total']),
                    }
                    supabase.table('vendas').update(update_data).eq('id', row['id']).execute()
                st.success("Alterações salvas!")
                st.rerun()
        else:
            st.info("Nenhuma venda encontrada.")

    with tab3:
        st.header("Relatórios e Gráficos")
        # Filtros dinâmicos
        prod_result = supabase.table('vendas').select('produto').eq('usuario', st.session_state.username).execute()
        produtos = ["Todos"] + sorted(list({row['produto'] for row in prod_result.data if row['produto']}));

        col1, col2, col3 = st.columns(3)
        with col1:
            data_inicio = st.date_input("Data Início", value=date.today())
        with col2:
            data_fim = st.date_input("Data Fim", value=date.today())
        with col3:
            produto_filtro = st.selectbox("Produto", produtos)

        # Query filtrada
        query = supabase.table('vendas').select("*").eq('usuario', st.session_state.username)
        if data_inicio:
            query = query.gte('data', data_inicio.isoformat())
        if data_fim:
            query = query.lte('data', data_fim.isoformat())
        if produto_filtro != "Todos":
            query = query.eq('produto', produto_filtro)
        result = query.execute()
        rel_df = pd.DataFrame(result.data)

        if not rel_df.empty:
            rel_df['data'] = pd.to_datetime(rel_df['data'])
            rel_df['total'] = pd.to_numeric(rel_df['total'])

            st.subheader("Tabela de Vendas")
            st.dataframe(rel_df)

            st.subheader("Gráficos")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig1 = px.bar(rel_df, x='data', y='total', title="Vendas por Data", color='produto')
                st.plotly_chart(fig1, use_container_width=True)
            with col_g2:
                fig2 = px.pie(rel_df, names='produto', values='total', title="Distribuição por Produto")
                st.plotly_chart(fig2, use_container_width=True)

            # Totais
            total_geral = rel_df['total'].sum()
            st.metric("Total Geral", f"R$ {total_geral:.2f}")
        else:
            st.info("Nenhum dado encontrado com os filtros selecionados.")