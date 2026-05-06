import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from supabase import create_client

@st.cache_resource
def get_supabase():
    url = st.secrets['supabase']['url'].strip()
    key = st.secrets['supabase']['key'].strip()
    return create_client(url, key)

@st.cache_data(ttl=300)
def load_vendas():
    supabase = get_supabase()
    return supabase.table('vendas').select('*').order('data_venda', desc=True).execute().data

st.set_page_config(page_title="App de Vendas Lucas", layout="wide")
st.title("📊 App de Vendas Lucas")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.needs_repair = None

if not st.session_state.logged_in:
    st.subheader("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Senha", type="password")
    col1, col2 = st.columns([3, 1])
    if col1.button("Entrar"):
        supabase = get_supabase()
        response = supabase.table('usuarios').select('id, username, password_hash').ilike('username', username).limit(1).execute()
        if response.data:
            user = response.data[0]
            input_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            if user['password_hash'] == input_hash:
                st.session_state.logged_in = True
                st.session_state.username = user['username']
                st.session_state.user_id = user.get('id')
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Senha incorreta!")
                if user['password_hash'] == 'lucas123':
                    st.session_state.needs_repair = user['username']
        else:
            st.error("Usuário não encontrado!")
    if col2.button("🔧 Reparar Senha") and st.session_state.needs_repair:
        supabase = get_supabase()
        correct_hash = hashlib.sha256('lucas123'.encode('utf-8')).hexdigest()
        supabase.table('usuarios').update({'password_hash': correct_hash}).eq('username', st.session_state.needs_repair).execute()
        st.success("Senha reparada! Faça login com 'lucas123'.")
        st.session_state.needs_repair = None
        st.rerun()
else:
    col_logout, _ = st.columns([1, 4])
    with col_logout:
        if st.button("Logout"):
            st.session_state.logged_in = False
            del st.session_state.username
            del st.session_state.user_id
            st.rerun()
    st.info(f"👋 Logado como {st.session_state.username}")

    vendas = load_vendas()
    df_vendas = pd.DataFrame(vendas) if vendas else pd.DataFrame()

    tab1, tab2, tab3 = st.tabs(["Cadastro de Vendas", "Listagem", "Dashboard Plotly"])

    with tab1:
        st.subheader("Nova Venda")
        with st.form("venda_form"):
            col1, col2 = st.columns(2)
            with col1:
                estabelecimento = st.text_input("Estabelecimento")
                data_venda = st.date_input("Data da Venda")
                bairro = st.text_input("Bairro")
                forma_pagamento = st.text_input("Forma de Pagamento")
            with col2:
                produto = st.text_input("Produto")
                quantidade = st.number_input("Quantidade", min_value=1, step=1)
                valor_unitario = st.number_input("Valor Unitário (R$)", min_value=0.01, format="%.2f")

            total = quantidade * valor_unitario
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                percentual_comissao = st.number_input("Comissão (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
                comissao_percentual = percentual_comissao / 100
            col_t2.markdown(f"**Total: R$ {total:.2f}**")
            col_t3.markdown(f"**Comissão: R$ {total * comissao_percentual:.2f}**")

            submitted = st.form_submit_button("Cadastrar Venda", use_container_width=True)
            if submitted:
                supabase = get_supabase()
                data_insert = {
                    "estabelecimento": estabelecimento,
                    "data_venda": data_venda.isoformat(),
                    "bairro": bairro,
                    "forma_pagamento": forma_pagamento,
                    "produto": produto,
                    "quantidade": float(quantidade),
                    "valor_unitario": float(valor_unitario),
                    "total": float(total),
                    "comissao_percentual": float(comissao_percentual),
                    "valor_comissao": float(total * comissao_percentual)
                }
                supabase.table('vendas').insert(data_insert).execute()
                st.success("Venda cadastrada com sucesso!")
                st.cache_data.clear()
                st.rerun()

    with tab2:
        st.subheader("Listagem de Vendas")
        if df_vendas.empty:
            st.info("Nenhuma venda cadastrada.")
        else:
            st.dataframe(df_vendas.style.format({
                'total': '{:.2f}',
                'valor_unitario': '{:.2f}',
                'valor_comissao': '{:.2f}',
                'comissao_percentual': '{:.2%}',
                'quantidade': '{:.0f}'
            }).format(na_rep='-'))

    with tab3:
        st.subheader("Dashboard")
        if df_vendas.empty:
            st.info("Nenhuma venda para exibir.")
        else:
            df_plot = df_vendas.copy()
            df_plot['data_venda'] = pd.to_datetime(df_plot['data_venda'])
            df_plot['data_venda'] = df_plot['data_venda'].dt.date

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Faturamento Total", f"R$ {df_plot['total'].sum():.2f}")
            with col2:
                st.metric("Comissões Acumuladas", f"R$ {df_plot['valor_comissao'].sum():.2f}")

            daily_sales = df_plot.groupby('data_venda')['total'].sum().reset_index()
            fig = px.bar(daily_sales, x='data_venda', y='total', title="Faturamento por Dia",
                         labels={'total': 'Faturamento (R$)', 'data_venda': 'Data'})
            st.plotly_chart(fig, use_container_width=True)
