import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import plotly.express as px
from datetime import datetime

# Função para obter conexão com o banco de dados
# Retorna uma conexão SQLite local
def get_db_connection():
    conn = sqlite3.connect('vendas.db')
    return conn

# Função para inicializar o banco de dados
# Cria tabelas se não existirem, incluindo admin se vazio
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Criar tabela vendas com todos os campos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estabelecimento TEXT,
            data_venda TEXT,
            bairro TEXT,
            forma_pagamento TEXT,
            produto TEXT,
            quantidade INTEGER,
            valor_produto REAL,
            total_venda REAL,
            comissao_percentual REAL,
            valor_comissao REAL,
            status TEXT DEFAULT 'ativa'
        )
    ''')
    
    # Criar tabela users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT DEFAULT 'user'
        )
    ''')
    
    # Verificar se admin existe, se não, criar
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed = hash_password('123456')
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", ('admin', hashed, 'admin'))
    
    conn.commit()
    conn.close()

# Função para hash de senha
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Função para verificar login
def check_login(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed = hash_password(password)
    cursor.execute("SELECT role FROM users WHERE username = ? AND password_hash = ?", (username, hashed))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Função para obter vendas ativas
def get_vendas_ativas():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM vendas WHERE status = 'ativa' ORDER BY id DESC", conn)
    conn.close()
    return df

# Função para cancelar venda
def cancelar_venda(venda_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE vendas SET status = 'cancelada' WHERE id = ?", (venda_id,))
    conn.commit()
    conn.close()

# Função para obter usuários
def get_users():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT id, username, role FROM users", conn)
    conn.close()
    return df

# Função para adicionar usuário
def add_user(username, password, role):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed = hash_password(password)
    try:
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, hashed, role))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

# Função para deletar usuário
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# Função para adicionar venda
def add_venda(estabelecimento, data_venda, bairro, forma_pagamento, produto, quantidade, valor_produto, comissao_percentual):
    total_venda = quantidade * valor_produto
    valor_comissao = total_venda * (comissao_percentual / 100)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO vendas (estabelecimento, data_venda, bairro, forma_pagamento, produto, quantidade, valor_produto, total_venda, comissao_percentual, valor_comissao, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (estabelecimento, data_venda, bairro, forma_pagamento, produto, quantidade, valor_produto, total_venda, comissao_percentual, valor_comissao, 'ativa'))
    conn.commit()
    conn.close()

# Inicializar banco de dados
init_db()

# Interface do Streamlit
st.title("Sistema de Vendas")

# Login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

