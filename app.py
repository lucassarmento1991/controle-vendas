import streamlit as st
import supabase
from supabase import create_client
import hashlib
from datetime import date
import pandas as pd

st.set_page_config(page_title="Sistema de Vendas", layout="wide")

@st.cache_resource
def init_supabase():
    url = st.secrets['supabase']['url'].strip()
    key = st.secrets['supabase']['key'].strip()
    return create_client(url, key)

supabase = init_supabase()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if not st.session_state.logged_in:
    st.title("Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if username and password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            result = (supabase.table('users')
                      .select('id')
                      .eq('username', username)
                      .eq('password_hash', password_hash)
                      .execute())
            if result.data:
                st.session_state.logged_in = True
                st.session_state.user_id = result.data[0]['id']
                st.rerun()
            else:
                st.error("Credenciais inválidas")
        else:
            st.error("Preencha todos os campos")
else:
    st.title("Sistema de Vendas")
    
    def logout():
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.rerun()
    
    st.sidebar.button("Logout", on_click=logout)
    
    tab1, tab2 = st.tabs(["Dashboard", "Cadastro Vendas"])
    
    with tab1:
        st.header("Dashboard")
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data Início", value=date.today().replace(day=1))
        with col2:
            data_fim = st.date_input("Data Fim", value=date.today())
        
        response = (supabase.table('vendas')
                    .select('*')
                    .gte('data_venda', data_inicio.isoformat())
                    .lte('data_venda', data_fim.isoformat())
                    .eq('status', 'ativa')
                    .execute())
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            total_faturamento = df['total_venda'].sum()
            total_vendas = len(df)
            total_comissao = df['valor_comissao'].sum()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Faturamento", f"R$ {total_faturamento:,.2f}")
            col2.metric("Nº Vendas", total_vendas)
            col3.metric("Comissão Total", f"R$ {total_comissao:,.2f}")
            
            st.subheader("Vendas por Bairro")
            bairro_vendas = df.groupby('bairro')['total_venda'].sum().sort_values(ascending=False)
            st.bar_chart(bairro_vendas)
        else:
            st.info("Nenhuma venda encontrada no período.")
    
    with tab2:
        st.header("Nova Venda")
        estabelecimento = st.text_input("Estabelecimento")
        data_venda = st.date_input("Data da Venda", value=date.today())
        bairro = st.text_input("Bairro")
        forma_pagamento = st.selectbox("Forma de Pagamento", ["Pix", "Cartão", "Dinheiro", "Boleto"])
        produto = st.text_input("Produto")
        quantidade = st.number_input("Quantidade", min_value=0.0, format="%.2f")
        valor_produto = st.number_input("Valor Unitário", min_value=0.0, format="%.2f")
        comissao_percentual = st.number_input("Comissão %", min_value=0.0, max_value=100.0, value=10.0, format="%.2f")
        
        total_venda = quantidade * valor_produto
        valor_comissao = total_venda * (comissao_percentual / 100)
        
        col1, col2 = st.columns(2)
        col1.metric("Total Venda", f"R$ {total_venda:.2f}")
        col2.metric("Valor Comissão", f"R$ {valor_comissao:.2f}")
        
        if st.button("Salvar Venda"):
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
                "status": 'ativa'
            }
            result = supabase.table('vendas').insert(data).execute()
            if result.data:
                st.success("Venda cadastrada com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao cadastrar venda.")
