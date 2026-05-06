import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from supabase import create_client, Client
from datetime import date, datetime

# 1. INICIALIZAÇÃO DO SUPABASE
st.set_page_config(page_title="Controle de Vendas", layout="wide", page_icon="📊")

@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"].strip()
        key = st.secrets["supabase"]["key"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro de Conexão: Verifique os Secrets. {str(e)}")
        st.stop()

supabase: Client = init_supabase()

# 2. AUTENTICAÇÃO (Sincronizada com o seu Hash do Banco)
def hash_password(password):
    # Gera o hash SHA-256 padrão
    return hashlib.sha256(password.