if not st.session_state.logged_in:
    st.subheader("Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        role = check_login(username, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = role
            st.rerun()
        else:
            st.error("Credenciais inválidas")
else:
    st.sidebar.write(f"Logado como: {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.rerun()
    
    # Sidebar menu
    menu = ["Adicionar Venda", "Listar Vendas", "Relatórios"]
    if st.session_state.role == 'admin':
        menu.append("Gerenciar Usuários")
    choice = st.sidebar.radio("Menu", menu)
    
    if choice == "Adicionar Venda":
        st.subheader("Adicionar Venda")
        col1, col2 = st.columns(2)
        with col1:
            estabelecimento = st.selectbox("Estabelecimento", ["Loja A", "Loja B", "Loja C"])
            data_venda = st.date_input("Data da Venda", datetime.today())
            bairro = st.text_input("Bairro")
            forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Cartão", "Pix"])
        with col2:
            produto = st.text_input("Produto")
            quantidade = st.number_input("Quantidade", min_value=1, value=1)
            valor_produto = st.number_input("Valor do Produto", min_value=0.01, value=0.01, step=0.01)
            comissao_percentual = st.number_input("Comissão Percentual", min_value=0.0, value=0.0, step=0.1)
        
        total_venda = quantidade * valor_produto
        valor_comissao = total_venda * (comissao_percentual / 100)
        st.write(f"**Total de Venda: R$ {total_venda:.2f}**")
        st.write(f"**Valor da Comissão: R$ {valor_comissao:.2f}**")
        
        if st.button("Adicionar"):
            if not bairro or not produto:
                st.error("Bairro e Produto são obrigatórios")
            else:
                add_venda(estabelecimento, str(data_venda), bairro, forma_pagamento, produto, quantidade, valor_produto, comissao_percentual)
                st.success("Venda adicionada com sucesso!")
                st.rerun()
    
    elif choice == "Listar Vendas":
        st.subheader("Listar Vendas")
        df = get_vendas_ativas()
        col1, col2 = st.columns(2)
        with col1:
            data_filtro = st.date_input("Data a partir de", datetime.today())
        with col2:
            bairro_filtro = st.text_input("Bairro")
        
        # Aplicar filtros
        df_filtrado = df[df['data_venda'] >= str(data_filtro)]
        if bairro_filtro:
            df_filtrado = df_filtrado[df_filtrado['bairro'].str.contains(bairro_filtro, case=False)]
        
        # Paginação
        page_size = st.slider("Itens por página", 5, 50, 10)
        total_pages = len(df_filtrado) // page_size + 1
        page = st.number_input("Página", min_value=1, max_value=total_pages, value=1)
        start = (page - 1) * page_size
        end = start + page_size
        
        st.dataframe(df_filtrado.iloc[start:end])
        
        # Botões cancelar
        for index, row in df_filtrado.iloc[start:end].iterrows():
            if st.button(f"Cancelar Venda {row['id']}", key=f'cancel_{row["id"]}'):
                st.warning(f"Tem certeza que deseja cancelar a venda {row['id']}?")
                if st.button("Confirmar", key=f'confirm_{row["id"]}'):
                    cancelar_venda(row['id'])
                    st.success("Venda cancelada!")
                    st.rerun()
    
    elif choice == "Relatórios":
        st.subheader("Relatórios")
        df = get_vendas_ativas()
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data Início")
        with col2:
            data_fim = st.date_input("Data Fim")
        
        df_filtrado = df[(df['data_venda'] >= str(data_inicio)) & (df['data_venda'] <= str(data_fim))]
        
        total_vendas = df_filtrado['total_venda'].sum()
        total_comissao = df_filtrado['valor_comissao'].sum()
        st.write(f"**Total de Vendas: R$ {total_vendas:.2f}**")
        st.write(f"**Total de Comissão: R$ {total_comissao:.2f}**")
        
        # Gráfico
        fig = px.bar(df_filtrado.groupby(['bairro', 'produto'])['total_venda'].sum().reset_index(), x='bairro', y='total_venda', color='produto', title="Vendas por Bairro e Produto")
        st.plotly_chart(fig)
        
        # Download CSV
        csv = df_filtrado.to_csv(index=False)
        st.download_button("Baixar CSV", csv, "relatorio.csv", "text/csv")
    
    elif choice == "Gerenciar Usuários" and st.session_state.role == 'admin':
        st.subheader("Gerenciar Usuários")
        df_users = get_users()
        st.dataframe(df_users)
        
        st.subheader("Adicionar Usuário")
        new_username = st.text_input("Novo Usuário")
        new_password = st.text_input("Senha", type="password")
        new_role = st.selectbox("Papel", ["user", "admin"])
        if st.button("Adicionar Usuário"):
            if add_user(new_username, new_password, new_role):
                st.success("Usuário adicionado!")
                st.rerun()
            else:
                st.error("Usuário já existe")
        
        st.subheader("Deletar Usuário")
        user_to_delete = st.selectbox("Selecionar Usuário para Deletar", df_users['username'].tolist())
        if st.button("Deletar Usuário"):
            user_id = df_users[df_users['username'] == user_to_delete]['id'].values[0]
            delete_user(user_id)
            st.success("Usuário deletado!")
            st.rerun()