import streamlit as st
from ui.settings import settings
from core.router import Router
from config import config

st.title('AOGx-Council')

settings_button = st.button('Pengaturan')
if settings_button:
    settings()