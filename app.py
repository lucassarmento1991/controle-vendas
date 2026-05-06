import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib
from datetime import date

# Initialize Supabase
@st.cache_resource
def init_supabase():
    try:
        url: str = st.secrets["supabase"]["url"]
        key: str = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Failed to initialize Supabase: {str(e)}")
        st.stop()

supabase: Client = init_supabase()

# Login
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("Login")
    with st.form("login_form"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
    if submitted:
        if not usuario.strip() or not senha:
            st.error("Preencha usuário e senha.")
        else:
            response = supabase.table('usuarios').select('*').ilike('usuario', f"%{usuario.strip()}%").execute()
            if response.data:
                user_data = response.data[0]
                hashed_input = hashlib.sha256(senha.encode()).hexdigest()
                if user_data['password'] == hashed_input:
                    st.session_state.user = user_data
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    if user_data['password'] == 'lucas123':
                        st.warning("Senha em texto puro (lucas123) detectada!")
                        if st.button("Atualizar Senha para Formato Seguro"):
                            hashed_correct = hashlib.sha256('lucas123'.encode()).hexdigest()
                            update_response = supabase.table('usuarios').update({'password': hashed_correct}).eq('id', user_data['id']).execute()
                            if update_response.data:
                                st.success("Senha reparada! Agora faça login com 'lucas123'.")
                            else:
                                st.error("Falha ao atualizar senha.")
                            st.rerun()
                    else:
                        st.error("Senha incorreta.")
            else:
                st.error("Usuário não encontrado.")
else:
    st.title(f"Bem-vindo, {st.session_state.user['usuario']}!")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
    tab1, tab2, tab3 = st.tabs(["Cadastro de Vendas", "Listagem", "Relatórios"])
    with tab1:
        st.subheader("Cadastrar Venda")
        with st.form("venda_form"):
            data_venda = st.date_input("Data da Venda", value=date.today())
            produto = st.text_input("Produto")
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            col1, col2 = st.columns(2)
            with col1:
                form_submitted = st.form_submit_button("Cadastrar Venda")
            with col2:
                if st.form_submit_button("Limpar"):
                    st.rerun()
        if form_submitted:
            if produto.strip():
                insert_response = supabase.table('vendas').insert({
                    "data_venda": data_venda.isoformat(),
                    "produto": produto.strip(),
                    "valor": float(valor),
                    "usuario_id": st.session_state.user['id']
                }).execute()
                if insert_response.data:
                    st.success("Venda cadastrada com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao cadastrar venda.")
            else:
                st.error("Preencha o produto.")
    with tab2:
        st.subheader("Listagem de Vendas")
        vendas_response = supabase.table('vendas').select('*').eq('usuario_id', st.session_state.user['id']).order('data_venda', desc=True).execute()
        if vendas_response.data:
            df = pd.DataFrame(vendas_response.data)
            df['data_venda'] = pd.to_datetime(df['data_venda'])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhuma venda cadastrada.")
    with tab3:
        st.subheader("Relatórios")
        vendas_response = supabase.table('vendas').select('*').eq('usuario_id', st.session_state.user['id']).execute()
        if vendas_response.data:
            df = pd.DataFrame(vendas_response.data)
            df['data_venda'] = pd.to_datetime(df['data_venda'])
            total_vendas = df['valor'].sum()
            st.metric("Total de Vendas", f"R$ {total_vendas:,.2f}")
            df['mes'] = df['data_venda'].dt.to_period('M')
            monthly = df.groupby('mes')['valor'].sum().reset_index()
            monthly['mes'] = monthly['mes'].astype(str)
            fig = px.bar(monthly, x='mes', y='valor', title="Vendas por Mês")
            st.plotly_chart(fig, use_container_width=True)
            by_prod = df.groupby('produto')['valor'].sum().reset_index().sort_values('valor', ascending=False)
            fig2 = px.bar(by_prod.head(10), x='produto', y='valor', title="Top 10 Produtos por Valor")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nenhuma venda para relatórios.")