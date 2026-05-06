import streamlit as st
import pandas as pd
import hashlib
from supabase import create_client
from datetime import date, datetime

@st.cache_resource
def init_supabase():
    secrets = st.secrets
    url = (
        secrets.get('SUPABASE_URL') or
        secrets.get('supabase', {}).get('url') or
        secrets.get('url', '').strip()
    ).strip()

    key_candidates = [
        'SUPABASE_KEY',
        'SUPABASE_ANON_KEY',
        'anon_key',
        ('supabase', 'anon_key'),
        ('supabase', 'key'),
        ('supabase', 'SUPABASE_ANON_KEY'),
    ]
    key = ''
    for candidate in key_candidates:
        if isinstance(candidate, tuple):
            key = secrets.get(candidate[0], {}).get(candidate[1], '').strip()
        else:
            key = secrets.get(candidate, '').strip()
        if key:
            break

    if not url or not key:
        st.error("Configurações do Supabase não encontradas nos secrets.")
        st.stop()

    return create_client(url, key)

supabase = init_supabase()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if email and password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            result = supabase.table('usuarios').select('id').eq('email', email).eq('password_hash', password_hash).execute()
            if result.data:
                st.session_state.user_id = result.data[0]['id']
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
        else:
            st.warning("Preencha email e senha.")
else:
    # Sidebar logout
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.pop('user_id', None)
        st.rerun()

    st.title("Gerenciamento de Registros")
    tab1, tab2 = st.tabs(["Gerenciar Registros", "Relatórios"])

    with tab1:
        st.subheader("Gerenciar Registros (apenas exclusão habilitada)")
        result = supabase.table('registros').select('*').execute()
        df = pd.DataFrame(result.data)
        if df.empty:
            st.info("Nenhum registro encontrado.")
        else:
            st.dataframe(df, use_container_width=True)
            selected_ids = st.multiselect(
                "Selecione IDs para excluir:",
                options=df['id'].tolist(),
                format_func=lambda x: f"ID {x}"
            )
            if st.button("Confirmar Exclusões") and selected_ids:
                for sid in selected_ids:
                    supabase.table('registros').delete().eq('id', sid).execute()
                st.success(f"{len(selected_ids)} registros excluídos.")
                st.rerun()

    with tab2:
        st.subheader("Relatórios")
        result = supabase.table('registros').select('*').execute()
        df_rep = pd.DataFrame(result.data)
        if df_rep.empty:
            st.info("Nenhum dado para relatórios.")
        else:
            if 'data' in df_rep.columns:
                df_rep['data'] = pd.to_datetime(df_rep['data'], errors='coerce')
                min_date = df_rep['data'].dt.date.min()
                max_date = df_rep['data'].dt.date.max()
            else:
                min_date = max_date = date.today()

            col1, col2, col3 = st.columns(3)
            with col1:
                est_opts = sorted(df_rep['estabelecimento'].dropna().unique())
                est_sel = st.multiselect("Estabelecimento", est_opts)
            with col2:
                pag_opts = sorted(df_rep['pagamento'].dropna().unique())
                pag_sel = st.multiselect("Pagamento", pag_opts)
            with col3:
                bai_opts = sorted(df_rep['bairro'].dropna().unique())
                bai_sel = st.multiselect("Bairro", bai_opts)

            date_range = st.date_input("Intervalo de datas", (min_date, max_date))
            data_ini, data_fim = date_range

            filtered = df_rep.copy()
            if est_sel:
                filtered = filtered[filtered['estabelecimento'].isin(est_sel)]
            if pag_sel:
                filtered = filtered[filtered['pagamento'].isin(pag_sel)]
            if bai_sel:
                filtered = filtered[filtered['bairro'].isin(bai_sel)]
            if 'data' in filtered.columns and pd.notna(data_ini):
                filtered = filtered[filtered['data'].dt.date >= data_ini]
            if 'data' in filtered.columns and pd.notna(data_fim):
                filtered = filtered[filtered['data'].dt.date <= data_fim]

            st.subheader("Dados Filtrados")
            st.dataframe(filtered, use_container_width=True)