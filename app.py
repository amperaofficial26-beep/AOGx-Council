import streamlit as st
from ui.settings import settings

st.title('AOGx-Council')

# Tambahkan tombol untuk mengakses halaman pengaturan
if st.button('Pengaturan'):
    settings()