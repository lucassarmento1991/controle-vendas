import streamlit as st
import supabase
from supabase import create_client, Client
import hashlib
import pandas as pd
import plotly.express as px
from datetime import date

# Configuração de login SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

CORRECT_HASH = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"  # SHA-256 de 'lucas'

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if hash_password(password) == CORRECT_HASH:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()

# Inicialização do cliente Supabase
url = st.secrets['supabase']['url'].strip()
key = st.secrets['supabase']['key'].strip()
supabase: Client = create_client(url, key)

st.title("App de Vendas - Lucas")

# Tabs
tab1, tab2 = st.tabs(["Cadastro de Vendas", "Gráficos"])

with tab1:
    st.header("Cadastro de Vendas")

    # Bloco de Debug de Colunas na sidebar
    with st.sidebar:
        st.subheader("Debug de Colunas")
        if st.button("Ver Colunas da Tabela 'vendas'"):
            try:
                response = supabase.table('vendas').select('*').limit(1).execute()
                if response.data:
                    cols = list(response.data[0].keys())
                    st.write("Colunas existentes:")
                    st.json(cols)
                else:
                    st.warning("Tabela 'vendas' está vazia.")
            except Exception as e:
                st.error(f"Erro ao buscar colunas: {str(e)}")

    # Formulário de cadastro
    col1, col2 = st.columns(2)

    with col1:
        estabelecimento = st.text_input("Estabelecimento")
        data_venda = st.date_input("Data da Venda", value=date.today())
        bairro = st.text_input("Bairro")
        forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Pix", "Cartão", "Boleto"])

    with col2:
        produto = st.text_input("Produto")
        quantidade = st.number_input("Quantidade", min_value=1, step=1)
        valor_unitario = st.number_input("Valor Unitário (R$)", min_value=0.01, step=0.01, format="%.2f")
        comissao_percentual = st.number_input("Comissão Percentual (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.1, format="%.1f")

    # Cálculos
g    total = quantidade * valor_unitario
    valor_comissao = total * (comissao_percentual / 100)

    col3, col4 = st.columns(2)
    col3.metric("Total", f"R$ {total:.2f}")
    col4.metric("Valor da Comissão", f"R$ {valor_comissao:.2f}")

    if st.button("Inserir Venda", type="primary"):
        data_insert = {
            'estabelecimento': estabelecimento,
            'data_venda': data_venda.isoformat(),
            'bairro': bairro,
            'forma_pagamento': forma_pagamento,
            'produto': produto,
            'quantidade': int(quantidade),
            'valor_unitario': float(valor_unitario),
            'total': float(total),
            'comissao_percentual': float(comissao_percentual),
            'valor_comissao': float(valor_comissao)
        }
        try:
            response = supabase.table('vendas').insert(data_insert).execute()
            st.success("Venda inserida com sucesso!")
            st.balloons()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao inserir venda (PostgREST): {str(e)}")
            st.subheader("Dados enviados para debug:")
            st.json(data_insert)

with tab2:
    st.header("Dashboard - Gráficos")

    try:
        response = supabase.table('vendas').select('*').execute()
        df = pd.DataFrame(response.data)

        if not df.empty:
            # Gráfico 1: Total de Vendas por Data
            df['data_venda'] = pd.to_datetime(df['data_venda'])
            vendas_por_data = df.groupby('data_venda')['total'].sum().reset_index()
            fig1 = px.bar(vendas_por_data, x='data_venda', y='total', title='Total de Vendas por Data',
                          labels={'total': 'Total (R$)', 'data_venda': 'Data'})
            st.plotly_chart(fig1, use_container_width=True)

            # Gráfico 2: Valor da Comissão por Produto
            comissao_por_produto = df.groupby('produto')['valor_comissao'].sum().reset_index()
            fig2 = px.pie(comissao_por_produto, values='valor_comissao', names='produto',
                          title='Distribuição de Comissões por Produto')
            st.plotly_chart(fig2, use_container_width=True)

            # Gráfico 3: Top Estabelecimentos por Total
            top_estabelecimentos = df.groupby('estabelecimento')['total'].sum().reset_index().nlargest(5, 'total')
            fig3 = px.bar(top_estabelecimentos, x='total', y='estabelecimento', orientation='h',
                          title='Top 5 Estabelecimentos por Total de Vendas',
                          labels={'total': 'Total (R$)', 'estabelecimento': 'Estabelecimento'})
            st.plotly_chart(fig3, use_container_width=True)

            # Estatísticas
            st.metric("Total Geral de Vendas", f"R$ {df['total'].sum():.2f}")
            st.metric("Total de Comissões", f"R$ {df['valor_comissao'].sum():.2f}")
            st.metric("Número de Vendas", len(df))
        else:
            st.info("\u26a1 Nenhuma venda cadastrada ainda. Cadastre vendas na aba anterior!")
    except Exception as e:
        st.error(f"Erro ao carregar dados para gráficos: {str(e)}")

# Rodapé
st.sidebar.markdown("---")
st.sidebar.markdown("App ajustado para correção de APIError no Supabase.")