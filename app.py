import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib
from datetime import date

st.set_page_config(page_title="Sistema de Vendas Lucas", layout="wide")

# Custom CSS for professional layout
st.markdown("""
<style>
    [data-testid="stSidebar"] > div:first-child {background-color: #f8f9fa;}
    .main .block-container {padding-top: 2rem; max-width: none;}
    .stTabs [data-baseweb="tab-list"] {gap: 10px;}
    .stTabs [data-baseweb="tab"] {font-weight: bold;}
    .metric-container {background-color: #e9ecef; padding: 1rem; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"].strip()
        key = st.secrets["supabase"]["key"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao inicializar Supabase: {str(e)}")
        st.stop()

supabase: Client = init_supabase()

# Session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login no Sistema")
    st.markdown("---")
    with st.form("login_form"):
        username = (st.text_input("Username", help="Seu nome de usuário")).strip()
        password = st.text_input("Senha", type="password", help="Sua senha")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_btn = st.form_submit_button("Entrar", use_container_width=True)
        if login_btn:
            if username and password:
                try:
                    hashed_pw = hashlib.sha256(password.encode('utf-8')).hexdigest()
                    response = supabase.table('usuarios').select('id').eq('username', username).eq('password_hash', hashed_pw).execute()
                    if len(response.data) > 0:
                        st.session_state.logged_in = True
                        st.success("✅ Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ Credenciais inválidas. Verifique username e senha.")
                except Exception as e:
                    st.error(f"❌ Erro no login: {str(e)}")
            else:
                st.error("❌ Preencha todos os campos.")
else:
    # Sidebar
    st.sidebar.title("👤 Usuário Logado")
    st.sidebar.success("Logado")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📝 Cadastro de Vendas", "📋 Listagem & Cancelamento", "📊 Relatórios"])

    with tab1:
        st.header("Nova Venda")
        st.markdown("---")
        with st.form("venda_form"):
            col1, col2 = st.columns(2)
            with col1:
                estabelecimento = (st.text_input("Estabelecimento")).strip()
                data_venda = st.date_input("Data da Venda", value=date.today())
                bairro = (st.text_input("Bairro")).strip()
                forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Pix", "Cartão", "Boleto"])
            with col2:
                produto = (st.text_input("Produto")).strip()
                quantidade = st.number_input("Quantidade", min_value=1, step=1, format="%d")
                valor_produto = st.number_input("Valor Unitário (R$)", min_value=0.01, step=0.01, format="%.2f")
                comissao_percentual = st.number_input("Comissão (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.1, format="%.1f")
            
            total_venda = quantidade * valor_produto
            valor_comissao = total_venda * (comissao_percentual / 100)
            
            col_t1, col_t2 = st.columns(2)
            col_t1.metric("Total Venda", f"R$ {total_venda:.2f}")
            col_t2.metric("Valor Comissão", f"R$ {valor_comissao:.2f}")
            
            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                submit_btn = st.form_submit_button("💾 Cadastrar Venda", use_container_width=True)
            
            if submit_btn:
                if all([estabelecimento, bairro, produto]):
                    try:
                        data_insert = {
                            "estabelecimento": estabelecimento,
                            "data_venda": data_venda.isoformat(),
                            "bairro": bairro,
                            "forma_pagamento": forma_pagamento,
                            "produto": produto,
                            "quantidade": int(quantidade),
                            "valor_produto": float(valor_produto),
                            "total_venda": float(total_venda),
                            "comissao_percentual": float(comissao_percentual),
                            "valor_comissao": float(valor_comissao),
                            "status": "ativa"
                        }
                        response = supabase.table('vendas').insert(data_insert).execute()
                        if response.data:
                            st.success("✅ Venda cadastrada com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Falha ao cadastrar venda.")
                    except Exception as e:
                        st.error(f"❌ Erro ao cadastrar venda: {str(e)}")
                else:
                    st.error("❌ Preencha todos os campos obrigatórios (estabelecimento, bairro, produto).")

    with tab2:
        st.header("Vendas Ativas")
        st.markdown("---")
        try:
            response = supabase.table('vendas').select('*').eq('status', 'ativa').order('data_venda', desc=True).execute()
            df_vendas = pd.DataFrame(response.data)
            if not df_vendas.empty:
                st.dataframe(df_vendas, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.subheader("Cancelar Venda")
                cancel_id = st.number_input("ID da Venda", min_value=1, step=1, help="Digite o ID da venda acima")
                col_c1, col_c2 = st.columns([3,1])
                with col_c2:
                    if st.button("🗑️ Cancelar", use_container_width=True):
                        try:
                            update_response = supabase.table('vendas').update({'status': 'cancelada'}).eq('id', int(cancel_id)).eq('status', 'ativa').execute()
                            if update_response.data:
                                st.success("✅ Venda cancelada com sucesso!")
                                st.rerun()
                            else:
                                st.warning("⚠️ Venda não encontrada ou já cancelada.")
                        except Exception as e:
                            st.error(f"❌ Erro ao cancelar: {str(e)}")
            else:
                st.info("📭 Nenhuma venda ativa no momento.")
        except Exception as e:
            st.error(f"❌ Erro ao carregar vendas: {str(e)}")

    with tab3:
        st.header("Relatórios e Dashboards")
        st.markdown("---")
        try:
            response = supabase.table('vendas').select('*').eq('status', 'ativa').execute()
            df_rel = pd.DataFrame(response.data)
            if df_rel.empty:
                st.info("📭 Nenhuma venda ativa para relatórios.")
            else:
                df_rel['data_venda'] = pd.to_datetime(df_rel['data_venda'])
                df_rel['data_venda_group'] = df_rel['data_venda'].dt.date
                
                # Métricas
                col_m1, col_m2, col_m3 = st.columns(3)
                total_vendas = len(df_rel)
                faturamento = df_rel['total_venda'].sum()
                comissao_total = df_rel['valor_comissao'].sum()
                
                with col_m1:
                    st.metric("Total de Vendas", total_vendas)
                with col_m2:
                    st.metric("Faturamento Total", f"R$ {faturamento:.2f}")
                with col_m3:
                    st.metric("Comissão Total", f"R$ {comissao_total:.2f}")
                
                # Gráficos
                st.markdown("---")
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    vendas_bairro = df_rel.groupby('bairro')['total_venda'].sum().reset_index()
                    fig_bairro = px.bar(vendas_bairro, x='bairro', y='total_venda', title="Vendas por Bairro")
                    st.plotly_chart(fig_bairro, use_container_width=True)
                with col_g2:
                    vendas_produto = df_rel.groupby('produto')['total_venda'].sum().reset_index().head(10)  # Top 10
                    fig_produto = px.bar(vendas_produto, x='produto', y='total_venda', title="Vendas por Produto")
                    st.plotly_chart(fig_produto, use_container_width=True)
                
                col_g3, col_g4 = st.columns(2)
                with col_g3:
                    fig_forma = px.pie(df_rel, names='forma_pagamento', values='total_venda', title="Forma de Pagamento")
                    st.plotly_chart(fig_forma, use_container_width=True)
                with col_g4:
                    vendas_temporal = df_rel.groupby('data_venda_group')['total_venda'].sum().reset_index()
                    fig_temporal = px.line(vendas_temporal, x='data_venda_group', y='total_venda', title="Evolução Temporal")
                    st.plotly_chart(fig_temporal, use_container_width=True)
        except Exception as e:
            st.error(f"❌ Erro ao gerar relatórios: {str(e)}")
