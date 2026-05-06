import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib
from datetime import date

# Configuração de Página
st.set_page_config(page_title="Sistema de Vendas Lucas", layout="wide")

# Inicialização segura do cliente Supabase
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"].strip()
        key = st.secrets["supabase"]["key"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro de conexão: {str(e)}")
        st.stop()

supabase: Client = init_supabase()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Controle de Sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login Administrativo")
    with st.form("login_form"):
        user_input = st.text_input("Usuário").strip()
        pass_input = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            try:
                hashed_pw = hash_password(pass_input)
                # Busca na tabela 'usuarios'
                response = supabase.table('usuarios').select('*').eq('username', user_input).execute()
                if response.data and response.data[0]['password_hash'] == hashed_pw:
                    st.session_state.logged_in = True
                    st.success("Acesso autorizado!")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
            except Exception as e:
                st.error(f"Erro de login: {str(e)}")
    st.stop()

# Layout Principal
st.sidebar.success("Conectado")
if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

tab1, tab2 = st.tabs(["🛒 Cadastro de Vendas", "📊 Dashboard"])

with tab1:
    st.header("Nova Venda")
    with st.form("venda_form"):
        col1, col2 = st.columns(2)
        with col1:
            estabelecimento = st.text_input("Estabelecimento")
            data_venda = st.date_input("Data da Venda", value=date.today())
            bairro = st.text_input("Bairro")
            forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Pix", "Cartão", "Boleto"])
        with col2:
            produto = st.text_input("Produto")
            quantidade = st.number_input("Quantidade", min_value=1, step=1)
            valor_unitario = st.number_input("Valor Unitário (R$)", min_value=0.01, format="%.2f")
            comissao_perc = st.number_input("Comissão (%)", min_value=0.0, max_value=100.0, value=10.0)

        # Cálculos automáticos
        total_calculado = quantidade * valor_unitario
        valor_comissao = total_calculado * (comissao_perc / 100)

        st.markdown(f"**Total da Venda:** R$ {total_calculado:.2f}")

        if st.form_submit_button("💾 Salvar Venda", use_container_width=True):
            data_insert = {
                "estabelecimento": estabelecimento,
                "data_venda": data_venda.isoformat(),
                "bairro": bairro,
                "forma_pagamento": forma_pagamento,
                "produto": produto,
                "quantidade": int(quantidade),
                "valor_unitario": float(valor_unitario),
                "total": float(total_calculado),
                "comissao_percentual": float(comissao_perc),
                "valor_comissao": float(valor_comissao)
            }
            try:
                supabase.table('vendas').insert(data_insert).execute()
                st.success("✅ Venda registrada no Supabase!")
            except Exception as e:
                st.error(f"Erro ao salvar: {str(e)}")

with tab2:
    st.header("Análise de Resultados")
    try:
        vendas = supabase.table('vendas').select('*').execute()
        if vendas.data:
            df = pd.DataFrame(vendas.data)
            st.metric("Faturamento Total", f"R$ {df['total'].sum():.2f}")
            fig = px.bar(df, x='produto', y='total', title="Vendas por Produto", color="bairro")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma venda encontrada.")
    except Exception as e:
        st.error(f"Erro ao carregar gráficos: {str(e)}")