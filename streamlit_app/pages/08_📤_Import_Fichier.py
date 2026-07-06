"""Page en développement"""
import streamlit as st
from streamlit_app.auth.simple_auth import check_authentication, show_login_page, show_user_info_sidebar

st.set_page_config(page_title="Page", page_icon="⚙️", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()

st.title("Import Fichier")
st.info("🚧 Page en cours de développement")