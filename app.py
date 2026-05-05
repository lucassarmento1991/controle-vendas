import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

def load_sheets():
    """Load and authorize Google Sheets client with cleaned credentials."""
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    gc = gspread.authorize(creds)
    return gc

# Example Streamlit app
st.title("Google Sheets Demo App")

try:
    gc = load_sheets()
    st.success("✅ Google Sheets client loaded successfully!")
    
    # Example: List sheet names (replace with your sheet ID or name)
    # sheets = gc.list_spreadsheet_files()
    # st.write("Available spreadsheets:", sheets)
    
except Exception as e:
    st.error(f"❌ Error loading sheets: {str(e)}")