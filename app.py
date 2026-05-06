import streamlit as st
import supabase
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import bcrypt

@st.cache_resource
def init_supabase():
    try:
        supabase_secrets = st.secrets['supabase']
        url = supabase_secrets.get('url', '').strip()
        key = supabase_secrets.get('anon_key', '').strip()
    except (KeyError, AttributeError):
        url = st.secrets.get('SUPABASE_URL', '').strip()
        key = st.secrets.get('SUPABASE_ANON_KEY', '').strip()
    if not url or not key:
        st.error("Supabase secrets not configured!")
        st.stop()
    return create_client(url, key)

supabase: Client = init_supabase()

st.set_page_config(page_title="App Vendas Lucas", page_icon="📊", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

def check_login(email: str, password: str):
    response = supabase.table('usuarios').select('*').eq('email', email).execute()
    data = response.data
    if data and bcrypt.checkpw(password.encode('utf-8'), data[0]['password_hash'].encode('utf-8')):
        return True, data[0]
    return False, None

def fetch_vendas():
    response = supabase.table('vendas').select('*').execute()
    df = pd.DataFrame(response.data)
    numeric_cols = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')
    if 'data_venda' in df.columns:
        df['data_venda'] = pd.to_datetime(df['data_venda'], errors='coerce')
    if not df.empty:
        df = df.sort_values('data_venda', ascending=False).reset_index(drop=True)
    return df

def add_venda_form():
    with st.form("add_venda"):
        col1, col2 = st.columns(2)
        with col1:
            estabelecimento = st.text_input("Estabelecimento")
            data_venda = st.date_input("Data da Venda", value=date.today())
            bairro = st.text_input("Bairro")
        with col2:
            forma_pagamento = st.selectbox("Forma de Pagamento", ["Pix", "Cartao", "Dinheiro"])
            produto = st.text_input("Produto")
            quantidade = st.number_input("Quantidade", min_value=0.0, step=1.0)
        col3, col4 = st.columns(2)
        with col3:
            valor_produto = st.number_input("Valor Unitario", min_value=0.0)
            total_venda = quantidade * valor_produto
            st.number_input("Total Venda", value=total_venda, disabled=True, label_visibility="collapsed")
        with col4:
            comissao_percentual = st.number_input("% Comissao", min_value=0.0, max_value=100.0) / 100
            valor_comissao = total_venda * comissao_percentual
            st.number_input("Valor Comissao", value=valor_comissao, disabled=True, label_visibility="collapsed")
        status = st.selectbox("Status", ["Pendente", "Pago", "Cancelado"])
        submitted = st.form_submit_button("Adicionar Venda")
        if submitted and estabelecimento and bairro and produto:
            data = {
                'estabelecimento': estabelecimento,
                'data_venda': data_venda.isoformat(),
                'bairro': bairro,
                'forma_pagamento': forma_pagamento,
                'produto': produto,
                'quantidade': float(quantidade),
                'valor_produto': float(valor_produto),
                'total_venda': float(total_venda),
                'comissao_percentual': float(comissao_percentual),
                'valor_comissao': float(valor_comissao),
                'status': status
            }
            supabase.table('vendas').insert(data).execute()
            st.success("Venda adicionada com sucesso!")
            st.rerun()

# Sidebar
if st.session_state.logged_in:
    st.sidebar.title(f"Olá, {st.session_state.user.get('nome', st.session_state.user.get('email', 'Usuario'))}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

st.title("📊 App de Vendas - Lucas")

# Tabs
tabs = st.tabs(["Login", "Vendas", "Relatórios", "Edição em Massa"])

with tabs[0]:
    st.header("Login")
    email = st.text_input("Email")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        success, user = check_login(email, password)
        if success:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.success(f"Login realizado! Bem-vindo, {user.get('nome', email)}")
            st.rerun()
        else:
            st.error("Email ou senha incorretos.")

with tabs[1]:
    if st.session_state.logged_in:
        st.header("Vendas")
        df = fetch_vendas()
        st.dataframe(df, use_container_width=True)
        st.subheader("Adicionar Nova Venda")
        add_venda_form()
    else:
        st.warning("🔒 Faça login para acessar.")

with tabs[2]:
    if st.session_state.logged_in:
        st.header("Relatórios")
        df = fetch_vendas()
        if df.empty:
            st.info("Nenhuma venda encontrada.")
        else:
            col_filt1, col_filt2, col_filt3, col_filt4 = st.columns(4)
            with col_filt1:
                data_inicio = st.date_input("Data Início", value=date.today() - timedelta(days=30))
            with col_filt2:
                data_fim = st.date_input("Data Fim", value=date.today())
            with col_filt3:
                bairros = st.multiselect("Bairros", options=sorted(df['bairro'].dropna().unique()))
            with col_filt4:
                estabelecimentos = st.multiselect("Estabelecimentos", options=sorted(df['estabelecimento'].dropna().unique()))

            filtered_df = df[(df['data_venda'] >= pd.to_datetime(data_inicio)) & (df['data_venda'] <= pd.to_datetime(data_fim) + timedelta(days=1))].copy()
            if bairros:
                filtered_df = filtered_df[filtered_df['bairro'].isin(bairros)]
            if estabelecimentos:
                filtered_df = filtered_df[filtered_df['estabelecimento'].isin(estabelecimentos)]

            col1, col2 = st.columns(2)
            with col1:
                if not filtered_df.empty:
                    vendas_por_estab = filtered_df.groupby('estabelecimento')['total_venda'].sum().reset_index()
                    fig1 = px.bar(vendas_por_estab, x='estabelecimento', y='total_venda', title='Total Vendas por Estabelecimento')
                    st.plotly_chart(fig1, use_container_width=True)
            with col2:
                if not filtered_df.empty:
                    comissao_por_estab = filtered_df.groupby('estabelecimento')['valor_comissao'].sum().reset_index()
                    fig2 = px.bar(comissao_por_estab, x='estabelecimento', y='valor_comissao', title='Total Comissão por Estabelecimento')
                    st.plotly_chart(fig2, use_container_width=True)

            col3, col4 = st.columns(2)
            with col3:
                if not filtered_df.empty:
                    vendas_tempo = filtered_df.groupby(filtered_df['data_venda'].dt.date)['total_venda'].sum().reset_index(name='total_venda')
                    vendas_tempo.columns = ['data_venda', 'total_venda']
                    fig3 = px.line(vendas_tempo, x='data_venda', y='total_venda', title='Vendas ao Longo do Tempo')
                    st.plotly_chart(fig3, use_container_width=True)
            with col4:
                if not filtered_df.empty:
                    fig4 = px.pie(filtered_df, names='forma_pagamento', values='total_venda', title='Distribuição por Forma de Pagamento')
                    st.plotly_chart(fig4, use_container_width=True)

            st.metric("Total Vendas", f"R$ {filtered_df['total_venda'].sum():.2f}")
            st.metric("Total Comissão", f"R$ {filtered_df['valor_comissao'].sum():.2f}")
            st.dataframe(filtered_df, use_container_width=True)
    else:
        st.warning("🔒 Faça login para acessar.")

with tabs[3]:
    if st.session_state.logged_in:
        st.header("Edição em Massa")
        df = fetch_vendas()
        if df.empty:
            st.info("Nenhuma venda para editar.")
        else:
            column_config = {
                "id": st.column_config.TextColumn("ID", disabled=True),
                "data_venda": st.column_config.DateColumn("Data Venda"),
                "quantidade": st.column_config.NumberColumn("Quantidade", format="%.2f"),
                "valor_produto": st.column_config.NumberColumn("Valor Produto", format="%.2f", prefix="R$"),
                "total_venda": st.column_config.NumberColumn("Total Venda", format="%.2f", prefix="R$"),
                "comissao_percentual": st.column_config.NumberColumn("% Comissão", format="%.2f", suffix="%"),
                "valor_comissao": st.column_config.NumberColumn("Valor Comissão", format="%.2f", prefix="R$"),
            }
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config=column_config,
                use_container_width=True,
                hide_index=False
            )
            if st.button("Salvar Alterações"):
                new_ids = set(edited_df['id'].dropna().astype(str).tolist())
                old_ids = set(df['id'].astype(str).tolist())
                to_delete = old_ids - new_ids
                for id_ in to_delete:
                    supabase.table('vendas').delete().eq('id', id_).execute()
                for _, row in edited_df.iterrows():
                    row_dict = row.to_dict()
                    id_val = row_dict.pop('id', None)
                    if pd.isna(id_val):
                        # Insert new
                        supabase.table('vendas').insert(row_dict).execute()
                    else:
                        # Update existing
                        supabase.table('vendas').update(row_dict).eq('id', str(id_val)).execute()
                st.success("Alterações salvas!")
                st.rerun()
    else:
        st.warning("🔒 Faça login para acessar.")