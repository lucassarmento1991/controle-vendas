import streamlit as st
import pandas as pd
import hashlib
from st_gsheets_connection import GSheetsConnection
from datetime import date

st.set_page_config(page_title="Sistema de Vendas", page_icon="💰", layout="wide")

# CSS profissional
st.markdown("""
<style>
    header {visibility: hidden;}
    .block-container {padding-top: 2rem;}
    .st-emotion-cache-1yfp8bb h1 {font-size: 2.5rem; color: #1f77b4; text-align: center;}
    .stButton > button {
        background: linear-gradient(45deg, #4CAF50, #45a049);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #ddd;
    }
    .stMetric > label {font-size: 1.2rem;}
    .stMetric > div {font-size: 2rem; color: #1f77b4;}
</style>
""", unsafe_allow_html=True)

# Inicializar session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

conn = st.connection("gsheets", type=GSheetsConnection)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Página de Login
if not st.session_state.logged_in:
    st.title("🔐 Login no Sistema de Vendas")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            col_a, col_b = st.columns([1, 1])
            with col_b:
                submitted = st.form_submit_button("Entrar")
            if submitted:
                df_users = conn.read(sheet="usuarios")
                if df_users is not None and not df_users.empty:
                    user_mask = df_users['username'] == username
                    if user_mask.any():
                        stored_hash = df_users.loc[user_mask, 'password_hash'].iloc[0]
                        if hash_password(password) == stored_hash:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.role = df_users.loc[user_mask, 'role'].iloc[0]
                            st.success("Login realizado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Senha incorreta!")
                    else:
                        st.error("Usuário não encontrado!")
                else:
                    st.error("Planilha de usuários não encontrada ou vazia!")
