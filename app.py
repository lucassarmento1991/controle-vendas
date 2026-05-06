import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date, datetime
import os

st.set_page_config(page_title="Sistema de Controle de Vendas V3.1", layout="wide")

st.title("🛒 Sistema de Controle de Vendas V3.1 (Correção de Tipos e Estabilidade)")

# Configurações Supabase no sidebar
with st.sidebar.expander("⚙️ Configurações Supabase", expanded=False):
    supabase_url = st.text_input("URL do Projeto", type="password", help="Ex: https://xyz.supabase.co")
    supabase_key = st.text_input("Chave Anon", type="password", help="Chave pública do projeto")

    if st.button("Testar Conexão"):
        try:
            client = create_client(supabase_url, supabase_key)
            client.table('vendas').select('count', count='exact').execute()
            st.success("Conexão OK!")
        except Exception as e:
            st.error(f"Erro: {e}")

if not supabase_url or not supabase_key:
    st.warning("🔧 Preencha as configurações do Supabase no sidebar.")
    st.stop()

supabase: Client = create_client(supabase_url, supabase_key)

@st.cache_data(ttl=300)
def load_data(_supabase: Client) -> pd.DataFrame:
    try:
        response = _supabase.table('vendas').select('*').order('data_venda', desc=True).execute()
        data = response.data
        if data:
            df = pd.DataFrame(data)
            # Conversões explícitas de tipos para compatibilidade com st.data_editor
            if 'data_venda' in df.columns:
                df['data_venda'] = pd.to_datetime(df['data_venda'], errors='coerce').dt.date
            numeric_cols = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')
            return df
        else:
            return pd.DataFrame(columns=['id', 'data_venda', 'produto', 'quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao', 'vendedor'])
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# Carrega dados
df_atual = load_data(supabase)

# Configuração de colunas com tipos corretos
tab1, tab2 = st.tabs(["📝 Cadastro", "📊 Relatórios"])

numeric_cols = ['quantidade', 'valor_produto', 'total_venda', 'comissao_percentual', 'valor_comissao']

column_config = {
    "id": st.column_config.TextColumn("ID", disabled=True, width="small"),
    "data_venda": st.column_config.DateColumn("Data da Venda", width="medium"),
    "produto": st.column_config.TextColumn("Produto", width="medium"),
    "vendedor": st.column_config.TextColumn("Vendedor", width="medium"),
    "quantidade": st.column_config.NumberColumn("Quantidade", format="%.0f", width="small"),
    "valor_produto": st.column_config.NumberColumn("Valor Unitário", format="R$ %.2f", width="small"),
    "total_venda": st.column_config.NumberColumn("Total Venda", format="R$ %.2f", width="small"),
    "comissao_percentual": st.column_config.NumberColumn("Comissão %", format="%.2f", width="small"),
    "valor_comissao": st.column_config.NumberColumn("Valor Comissão", format="R$ %.2f", width="small"),
    "delete": st.column_config.CheckboxColumn("Deletar", default=False, width="small"),
}

with tab1:
    st.subheader("Gerenciar Vendas")

    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

    # Prepara DataFrame para editor com tipos corretos
    df_editor = df_atual.copy()
    if 'delete' not in df_editor.columns:
        df_editor['delete'] = False

    # Conversões explícitas ANTES do data_editor
    df_editor['data_venda'] = pd.to_datetime(df_editor['data_venda'], errors='coerce').dt.date
    for col in numeric_cols:
        if col in df_editor.columns:
            df_editor[col] = pd.to_numeric(df_editor[col], errors='coerce').astype('float64')

    edited_df = st.data_editor(
        df_editor,
        column_config=column_config,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=False,
        key="vendas_editor"
    )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 Salvar Alterações", type="primary"):
            try:
                # Deletar primeiro
                to_delete_ids = edited_df[edited_df['delete'] == True]['id'].dropna().tolist()
                for id_val in to_delete_ids:
                    supabase.table('vendas').delete().eq('id', id_val).execute()

                # Preparar rows sem delete
                edited_no_delete = edited_df[edited_df['delete'] == False].drop(columns=['delete'])
                added_rows = edited_no_delete[pd.isna(edited_no_delete['id'])]
                updated_rows = edited_no_delete[~pd.isna(edited_no_delete['id'])]

                # Insert
                for _, row in added_rows.iterrows():
                    data = row.dropna().to_dict()
                    if 'id' in data:
                        del data['id']
                    data['data_venda'] = data['data_venda'].isoformat()
                    data['total_venda'] = float(data['quantidade']) * float(data['valor_produto'])
                    data['valor_comissao'] = data['total_venda'] * (float(data['comissao_percentual']) / 100.0)
                    supabase.table('vendas').insert(data).execute()

                # Update
                for _, row in updated_rows.iterrows():
                    data = row.dropna().to_dict()
                    data['data_venda'] = data['data_venda'].isoformat()
                    data['total_venda'] = float(data['quantidade']) * float(data['valor_produto'])
                    data['valor_comissao'] = data['total_venda'] * (float(data['comissao_percentual']) / 100.0)
                    supabase.table('vendas').update(data).eq('id', data['id']).execute()

                st.success("✅ Alterações salvas com sucesso!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao salvar: {str(e)}")

    with col_btn2:
        if st.button("↩️ Cancelar"):
            st.rerun()

with tab2:
    st.subheader("Relatórios Filtrados")

    col1, col2, col3 = st.columns(3)
    data_inicio = col1.date_input("Data Início", value=date.today())
    data_fim = col2.date_input("Data Fim", value=date.today())
    vendedores = ["Todos"] + sorted(df_atual['vendedor'].dropna().unique().tolist()) if not df_atual.empty else ["Todos"]
    vendedor_sel = col3.selectbox("Vendedor", vendedores)

    df_rel = df_atual.copy()
    df_rel['data_venda'] = pd.to_datetime(df_rel['data_venda'], errors='coerce').dt.date

    mask = (
        (df_rel['data_venda'] >= data_inicio) &
        (df_rel['data_venda'] <= data_fim)
    )
    if vendedor_sel != "Todos":
        mask &= (df_rel['vendedor'] == vendedor_sel)

    df_filt = df_rel[mask].copy()

    if not df_filt.empty:
        col_a, col_b, col_c, col_d = st.columns(4)
        total_vendas = df_filt['total_venda'].sum()
        total_comissoes = df_filt['valor_comissao'].sum()
        qtd_vendas = len(df_filt)
        media_venda = df_filt['total_venda'].mean()

        col_a.metric("💰 Total Vendas", f"R$ {total_vendas:,.2f}")
        col_b.metric("🏆 Total Comissões", f"R$ {total_comissoes:,.2f}")
        col_c.metric("📦 Qtd. Vendas", qtd_vendas)
        col_d.metric("📈 Média/Venda", f"R$ {media_venda:,.2f}")

        st.dataframe(df_filt, use_container_width=True)
    else:
        st.info("📭 Nenhum dado encontrado para os filtros selecionados.")

st.sidebar.info("👨‍💻 Desenvolvido com Streamlit + Supabase")
