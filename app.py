import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib

@st.cache_resource
def load_supabase():
    try:
        url = st.secrets["SUPABASE_URL"].strip()
        key = st.secrets["SUPABASE_KEY"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao inicializar Supabase: {str(e)}")
        st.stop()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_data(sb: Client) -> pd.DataFrame:
    response = sb.table('vendas').select('*').order('data_venda', desc=True).execute()
    data = response.data
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if 'id' in df.columns:
        df['id'] = df['id'].astype('Int64')
    df['data_venda'] = pd.to_datetime(df['data_venda'], errors='coerce')
    num_cols = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].astype('float64')
    return df

st.set_page_config(page_title="Sistema de Controle de Vendas V3.2", layout="wide")

st.title("🛒 Sistema de Controle de Vendas V3.2")
st.caption("Remoção de Dependências Externas e Estabilidade (usando hashlib SHA-256)")

supabase: Client = load_supabase()

if 'user' not in st.session_state:
    st.header("🔐 Login")
    col1, col2 = st.columns(2)
    with col1:
        email = st.text_input("Email", key="login_email")
    with col2:
        password = st.text_input("Senha", type="password", key="login_password")
    if st.button("Entrar", type="primary"):
        if email and password:
            response = supabase.table('usuarios').select("id, email, password_hash").eq("email", email).execute()
            if response.data and hash_password(password) == response.data[0].get("password_hash"):
                st.session_state.user = {"id": response.data[0]["id"], "email": response.data[0]["email"]}
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Email ou senha incorretos.")
        else:
            st.warning("Preencha email e senha.")