else:
    # App principal
    st.title("💰 Sistema de Gerenciamento de Vendas")

    # Sidebar navegação
    st.sidebar.title("Navegação")
    if st.session_state.role == "admin":
        pages = ["Cadastro de Vendas", "Listagem de Vendas", "Relatórios", "Gerenciar Usuários"]
    else:
        pages = ["Cadastro de Vendas", "Listagem de Vendas", "Relatórios"]
    page = st.sidebar.selectbox("Selecione uma página:", pages)

    st.sidebar.markdown("---")
    st.sidebar.info(f"👤 **{st.session_state.username}**")
    st.sidebar.info(f"📋 **{st.session_state.role.upper()}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.rerun()

    # Páginas
    if page == "Cadastro de Vendas":
        st.header("📝 Cadastro de Nova Venda")
        with st.form("cadastro_venda"):
            col1, col2 = st.columns(2)
            with col1:
                estabelecimento = st.text_input("Estabelecimento")
                data_venda = st.date_input("Data da Venda", value=date.today())
                bairro = st.text_input("Bairro")
                forma_pag = st.selectbox("Forma de Pagamento", ["Dinheiro", "Pix", "Cartão Débito", "Cartão Crédito"])
            with col2:
                produto = st.text_input("Produto")
                quantidade = st.number_input("Quantidade", min_value=1, step=1)
                valor_produto = st.number_input("Valor Unitário (R$)", min_value=0.0, step=0.01, format="%.2f")
                comissao_perc = st.number_input("Comissão %", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
            col_t, col_c = st.columns(2)
            total_venda = quantidade * valor_produto
            valor_comissao = total_venda * (comissao_perc / 100)
            with col_t:
                st.metric("Total Venda", f"R$ {total_venda:.2f}")
            with col_c:
                st.metric("Valor Comissão", f"R$ {valor_comissao:.2f}")
            submitted = st.form_submit_button("🚀 Cadastrar Venda")
            if submitted:
                if estabelecimento and bairro and produto:
                    new_row = {
                        "Estabelecimento": estabelecimento,
                        "Data_Venda": data_venda.strftime("%Y-%m-%d"),
                        "Bairro": bairro,
                        "Forma_Pagamento": forma_pag,
                        "Produto": produto,
                        "Quantidade": quantidade,
                        "Valor_Produto": valor_produto,
                        "Total_Venda": total_venda,
                        "Comissao_Percentual": comissao_perc,
                        "Valor_Comissao": valor_comissao,
                        "Status": "ativa"
                    }
                    df_vendas = conn.read(sheet="Página1")
                    if df_vendas is None or df_vendas.empty:
                        df_vendas = pd.DataFrame([new_row])
                    else:
                        df_vendas = pd.concat([df_vendas, pd.DataFrame([new_row])], ignore_index=True)
                    conn.update(sheet="Página1", data=df_vendas)
                    st.success("✅ Venda cadastrada com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Preencha todos os campos obrigatórios!")

    elif page == "Listagem de Vendas":
        st.header("📋 Listagem de Vendas")
        df_vendas = conn.read(sheet="Página1")
        if df_vendas is None or df_vendas.empty:
            st.info("Nenhuma venda cadastrada ainda.")
        else:
            st.dataframe(df_vendas, use_container_width=True)
            st.markdown("---")
            st.subheader("Ações de Cancelamento")
            for idx in df_vendas.index:
                if df_vendas.loc[idx, "Status"] == "ativa":
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{df_vendas.loc[idx, 'Produto']}** - {df_vendas.loc[idx, 'Estabelecimento']} | R$ {df_vendas.loc[idx, 'Total_Venda']:.2f}")
                    with col2:
                        if st.button("❌ Cancelar", key=f"cancel_{idx}"):
                            df_update = df_vendas.copy()
                            df_update.loc[idx, "Status"] = "cancelada"
                            conn.update(sheet="Página1", data=df_update)
                            st.success("Venda cancelada!")
                            st.rerun()

    elif page == "Relatórios":
        st.header("📊 Relatórios")
        df_vendas = conn.read(sheet="Página1")
        if df_vendas is None or df_vendas.empty:
            st.info("Nenhuma venda para relatórios.")
        else:
            df_ativa = df_vendas[df_vendas["Status"] == "ativa"].copy()
            if df_ativa.empty:
                st.info("Nenhuma venda ativa.")
            else:
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    data_de = st.date_input("Data De")
                with col_f2:
                    data_ate = st.date_input("Data Até")
                with col_f3:
                    estabs = st.multiselect("Estabelecimentos", df_ativa["Estabelecimento"].unique())
                df_filt = df_ativa.copy()
                df_filt["Data_Venda_dt"] = pd.to_datetime(df_filt["Data_Venda"])
                if data_de:
                    df_filt = df_filt[df_filt["Data_Venda_dt"] >= pd.to_datetime(data_de)]
                if data_ate:
                    df_filt = df_filt[df_filt["Data_Venda_dt"] <= pd.to_datetime(data_ate)]
                if estabs:
                    df_filt = df_filt[df_filt["Estabelecimento"].isin(estabs)]
                total_vendas = df_filt["Total_Venda"].sum()
                total_comissao = df_filt["Valor_Comissao"].sum()
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Vendas", f"R$ {total_vendas:.2f}")
                col2.metric("Total Comissões", f"R$ {total_comissao:.2f}")
                col3.metric("Qtd. Vendas", len(df_filt))
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    st.subheader("Vendas por Estabelecimento")
                    chart_data = df_filt.groupby("Estabelecimento")["Total_Venda"].sum()
                    st.bar_chart(chart_data)
                with col_chart2:
                    st.subheader("Comissões por Estabelecimento")
                    chart_com = df_filt.groupby("Estabelecimento")["Valor_Comissao"].sum()
                    st.bar_chart(chart_com)
                st.subheader("Vendas Filtradas")
                st.dataframe(df_filt.drop(columns=["Data_Venda_dt"]), use_container_width=True)

    elif page == "Gerenciar Usuários":
        st.header("👥 Gerenciar Usuários")
        df_users = conn.read(sheet="usuarios")
        if df_users is None or df_users.empty:
            st.info("Nenhum usuário cadastrado.")
        else:
            st.dataframe(df_users, use_container_width=True)
            st.markdown("---")
            st.subheader("➕ Adicionar Novo Usuário")
            with st.form("add_user_form"):
                new_username = st.text_input("Novo Usuário")
                new_password = st.text_input("Nova Senha", type="password")
                new_role = st.selectbox("Role", ["user", "admin"])
                submitted_add = st.form_submit_button("Adicionar")
                if submitted_add:
                    if new_username and new_password:
                        if new_username not in df_users["username"].values:
                            new_hash = hash_password(new_password)
                            new_row = {"username": new_username, "password_hash": new_hash, "role": new_role}
                            df_new_users = pd.concat([df_users, pd.DataFrame([new_row])], ignore_index=True)
                            conn.update(sheet="usuarios", data=df_new_users)
                            st.success("Usuário adicionado!")
                            st.rerun()
                        else:
                            st.error("Usuário já existe!")
                    else:
                        st.error("Preencha usuário e senha!")
            st.markdown("---")
            st.subheader("🗑️ Remover Usuário")
            for idx in df_users.index:
                if df_users.loc[idx, "username"] != st.session_state.username:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{df_users.loc[idx, 'username']}** ({df_users.loc[idx, 'role']})")
                    with col2:
                        if st.button("Deletar", key=f"del_{idx}"):
                            df_update_users = df_users.drop(idx).reset_index(drop=True)
                            conn.update(sheet="usuarios", data=df_update_users)
                            st.success("Usuário removido!")
                            st.rerun()
                else:
                    st.warning("Não é possível remover o próprio usuário.")
