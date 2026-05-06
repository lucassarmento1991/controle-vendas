import streamlit as st
import pandas as pd
import hashlib
from supabase import create_client, Client
from datetime import date

st.set_page_config(page_title="Gestão de Vendas", page_icon="⭐", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

@st.cache_resource
def init_supabase():
    try:
        url = st.secrets['supabase']['url']
        key = st.secrets['supabase']['key']
        return create_client(url, key)
    except Exception as e:
        st.error(f"Falha ao inicializar Supabase: {str(e)}")
        return None

@st.cache_data(ttl=300)
def load_data(supabase: Client):
    if not supabase:
        return pd.DataFrame()
    try:
        response = supabase.table('vendas').select('*').execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['data_venda'] = pd.to_datetime(df['data_venda'], errors='coerce')
            # Garantir tipos numéricos
            numeric_cols = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

if not st.session_state.logged_in:
    st.title("🔑 Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        if st.button("Entrar", use_container_width=True):
            u = username.strip()
            p = password.strip()
            if u and p:
                h = hashlib.sha256(p.encode()).hexdigest()
                st.info(f"Hash gerado: {h}")  # Log temporário para debug
                expected_hash = "90e4f8d6874e0573e936e57200233083f9872e909a349f7e4975d7963286392a"
                if u == "paodequeijo" and h == expected_hash:
                    st.session_state.logged_in = True
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Senha incorreta!")
                    st.info(f"Hash esperado para 'vendas2026': {expected_hash}")  # Debug extra
            else:
                st.warning("Preencha usuário e senha!")
else:
    supabase = init_supabase()
    df = load_data(supabase)
    
    st.sidebar.title("📦 Menu")
    if st.sidebar.button("Sair", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    tab1, tab2 = st.tabs(["Gerenciar", "Relatórios"])
    
    with tab1:
        st.subheader("Gerenciar Vendas (Apenas Exclusão)")
        if df.empty:
            st.warning("Nenhum registro encontrado.")
        else:
            col_config = {
                "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "estabelecimento": st.column_config.TextColumn("Estabelecimento", disabled=True),
                "data_venda": st.column_config.DatetimeColumn("Data da Venda", disabled=True),
                "bairro": st.column_config.TextColumn("Bairro", disabled=True),
                "forma_pagamento": st.column_config.TextColumn("Forma de Pagamento", disabled=True),
                "produto": st.column_config.TextColumn("Produto", disabled=True),
                "quantidade": st.column_config.NumberColumn("Quantidade", disabled=True, format="%.0f"),
                "valor_produto": st.column_config.NumberColumn("Valor Unitário", disabled=True, format="R$ %.2f"),
                "total_venda": st.column_config.NumberColumn("Total Venda", disabled=True, format="R$ %.2f"),
                "comissao_percentual": st.column_config.NumberColumn("% Comissão", disabled=True, format="%.2f %%"),
                "valor_comissao": st.column_config.NumberColumn("Valor Comissão", disabled=True, format="R$ %.2f"),
                "status": st.column_config.TextColumn("Status", disabled=True)
            }
            
            edited_df = st.data_editor(
                df,
                column_config=col_config,
                hide_index=True,
                use_container_width=True
            )
            
            if st.button("Salvar Exclusões", type="primary"):
                if len(edited_df) < len(df):
                    ids_before = set(df['id'].astype(int))
                    ids_after = set(edited_df['id'].astype(int))
                    to_delete = list(ids_before - ids_after)
                    deleted_count = 0
                    for id_del in to_delete:
                        res = supabase.table('vendas').delete().eq('id', id_del).execute()
                        if res.data:
                            deleted_count += 1
                    st.cache_data.clear()
                    st.success(f"{deleted_count} linha(s) excluída(s) com sucesso!")
                    st.rerun()
                else:
                    st.info("Nenhuma exclusão detectada.")
    
    with tab2:
        st.subheader("Relatórios com Filtros Avançados")
        if df.empty:
            st.warning("Nenhum dado para exibir.")
        else:
            with st.expander("Filtros Avançados", expanded=True):
                col1, col2, col3 = st.columns(3)
                est_options = sorted(df['estabelecimento'].dropna().unique())
                fp_options = sorted(df['forma_pagamento'].dropna().unique())
                bai_options = sorted(df['bairro'].dropna().unique())
                
                selected_est = col1.multiselect("Estabelecimento", est_options)
                selected_fp = col2.multiselect("Forma de Pagamento", fp_options)
                selected_bai = col3.multiselect("Bairro", bai_options)
                
                col_date1, col_date2 = st.columns(2)
                min_date = df['data_venda'].dt.date.min().date() if not pd.isna(df['data_venda'].min()) else date.today()
                max_date = df['data_venda'].dt.date.max().date() if not pd.isna(df['data_venda'].max()) else date.today()
                date_from = col_date1.date_input("Data Inicial", value=min_date)
                date_to = col_date2.date_input("Data Final", value=max_date)
            
            filtered_df = df.copy()
            
            if selected_est:
                filtered_df = filtered_df[filtered_df['estabelecimento'].isin(selected_est)]
            if selected_fp:
                filtered_df = filtered_df[filtered_df['forma_pagamento'].isin(selected_fp)]
            if selected_bai:
                filtered_df = filtered_df[filtered_df['bairro'].isin(selected_bai)]
            
            date_mask = (filtered_df['data_venda'].dt.date >= date_from) & (filtered_df['data_venda'].dt.date <= date_to)
            filtered_df = filtered_df[date_mask]
            
            if not filtered_df.empty:
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                total_vendas = filtered_df['total_venda'].sum()
                total_comissao = filtered_df['valor_comissao'].sum()
                qtd_vendas = len(filtered_df)
                avg_comissao = filtered_df['valor_comissao'].mean()
                
                col_m1.metric("Total Vendas", f"R$ {total_vendas:,.2f}")
                col_m2.metric("Total Comissão", f"R$ {total_comissao:,.2f}")
                col_m3.metric("Qtd. Vendas", qtd_vendas)
                col_m4.metric("Média Comissão", f"R$ {avg_comissao:,.2f}" if not pd.isna(avg_comissao) else "R$ 0,00")
                
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum registro atende aos filtros selecionados.")