else:
    st.sidebar.success(f"👤 Logado como: {st.session_state.user['email']}")
    if st.sidebar.button("Sair"):
        del st.session_state.user
        st.rerun()

    tab1, tab2 = st.tabs(["📝 Edição", "📊 Relatórios"])

    with tab1:
        st.header("Gerenciar Vendas")
        if 'data_viewed' not in st.session_state or st.session_state.data_viewed is None:
            st.session_state.data_viewed = get_data(supabase)
        df_original = st.session_state.data_viewed

        # Opções para selectbox
        estabs = sorted(df_original['estabelecimento'].dropna().unique().tolist()) if not df_original.empty else []
        bairros = sorted(df_original['bairro'].dropna().unique().tolist()) if not df_original.empty else []
        formas = sorted(df_original['forma_pagamento'].dropna().unique().tolist()) if not df_original.empty else []
        produtos = sorted(df_original['produto'].dropna().unique().tolist()) if not df_original.empty else []
        statuses = ["Pendente", "Pago", "Cancelado"]

        column_config = {
            "id": st.column_config.NumberColumn("ID", disabled=True, required=False),
            "data_venda": st.column_config.DateColumn("Data da Venda", required=True),
            "estabelecimento": st.column_config.SelectboxColumn("Estabelecimento", options=estabs, required=True),
            "bairro": st.column_config.SelectboxColumn("Bairro", options=bairros, required=True),
            "forma_pagamento": st.column_config.SelectboxColumn("Forma Pagamento", options=formas, required=True),
            "produto": st.column_config.SelectboxColumn("Produto", options=produtos, required=True),
            "quantidade": st.column_config.NumberColumn("Quantidade", min_value=1, step=1, format="%.0f"),
            "valor_produto": st.column_config.NumberColumn("Valor Produto", min_value=0.01, format="%.2f"),
            "total_venda": st.column_config.NumberColumn("Total Venda", min_value=0.01, format="%.2f"),
            "comissao_percentual": st.column_config.NumberColumn("Comissão %", min_value=0.0, max_value=100.0, format="%.2f"),
            "valor_comissao": st.column_config.NumberColumn("Valor Comissão", min_value=0.0, format="%.2f"),
            "status": st.column_config.SelectboxColumn("Status", options=statuses),
        }

        edited_df = st.data_editor(
            df_original,
            column_config=column_config,
            use_container_width=True,
            hide_index=False,
            num_rows="dynamic"
        )

        if st.button("💾 Salvar Alterações", type="primary"):
            # Adicionados
            added_rows = edited_df[pd.isna(edited_df['id'])].drop(columns=['id']).to_dict(orient='records')
            for row in added_rows:
                if pd.isna(row.get('data_venda')):
                    continue
                row['data_venda'] = row['data_venda'].isoformat()
                if pd.notna(row.get('quantidade')):
                    row['quantidade'] = int(row['quantidade'])
                supabase.table('vendas').insert(row).execute()

            # Deletados
            edited_ids = edited_df['id'].dropna().unique().tolist()
            deleted_ids = df_original[~df_original['id'].isin(edited_ids)]['id'].tolist()
            for id_val in deleted_ids:
                supabase.table('vendas').delete().eq('id', id_val).execute()

            # Atualizados
            for _, row in edited_df.iterrows():
                if pd.notna(row['id']) and row['id'] in df_original['id'].values:
                    orig_row = df_original[df_original['id'] == row['id']].iloc[0]
                    if not row.equals(orig_row):
                        update_dict = row.drop('id').to_dict()
                        if pd.notna(update_dict.get('data_venda')):
                            update_dict['data_venda'] = update_dict['data_venda'].isoformat()
                        if pd.notna(update_dict.get('quantidade')):
                            update_dict['quantidade'] = int(update_dict['quantidade'])
                        supabase.table('vendas').update(update_dict).eq('id', row['id']).execute()

            st.success("✅ Alterações salvas com sucesso!")
            st.session_state.data_viewed = get_data(supabase)
            st.rerun()

    with tab2:
        st.header("Relatórios e Gráficos")
        df_report = get_data(supabase)
        if df_report.empty:
            st.info("Nenhum dado disponível para relatórios.")
        else:
            col1, col2, col3, col4, col5 = st.columns(5)
            estabs_u = sorted(df_report['estabelecimento'].dropna().unique())
            f_estab = col1.multiselect("Estabelecimento", estabs_u, default=estabs_u)
            bairros_u = sorted(df_report['bairro'].dropna().unique())
            f_bairro = col2.multiselect("Bairro", bairros_u, default=bairros_u)
            formas_u = sorted(df_report['forma_pagamento'].dropna().unique())
            f_forma = col3.multiselect("Forma Pagamento", formas_u, default=formas_u)
            prods_u = sorted(df_report['produto'].dropna().unique())
            f_prod = col4.multiselect("Produto", prods_u, default=prods_u)
            col5.markdown("**Data**")

            min_date = st.date_input("Data Inicial", value=df_report['data_venda'].min().date())
            max_date = st.date_input("Data Final", value=df_report['data_venda'].max().date())

            filtered_df = df_report.copy()
            if f_estab:
                filtered_df = filtered_df[filtered_df['estabelecimento'].isin(f_estab)]
            if f_bairro:
                filtered_df = filtered_df[filtered_df['bairro'].isin(f_bairro)]
            if f_forma:
                filtered_df = filtered_df[filtered_df['forma_pagamento'].isin(f_forma)]
            if f_prod:
                filtered_df = filtered_df[filtered_df['produto'].isin(f_prod)]
            if pd.notna(min_date):
                filtered_df = filtered_df[filtered_df['data_venda'] >= pd.to_datetime(min_date)]
            if pd.notna(max_date):
                filtered_df = filtered_df[filtered_df['data_venda'] <= pd.to_datetime(max_date)]

            if filtered_df.empty:
                st.info("Nenhum registro encontrado com os filtros aplicados.")
            else:
                col_a, col_b, col_c = st.columns(3)
                total_vendas = filtered_df['total_venda'].sum()
                total_comissao = filtered_df['valor_comissao'].sum()
                qtd_vendas = len(filtered_df)
                col_a.metric("Total Vendas", f"R$ {total_vendas:,.2f}")
                col_b.metric("Total Comissão", f"R$ {total_comissao:,.2f}")
                col_c.metric("Qtd. Vendas", qtd_vendas)

                st.subheader("📈 Gráficos")
                fig1 = px.bar(filtered_df.groupby('produto')['total_venda'].sum().reset_index(), x='produto', y='total_venda', title="Total Vendas por Produto")
                st.plotly_chart(fig1, use_container_width=True)

                fig2 = px.pie(filtered_df, names='forma_pagamento', values='total_venda', title="Distribuição por Forma de Pagamento")
                st.plotly_chart(fig2, use_container_width=True)

                fig3 = px.bar(filtered_df.groupby('bairro')['total_venda'].sum().reset_index(), x='bairro', y='total_venda', title="Total Vendas por Bairro")
                st.plotly_chart(fig3, use_container_width=True)

                daily_sales = filtered_df.groupby(filtered_df['data_venda'].dt.date)['total_venda'].sum().reset_index()
                fig4 = px.line(daily_sales, x='data_venda', y='total_venda', title="Vendas por Data")
                st.plotly_chart(fig4, use_container_width=True)

                fig5 = px.scatter(filtered_df, x='total_venda', y='valor_comissao', color='estabelecimento', size='quantidade', hover_data=['produto'], title="Comissão vs Total Venda")
                st.plotly_chart(fig5, use_container_width=True)