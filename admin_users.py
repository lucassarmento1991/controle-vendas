import streamlit as st
import hashlib
from supabase import create_client

# Configuração do Supabase usando secrets
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
supabase: create_client = create_client(url, key)

st.title("🛡️ Gestão de Usuários - Supabase")

# Inputs
username = st.text_input("Novo Username:")
password = st.text_input("Nova Senha:", type="password")

col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Inserir Usuário"):
        if username and password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            data = {
                "username": username,
                "password_hash": password_hash,
                "role": "user"
            }
            result = supabase.table("usuarios").insert(data).execute()
            if result.data:
                st.success(f"✅ Usuário '{username}' inserido com sucesso!")
                st.info(f"Hash gerado: `{password_hash}`")
                st.rerun()
            else:
                st.error("❌ Erro ao inserir usuário. Verifique se o username já existe.")
        else:
            st.warning("⚠️ Preencha username e senha.")

with col2:
    if st.button("📋 Listar Usuários Atuais"):
        try:
            response = supabase.table("usuarios").select("*")("order", "username").execute()
            if response.data:
                st.subheader("Usuários cadastrados:")
                for user in response.data:
                    st.write(f"- **{user['username']}** (Role: {user['role']})")
                # st.json(response.data)  # Descomente para ver hashes
            else:
                st.info("Nenhum usuário cadastrado.")
        except Exception as e:
            st.error(f"Erro ao listar: {str(e)}")
