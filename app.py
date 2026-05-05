import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
from datetime import date
import hashlib

st.set_page_config(page_title="Gestão de Vendas", page_icon="💰", layout="wide")

st.markdown("""
<style>
    .main {padding-top: 2rem;}
    section[data-testid="stSidebar"] {width: 300px;}
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@st.cache_resource
def load_sheets():
    creds_dict = st.secrets["connections"]["gsheets"]
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open_by_url(creds_dict["spreadsheet"])
    return sh

sh = load_sheets()

@st.cache_data(ttl=60)
def load_sales_df():
    ws = sh.worksheet('Página1')
    all_values = ws.get_all_values()
    if len(all_values) <= 1:
        return pd.DataFrame()
    df = pd.DataFrame(all_values[1:], columns=all_values[0])
    df['row_num'] = range(2, len(df) + 2)
    numeric_cols = ['Quantidade', 'Valor_Produto', 'Total_Venda', 'Comissao_Percentual', 'Valor_Comissao']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    if 'Data_Venda' in df.columns:
        df['Data_Venda'] = pd.to_datetime(df['Data_Venda'], dayfirst=True, errors='coerce')
    return df

@st.cache_data(ttl=60)
def load_users_df():
    ws = sh.worksheet('usuarios')
    all_values = ws.get_all_values()
    if len(all_values) <= 1:
        return pd.DataFrame()
    df = pd.DataFrame(all_values[1:], columns=all_values[0])
    df['row_num'] = range(2, len(df) + 2)
    return df

if not st.session_state.logged_in:
    st.title("🔐 Login")
    col_login1, col_login2 = st.columns([1, 2])
    with col_login1:
        st.image("https://via.placeholder.com/300x200/4A90E2/white?text=Gestão+de+Vendas", use_column_width=True)
    with col_login2:
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            users_df = load_users_df()
            if not users_df.empty:
                matching_user = users_df[users_df['username'] == username]
                if not matching_user.empty:
                    if matching_user.iloc[0]['password_hash'] == hash_password(password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.role = matching_user.iloc[0]['role']
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("Usuário não encontrado.")
            else:
                st.error("Nenhum usuário cadastrado na planilha 'usuarios'.")
else:
    st.sidebar.title("Navegação")
    st.sidebar.info(f"👤 {st.session_state.username} | {st.session_state.role.upper()}")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.rerun()

    st.title("💰 Gestão de Vendas")
    tab1, tab2, tab3, tab4 = st.tabs(["📥 Cadastro de Vendas", "📋 Listagem de Vendas", "📊 Relatórios", "👥 Gerenciamento de Usuários"])

    with tab1:
        st.subheader("Nova Venda")
        with st.form("cadastro_venda"):
            col1, col2 = st.columns(2)
            with col1:
                estabelecimento = st.text_input("Estabelecimento")
                data_venda = st.date_input("Data da Venda", value=date.today()).strftime("%d/%m/%Y")
                bairro = st.text_input("Bairro")
                forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Pix", "Cartão", "Boleto"])
            with col2:
                produto = st.text_input("Produto")
                quantidade = st.number_input("Quantidade", min_value=1, step=1)
                valor_produto = st.number_input("Valor do Produto (R$)", min_value=0.0, format="%.2f", step=0.01)
                comissao_percentual = st.number_input("Comissão (%)", min_value=0.0, max_value=100.0, step=0.1)
            total_venda = quantidade * valor_produto
            valor_comissao = total_venda * (comissao_percentual / 100)
            col_info1, col_info2 = st.columns(2)
            col_info1.info(f"**Total Venda: R$ {total_venda:.2f}**")
            col_info2.info(f"**Comissão: R$ {valor_comissao:.2f}**")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submitted = st.form_submit_button("✅ Cadastrar Venda")
        if submitted:
            if all([estabelecimento, bairro, produto]):
                ws = sh.worksheet('Página1')
                row = [estabelecimento, data_venda, bairro, forma_pagamento, produto, int(quantidade), float(valor_produto), float(total_venda), float(comissao_percentual), float(valor_comissao), 'ativa']
                ws.append_row(row)
                st.success("Venda cadastrada com sucesso!")
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios.")

    with tab2:
        st.subheader("Vendas Ativas")
        sales_df = load_sales_df()
        df_ativa = sales_df[sales_df['Status'] == 'ativa'].copy()
        if not df_ativa.empty:
            st.dataframe(df_ativa.drop(columns=['row_num', 'Status']), use_container_width=True)
            st.markdown("---")
            status_col = sales_df.columns.get_loc('Status') + 1
            for _, row in df_ativa.iterrows():
                col1, col2, col3 = st.columns([1, 4, 1])
                with col1:
                    st.write(f"**{row['Estabelecimento']}**")
                with col2:
                    st.write(f"{row['Produto']} × {int(row['Quantidade'])} | {row['Bairro']} | {row['Data_Venda'].strftime('%d/%m/%Y')} | R$ {row['Total_Venda']:.2f}")
                with col3:
                    if st.button("❌ Cancelar", key=f"cancel_sale_{row['row_num']}"):
                        ws = sh.worksheet('Página1')
                        ws.update_cell(int(row['row_num']), status_col, 'cancelada')
                        st.success("Venda cancelada!")
                        st.rerun()
        else:
            st.info("Nenhuma venda ativa.")

    with tab3:
        st.subheader("Relatórios")
        sales_df = load_sales_df()
        df_ativa = sales_df[sales_df['Status'] == 'ativa'].copy()
        if df_ativa.empty:
            st.info("Nenhuma venda ativa para relatórios.")
        else:
            col1, col2, col3 = st.columns(3)
            total_vendas = len(df_ativa)
            total_faturamento = df_ativa['Total_Venda'].sum()
            total_comissoes = df_ativa['Valor_Comissao'].sum()
            with col1:
                st.metric("Total Vendas", total_vendas)
            with col2:
                st.metric("Faturamento", f"R$ {total_faturamento:.2f}")
            with col3:
                st.metric("Comissões", f"R$ {total_comissoes:.2f}")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                prod_group = df_ativa.groupby('Produto')['Total_Venda'].sum().reset_index()
                fig1 = px.bar(prod_group, x='Produto', y='Total_Venda', title="Total por Produto")
                st.plotly_chart(fig1, use_container_width=True)
            with col_g2:
                bairro_group = df_ativa.groupby('Bairro')['Total_Venda'].sum().reset_index()
                fig2 = px.bar(bairro_group, x='Bairro', y='Total_Venda', title="Total por Bairro")
                st.plotly_chart(fig2, use_container_width=True)
            col_g3, col_g4 = st.columns(2)
            with col_g3:
                forma_counts = df_ativa['Forma_Pagamento'].value_counts()
                fig3 = px.pie(values=forma_counts.values, names=forma_counts.index, title="Forma de Pagamento")
                st.plotly_chart(fig3, use_container_width=True)
            with col_g4:
                df_ativa['data_date'] = df_ativa['Data_Venda'].dt.date
                date_group = df_ativa.groupby('data_date')['Total_Venda'].sum().reset_index()
                fig4 = px.line(date_group, x='data_date', y='Total_Venda', title="Evolução por Data")
                st.plotly_chart(fig4, use_container_width=True)

    with tab4:
        if st.session_state.role != 'admin':
            st.warning("🔒 Acesso restrito a administradores.")
        else:
            st.subheader("Gerenciamento de Usuários")
            users_df = load_users_df()
            if not users_df.empty:
                st.dataframe(users_df[['username', 'role']].drop(columns=['row_num'], errors='ignore'), use_container_width=True)
            with st.expander("➕ Adicionar Usuário"):
                new_username = st.text_input("Novo Usuário")
                new_password = st.text_input("Nova Senha", type="password")
                new_role = st.selectbox("Role", ["user", "admin"])
                if st.button("Adicionar"):
                    if new_username and new_password:
                        if new_username not in users_df['username'].values:
                            ws_users = sh.worksheet('usuarios')
                            hashed_pw = hash_password(new_password)
                            ws_users.append_row([new_username, hashed_pw, new_role])
                            st.success("Usuário adicionado!")
                            st.rerun()
                        else:
                            st.error("Usuário já existe.")
                    else:
                        st.error("Preencha usuário e senha.")
            st.markdown("---")
            if not users_df.empty:
                for _, row in users_df.iterrows():
                    col_u1, col_u2 = st.columns([3, 1])
                    with col_u1:
                        st.write(f"**{row['username']}** ({row['role']})")
                    with col_u2:
                        if st.button("🗑️ Remover", key=f"del_user_{row['row_num']}"):
                            ws_users = sh.worksheet('usuarios')
                            ws_users.delete_rows(int(row['row_num']))
                            st.success("Usuário removido!")
                            st.rerun()
            else:
                st.info("Nenhum usuário encontrado.")