import streamlit as st
import pandas as pd
import hashlib
from supabase import create_client
from datetime import date

st.set_page_config(page_title="Sistema de Vendas", layout="wide")
st.title("Sistema de Vendas")

# Configurar Supabase
url = st.secrets["supabase"]["url"].strip()
key = st.secrets["supabase"]["key"].strip()
supabase: create_client = create_client(url, key)

# Gerenciar estado de login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if username and password:
            try:
                hash_pass = hashlib.sha256(password.encode()).hexdigest()
                response = supabase.table("usuarios").select("password_hash").eq("username", username).execute()
                if response.data and len(response.data) > 0 and response.data[0]["password_hash"] == hash_pass:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
            except Exception as e:
                st.error(f"Erro de Banco: {str(e)}")
        else:
            st.warning("Preencha todos os campos.")
else:
    # Sidebar com logout
    st.sidebar.title(f"Olá, {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    # Abas
    tab1, tab2 = st.tabs(["Dashboard", "Cadastro Vendas"])

    with tab1:
        st.header("Dashboard")
        try:
            response = supabase.table("vendas").select("*").order("data_venda", desc=True).execute()
            vendas = response.data
            if vendas:
                df = pd.DataFrame(vendas)
                col1, col2, col3 = st.columns(3)
                total_vendas = len(df)
                total_receita = df["total_venda"].sum()
                total_comissao = df["valor_comissao"].sum()
                col1.metric("Total Vendas", total_vendas)
                col2.metric("Receita Total", f"R$ {total_receita:.2f}")
                col3.metric("Comissão Total", f"R$ {total_comissao:.2f}")

                st.subheader("Vendas por Status")
                st.bar_chart(df["status"].value_counts())

                st.subheader("Últimas Vendas")
                st.dataframe(df.head(10))
            else:
                st.info("Nenhuma venda cadastrada ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar dashboard: {str(e)}")

    with tab2:
        st.header("Cadastro de Vendas")
        with st.form("venda_form"):
            col1, col2 = st.columns(2)
            with col1:
                estabelecimento = st.text_input("Estabelecimento")
                data_venda = st.date_input("Data da Venda", value=date.today())
                bairro = st.text_input("Bairro")
                forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Pix", "Cartão Débito", "Cartão Crédito"])
            with col2:
                produto = st.text_input("Produto")
                quantidade = st.number_input("Quantidade", min_value=1, step=1)
                valor_produto = st.number_input("Valor por Produto", min_value=0.01, format="%.2f")

            total_venda = quantidade * valor_produto
            st.info(f"**Total Venda: R$ {total_venda:.2f}**")

            comissao_percentual = st.number_input("Comissão Percentual (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
            valor_comissao = total_venda * (comissao_percentual / 100)
            st.info(f"**Valor Comissão: R$ {valor_comissao:.2f}**")

            status = st.selectbox("Status", ["Pendente", "Concluída", "Cancelada"])

            if st.form_submit_button("Cadastrar Venda"):
                if all([estabelecimento, bairro, produto]):
                    data = {
                        "estabelecimento": estabelecimento,
                        "data_venda": data_venda.isoformat(),
                        "bairro": bairro,
                        "forma_pagamento": forma_pagamento,
                        "produto": produto,
                        "quantidade": float(quantidade),
                        "valor_produto": float(valor_produto),
                        "total_venda": float(total_venda),
                        "comissao_percentual": float(comissao_percentual),
                        "valor_comissao": float(valor_comissao),
                        "status": status
                    }
                    try:
                        supabase.table("vendas").insert(data).execute()
                        st.success("Venda cadastrada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar venda: {str(e)}")
                else:
                    st.error("Preencha todos os campos obrigatórios.")