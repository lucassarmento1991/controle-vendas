import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
import datetime

@st.cache_resource
def get_supabase():
    try:
        if "supabase" in st.secrets:
            config = st.secrets["supabase"]
            url = config.get("url", "").strip()
            anon_key = config.get("anon_key", config.get("key", "")).strip()
        else:
            url = st.secrets.get("SUPABASE_URL", "").strip()
            anon_key = st.secrets.get("SUPABASE_ANON_KEY", st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
        if not url or not anon_key:
            st.error("Configurações do Supabase não encontradas.")
            return None
        return create_client(url, anon_key)
    except Exception as e:
        st.error(f"Erro ao inicializar Supabase: {e}")
        return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if st.session_state.logged_in:
        return True

    st.title("Login")
    tab1, tab2 = st.tabs(["Entrar", "Criar Usuário"])

    with tab1:
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            supabase = get_supabase()
            if supabase:
                hashed = hash_password(password)
                res = supabase.table("usuarios").select("id").eq("username", username).eq("password", hashed).execute()
                if res.data:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")

    with tab2:
        new_username = st.text_input("Novo Usuário")
        new_password = st.text_input("Nova Senha", type="password")
        if st.button("Criar Usuário"):
            supabase = get_supabase()
            if supabase:
                hashed = hash_password(new_password)
                try:
                    res = supabase.table("usuarios").insert({"username": new_username, "password": hashed}).execute()
                    if res.data:
                        st.success("Usuário criado com sucesso!")
                    else:
                        st.error("Erro ao criar usuário.")
                except Exception as e:
                    st.error(f"Erro: {e}")

    if not st.session_state.logged_in:
        st.stop()

st.set_page_config(page_title="App Vendas", layout="wide")

check_login()

if 'cache_buster' not in st.session_state:
    st.session_state.cache_buster = 0

def refresh_data():
    st.session_state.cache_buster += 1
    st.rerun()

# Sidebar
with st.sidebar:
    st.button("Atualizar Dados", on_click=refresh_data)
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

@st.cache_data
def load_vendas(cache_buster):
    supabase = get_supabase()
    if not supabase:
        return pd.DataFrame()
    res = supabase.table("vendas").select("*").order("data_venda", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['data_venda'] = pd.to_datetime(df['data_venda'], errors='coerce')
        # Ensure numeric columns
        numeric_cols = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

df = load_vendas(st.session_state.cache_buster)

supabase = get_supabase()

tab1, tab2, tab3 = st.tabs(["Cadastro", "Edição em Massa", "Relatórios"])

with tab1:
    st.header("Cadastro de Venda")
    with st.form("form_cadastro"):
        col1, col2 = st.columns(2)
        with col1:
            estabelecimento = st.text_input("Estabelecimento")
            data_venda = st.date_input("Data da Venda", value=datetime.date.today())
            bairro = st.selectbox("Bairro", options=["Centro", "Norte", "Sul", "Leste", "Oeste"])
            forma_pagamento = st.selectbox("Forma de Pagamento", options=["Dinheiro", "Pix", "Cartão", "Boleto"])
            produto = st.text_input("Produto")
        with col2:
            quantidade = st.number_input("Quantidade", min_value=1, step=1)
            valor_produto = st.number_input("Valor por Produto", min_value=0.01, format="%.2f")
            comissao_percentual = st.number_input("Comissão Percentual", min_value=0.0, max_value=100.0, value=10.0, step=0.1, format="%.1f")

        total_venda = quantidade * valor_produto
        valor_comissao = total_venda * (comissao_percentual / 100)

        st.info(f"**Total da Venda:** R$ {total_venda:.2f}")
        st.info(f"**Valor da Comissão:** R$ {valor_comissao:.2f}")

        status = st.selectbox("Status", options=["Pendente", "Pago", "Cancelado"])

        submitted = st.form_submit_button("Cadastrar Venda")
        if submitted and supabase:
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
            res = supabase.table("vendas").insert(data).execute()
            if res.data:
                st.success("Venda cadastrada com sucesso!")
                refresh_data()
            else:
                st.error("Erro ao cadastrar venda.")

with tab2:
    st.header("Edição em Massa")
    if df.empty:
        st.info("Nenhum dado para editar.")
    else:
        st.dataframe(df, use_container_width=True)

        # Delete
        selected_ids = st.multiselect("IDs para excluir", options=df['id'].astype(str).tolist())
        if st.button("Excluir Selecionados") and selected_ids and supabase:
            for id_str in selected_ids:
                supabase.table("vendas").delete().eq("id", id_str).execute()
            st.success("Registros excluídos!")
            refresh_data()

        # Edit
        st.subheader("Editar Dados")
        original_df = df[['id', 'estabelecimento', 'data_venda', 'bairro', 'forma_pagamento', 'produto', 'quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao', 'status']].copy()

        column_config = {
            "id": st.column_config.TextColumn("ID", disabled=True),
            "data_venda": st.column_config.DateColumn("Data da Venda"),
            "quantidade": st.column_config.NumberColumn("Quantidade", min_value=1, step=1),
            "valor_produto": st.column_config.NumberColumn("Valor Unitário", format="%.2f"),
            "total_venda": st.column_config.NumberColumn("Total Venda", format="%.2f"),
            "comissao_percentual": st.column_config.NumberColumn("% Comissão", format="%.2f"),
            "valor_comissao": st.column_config.NumberColumn("Valor Comissão", format="%.2f"),
            "status": st.column_config.SelectboxColumn("Status", options=["Pendente", "Pago", "Cancelado"]),
        }

        edited_df = st.data_editor(
            original_df,
            num_rows="fixed",
            use_container_width=True,
            column_config=column_config,
            hide_index=False,
        )

        if st.button("Salvar Alterações") and supabase:
            updated = 0
            for idx in range(len(edited_df)):
                orig_row = original_df.iloc[idx]
                edit_row = edited_df.iloc[idx]
                if not orig_row.equals(edit_row):
                    changes = {}
                    for col in edit_row.index:
                        if col != 'id' and edit_row[col] != orig_row[col]:
                            changes[col] = edit_row[col]
                    if changes:
                        update_res = supabase.table("vendas").update(changes).eq("id", edit_row['id']).execute()
                        if update_res.data:
                            updated += 1
            st.success(f"{updated} registros atualizados!")
            refresh_data()

with tab3:
    st.header("Relatórios")
    if df.empty:
        st.info("Nenhum dado para relatórios.")
    else:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            min_date = df['data_venda'].min().date()
            max_date = df['data_venda'].max().date()
            date_from, date_to = st.date_input("Período", [min_date, max_date])
        with col2:
            unique_bairros = sorted(df['bairro'].unique())
            bairros = st.multiselect("Bairros", unique_bairros)
        with col3:
            unique_pag = sorted(df['forma_pagamento'].unique())
            pagamentos = st.multiselect("Formas de Pagamento", unique_pag)
        with col4:
            unique_prod = sorted(df['produto'].dropna().unique())
            produtos = st.multiselect("Produtos", unique_prod)
        with col5:
            unique_estab = sorted(df['estabelecimento'].unique())
            estabs = st.multiselect("Estabelecimentos", unique_estab)

        filtered_df = df.copy()
        filtered_df = filtered_df[(filtered_df['data_venda'].dt.date >= date_from) & (filtered_df['data_venda'].dt.date <= date_to)]
        if bairros:
            filtered_df = filtered_df[filtered_df['bairro'].isin(bairros)]
        if pagamentos:
            filtered_df = filtered_df[filtered_df['forma_pagamento'].isin(pagamentos)]
        if produtos:
            filtered_df = filtered_df[filtered_df['produto'].isin(produtos)]
        if estabs:
            filtered_df = filtered_df[filtered_df['estabelecimento'].isin(estabs)]

        col_a, col_b, col_c = st.columns(3)
        total_vendas = len(filtered_df)
        total_valor = filtered_df['total_venda'].sum()
        total_comissao = filtered_df['valor_comissao'].sum()

        col_a.metric("Total de Vendas", total_vendas)
        col_b.metric("Faturamento Total", f"R$ {total_valor:.2f}")
        col_c.metric("Comissão Total", f"R$ {total_comissao:.2f}")

        st.dataframe(filtered_df, use_container_width=True)

        st.subheader("Gráfico: Faturamento por Bairro")
        if not filtered_df.empty:
            chart_data = filtered_df.groupby('bairro')['total_venda'].sum().reset_index()
            st.bar_chart(chart_data.set_index('bairro'))

            st.subheader("Gráfico: Vendas por Forma de Pagamento")
            chart_data2 = filtered_df.groupby('forma_pagamento')['total_venda'].sum().reset_index()
            st.bar_chart(chart_data2.set_index('forma_pagamento'))