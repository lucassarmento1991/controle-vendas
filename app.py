import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib

# Initialize Supabase
@st.cache_resource
def init_supabase():
    return create_client(st.secrets['supabase']['url'], st.secrets['supabase']['key'])

supabase: Client = init_supabase()

# Password hash function
def hash_password(password):
    return hashlib.sha256(password.strip().encode('utf-8')).hexdigest()

# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

# Login page
if not st.session_state.logged_in:
    st.title("Sistema de Controle de Vendas - Login")
    username = st.text_input("Usuário").strip()
    password = st.text_input("Senha", type="password").strip()
    
    if st.button("Entrar"):
        hashed_pw = hash_password(password)
        st.info(f"DEBUG TEMPORÁRIO: Hash gerado: {hashed_pw}")  # Debug for comparison with DB
        
        if username == 'vendas' and hashed_pw == 'ad1e10c7f2d809520c2191e442ed016ed7507debeaad03d061a97ec69dc2361e':
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("Login realizado com sucesso!")
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")
else:
    st.title(f"Sistema de Controle de Vendas - Bem-vindo, {st.session_state.username}")
    
    # Sidebar logout
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()
    
    # Tabs
    tab1, tab2 = st.tabs(["Gerenciar Registros", "Relatórios"])
    
    with tab1:
        st.subheader("Gerenciar Registros")
        
        # Fetch data from Supabase
        response = supabase.table('vendas').select('*').execute()
        df = pd.DataFrame(response.data)
        
        if df.empty:
            st.info("Nenhum registro encontrado.")
        else:
            # Prepare dataframe with delete column
            df_display = df.copy()
            df_display['Excluir'] = False
            
            # Column configuration: all disabled except 'Excluir'
            col_config = {}
            for col in df.columns:
                col_config[col] = st.column_config.TextColumn(col, disabled=True)
            col_config['Excluir'] = st.column_config.CheckboxColumn("Excluir", default=False)
            
            # Data editor
            edited_df = st.data_editor(
                df_display,
                column_config=col_config,
                use_container_width=True,
                hide_index=True
            )
            
            # Confirm deletions
            if st.button("Confirmar Exclusões"):
                deleted_rows = edited_df[edited_df['Excluir'] == True]
                deleted_ids = deleted_rows['id'].tolist()
                
                if deleted_ids:
                    success_count = 0
                    for id_val in deleted_ids:
                        result = supabase.table('vendas').delete().eq('id', id_val).execute()
                        if result.data:
                            success_count += 1
                    st.success(f"{success_count} registros excluídos com sucesso do Supabase.")
                    st.rerun()
                else:
                    st.warning("Nenhum registro selecionado para exclusão.")
    
    with tab2:
        st.subheader("Relatórios")
        
        # Fetch or cache reports data
        if 'df_reports' not in st.session_state:
            response = supabase.table('vendas').select('*').execute()
            st.session_state.df_reports = pd.DataFrame(response.data)
        
        df_rep = st.session_state.df_reports.copy()
        
        if df_rep.empty:
            st.info("Nenhum dado para relatórios.")
        else:
            # Multiselect filters
            est_unique = sorted(df_rep['estabelecimento'].dropna().unique())
            bairro_unique = sorted(df_rep['bairro'].dropna().unique())
            pag_unique = sorted(df_rep['forma_pagamento'].dropna().unique())
            
            col1, col2, col3 = st.columns(3)
            with col1:
                selected_est = st.multiselect("Estabelecimento", est_unique, default=est_unique)
            with col2:
                selected_bairro = st.multiselect("Bairro", bairro_unique, default=bairro_unique)
            with col3:
                selected_pag = st.multiselect("Forma Pagamento", pag_unique, default=pag_unique)
            
            # Apply filters
            mask = (
                df_rep['estabelecimento'].isin(selected_est) &
                df_rep['bairro'].isin(selected_bairro) &
                df_rep['forma_pagamento'].isin(selected_pag)
            )
            filtered_df = df_rep[mask].copy()
            
            if filtered_df.empty:
                st.info("Nenhum registro com os filtros selecionados.")
            else:
                # Charts
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    fig1 = px.bar(
                        filtered_df,
                        x='estabelecimento',
                        y='total_venda',
                        title='Vendas por Estabelecimento',
                        color='estabelecimento'
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col_chart2:
                    fig2 = px.pie(
                        filtered_df,
                        names='forma_pagamento',
                        values='total_venda',
                        title='Distribuição por Forma de Pagamento'
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                
                # Filtered data table
                st.subheader("Dados Filtrados")
                st.dataframe(filtered_df, use_container_width=True)
