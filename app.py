import streamlit as st
import pandas as pd
from supabase import create_client, Client
import hashlib
from datetime import date
import plotly.express as px

st.set_page_config(page_title="App Vendas Lucas", layout="wide")

# Inicialização segura do Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets['supabase']['url'].strip()
    key = st.secrets['supabase']['key'].strip()
    return create_client(url, key)

supabase: Client = init_supabase()

# Estado da sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Interface de Login
if not st.session_state.logged_in:
    st.title("🔑 Login Administrativo")
    with st.form("login_form"):
        username_input = st.text_input("Usuário").strip()
        password_input = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            try:
                # CORREÇÃO: Usando a tabela 'usuarios' e coluna 'username' conforme seu banco
                result = supabase.table('usuarios').select('password_hash').eq('username', username_input).execute()
                
                if result.data:
                    stored_hash = result.data[0]['password_hash']
                    if hash_password(password_input) == stored_hash:
                        st.session_state.logged_in = True
                        st.session_state.username = username_input
                        st.success("Acesso autorizado!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta!")
                else:
                    st.error("Usuário não encontrado no banco de dados.")
            except Exception as e:
                st.error(f"Erro de Banco (Tabela/Coluna): {str(e)}")
    st.stop()

# Dashboard Principal
st.sidebar.title(f"👤 {st.session_state.username}")
if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

tab1, tab2, tab3 = st.tabs(["🛒 Nova Venda", "✏️ Editar Registros", "📊 Relatórios"])

with tab1:
    st.header("Cadastrar Venda")
    with st.form("venda_form"):
        col1, col2 = st.columns(2)
        with col1:
            estabelecimento = st.text_input("Estabelecimento")
            data_venda = st.date_input("Data da Venda", value=date.today())
            bairro = st.text_input("Bairro")
            forma_pagamento = st.selectbox("Pagamento", ["Pix", "Cartão", "Dinheiro", "Boleto"])
        with col2:
            produto = st.text_input("Produto")
            quantidade = st.number_input("Quantidade", min_value=1.0, step=1.0)
            valor_produto = st.number_input("Valor Unitário", min_value=0.01, format="%.2f")
            comissao_percentual = st.number_input("Comissão (%)", value=10.0)

        total_venda = quantidade * valor_produto
        valor_comissao = total_venda * (comissao_percentual / 100)

        if st.form_submit_button("Salvar Venda", use_container_width=True):
            data_insert = {
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
                "status": "ativa"
            }
            try:
                supabase.table('vendas').insert(data_insert).execute()
                st.success("Venda salva com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar: {str(e)}")

with tab2:
    st.header("Edição de Vendas")
    try:
        response = supabase.table('vendas').select("*").execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor_vendas")
            if st.button("Salvar Alterações"):
                for index, row in edited_df.iterrows():
                    # Lógica de update simplificada por ID
                    id_venda = row.get('id')
                    if id_venda:
                        data_update = row.to_dict()
                        data_update.pop('id', None) # Não altera o ID
                        supabase.table('vendas').update(data_update).eq('id', id_venda).execute()
                st.success("Banco de dados atualizado!")
                st.rerun()
    except Exception as e:
        st.error(f"Erro ao carregar edição: {str(e)}")

with tab3:
    st.header("Filtros e Gráficos")
    # Filtros simplificados
    try:
        res = supabase.table('vendas').select("*").execute()
        df_rel = pd.DataFrame(res.data)
        if not df_rel.empty:
            df_rel['data_venda'] = pd.to_datetime(df_rel['data_venda'])
            
            # Sidebar Filtros
            st.subheader("Filtrar Resultados")
            lista_bairros = ["Todos"] + list(df_rel['bairro'].unique())
            bairro_sel = st.selectbox("Selecione o Bairro", lista_bairros)
            
            df_filtrado = df_rel if bairro_sel == "Todos" else df_rel[df_rel['bairro'] == bairro_sel]
            
            st.metric("Faturamento Filtrado", f"R$ {df_filtrado['total_venda'].sum():.2f}")
            fig = px.pie(df_filtrado, values='total_venda', names='produto', title="Vendas por Produto")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para relatório.")
    except Exception as e:
        st.error(f"Erro no relatório: {str(e)}")