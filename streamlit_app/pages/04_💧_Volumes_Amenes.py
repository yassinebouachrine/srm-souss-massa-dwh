"""Page 4 : Volumes Amenés"""
import streamlit as st
from streamlit_app.auth.simple_auth import check_authentication, show_login_page, show_user_info_sidebar

st.set_page_config(page_title="Volumes Amenés", page_icon="💧", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()

st.title("💧 Volumes Amenés par Étage")
st.info("🚧 Page en cours de développement - Sera enrichie avec les fonctionnalités complètes")