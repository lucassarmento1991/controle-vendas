import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from supabase import create_client, Client
from datetime import date, datetime

# 1. CONFIGURAÇÃO E INICIALIZAÇÃO RESILIENTE
st.set_page_config(page_title="Controle de Vendas", layout="wide", page_icon="📊")

@st.cache_resource
def init_supabase():
    try:
        # Busca resiliente: tenta bloco [supabase], depois tenta raiz direta
        if "supabase" in st.secrets:
            url = st.secrets["supabase"].get("url") or st.secrets["supabase"].get("SUPABASE_URL")
            key = st.secrets["supabase"].get("key") or st.secrets["supabase"].get("SUPABASE_KEY")
        else:
            url = st.secrets.get("SUPABASE_URL") or st.secrets.get("url")
            key = st.secrets.get("SUPABASE_KEY") or st.secrets.get("key")

        if not url or not key:
            st.error("❌ Erro de Configuração: Chaves do Supabase não encontradas nos Secrets.")
            st.stop()
            
        return create_client(url.strip(), key.strip())
    except Exception as e:
        st.error(f"Erro de Conexão: Verifique os Secrets no Streamlit Cloud. {str(e)}")
        st.stop()

supabase: Client = init_supabase()

# 2. SISTEMA DE AUTENTICAÇÃO ROBUSTO
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Gestão de Vendas")
    with st.form("login_form"):
        user_input = st.text_input("Usuário (Username)").strip()
        pass_input = st.text_input("Senha", type="password")
        
        if st.form_submit_button("Entrar", use_container_width=True):
            try:
                # Busca exata pelo username na tabela 'usuarios'
                res = supabase.table('usuarios').select('*').eq('username', user_input).execute()
                
                if res.data:
                    db_user = res.data[0]
                    input_hash = hash_password(pass_input)
                    
                    if db_user['password_hash'] == input_hash:
                        st.session_state.logged_in = True
                        st.session_state.username = user_input
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("Usuário não encontrado.")
            except Exception as e:
                st.error(f"Falha na comunicação com o banco: {str(e)}")
    st.stop()

# 3. INTERFACE E CARREGAMENTO DE DADOS
st.sidebar.title(f"👤 {st.session_state.username}")

# NOVO: Funcionalidade de Alterar Senha solicitada
with st.sidebar.expander("🔑 Alterar minha senha"):
    with st.form("change_password_form"):
        current_pw = st.text_input("Senha Atual", type="password")
        new_pw = st.text_input("Nova Senha", type="password")
        confirm_pw = st.text_input("Confirme a Nova Senha", type="password")
        
        if st.form_submit_button("Atualizar Senha"):
            # Validação da senha atual
            res_val = supabase.table('usuarios').select('password_hash').eq('username', st.session_state.username).execute()
            if res_val.data and res_val.data[0]['password_hash'] == hash_password(current_pw):
                if new_pw == confirm_pw and len(new_pw) >= 4:
                    new_hash = hash_password(new_pw)
                    supabase.table('usuarios').update({"password_hash": new_hash}).eq('username', st.session_state.username).execute()
                    st.success("✅ Senha alterada com sucesso!")
                else:
                    st.error("As senhas não coincidem ou são muito curtas.")
            else:
                st.error("Senha atual incorreta.")

if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

@st.cache_data(ttl=60)
def load_data():
    try:
        res = supabase.table('vendas').select('*').order('data_venda', desc=True).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data_venda'] = pd.to_datetime(df['data_venda']).dt.date
            cols_num = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
            for col in cols_num:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
        return df
    except:
        return pd.DataFrame()

tab1, tab2, tab3 = st.tabs(["🛒 Cadastro", "🗑️ Gerenciar Registros", "📊 Relatórios"])

# --- ABA CADASTRO ---
with tab1:
    st.header("Novo Cadastro")
    with st.form("cadastro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            est = st.text_input("Estabelecimento")
            dt = st.date_input("Data", value=date.today())
            br = st.text_input("Bairro")
            pg = st.selectbox("Pagamento", ["Pix", "Cartão", "Dinheiro", "Boleto", "Não Pago"])
        with c2:
            prod = st.text_input("Produto")
            qtd = st.number_input("Quantidade", min_value=1)
            val = st.number_input("Valor Unitário", min_value=0.01)
            com = st.number_input("Comissão %", value=10.0)
        
        total = qtd * val
        v_com = total * (com / 100)
        
        if st.form_submit_button("Salvar Venda", use_container_width=True):
            data = {
                "estabelecimento": est, "data_venda": dt.isoformat(), "bairro": br,
                "forma_pagamento": pg, "produto": prod, "quantidade": float(qtd),
                "valor_produto": float(val), "total_venda": float(total),
                "comissao_percentual": float(com), "valor_comissao": float(v_com), "status": "ativa"
            }
            supabase.table('vendas').insert(data).execute()
            st.success("Venda salva com sucesso!")
            st.cache_data.clear()

# --- ABA GERENCIAR (APENAS EXCLUSÃO) ---
with tab2:
    st.header("Gerenciamento de Registros")
    st.warning("⚠️ Edição desativada. Use a lixeira para excluir registros.")
    df_excluir = load_data()
    
    if not df_excluir.empty:
        config_view = {col: st.column_config.Column(disabled=True) for col in df_excluir.columns}
        
        edited_df = st.data_editor(
            df_excluir, 
            num_rows="dynamic", 
            column_config=config_view, 
            use_container_width=True,
            hide_index=True
        )
        if st.button("🗑️ Confirmar Exclusões no Banco", type="primary"):
            orig_ids = set(df_excluir['id'].tolist())
            curr_ids = set(edited_df['id'].dropna().tolist())
            ids_para_deletar = orig_ids - curr_ids
            
            if ids_para_deletar:
                for rid in ids_para_deletar:
                    supabase.table('vendas').delete().eq('id', rid).execute()
                st.success(f"Registros removidos com sucesso!")
                st.cache_data.clear()
                st.rerun()

# --- ABA RELATÓRIOS ---
with tab3:
    st.header("Análise de Dados")
    df_rel = load_data()
    
    if not df_rel.empty:
        with st.expander("🔍 Filtros Avançados", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                d_ini = st.date_input("De:", value=df_rel['data_venda'].min())
                d_fim = st.date_input("Até:", value=date.today())
            with c2:
                f_est = st.multiselect("Estabelecimentos", options=sorted(df_rel['estabelecimento'].unique()))
                f_bairro = st.multiselect("Bairros", options=sorted(df_rel['bairro'].unique()))
            with c3:
                f_pag = st.multiselect("Formas de Pagamento", options=sorted(df_rel['forma_pagamento'].unique()))
        
        df_f = df_rel[(df_rel['data_venda'] >= d_ini) & (df_rel['data_venda'] <= d_fim)]
        if f_est: df_f = df_f[df_f['estabelecimento'].isin(f_est)]
        if f_bairro: df_f = df_f[df_f['bairro'].isin(f_bairro)]
        if f_pag: df_f = df_f[df_f['forma_pagamento'].isin(f_pag)]
        
        if not df_f.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Faturamento", f"R$ {df_f['total_venda'].sum():,.2f}")
            m2.metric("Comissões", f"R$ {df_f['valor_comissao'].sum():,.2f}")
            m3.metric("Total Vendas", len(df_f))
            
            st.plotly_chart(px.bar(df_f, x="data_venda", y="total_venda", color="estabelecimento", barmode="group"), use_container_width=True)