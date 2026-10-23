import streamlit as st
from config import config

st.title('Pengaturan')
st.write('Halaman pengaturan aplikasi AOGx-Council')

# Tambahkan form untuk mengatur konfigurasi aplikasi
with st.form('pengaturan'):
    # Tambahkan field untuk mengatur mode kedalaman
    mode = st.selectbox('Mode Kedalaman', ['Cepat', 'Seimbang', 'Mendalam'])
    
    # Tambahkan field untuk mengatur ambang kualitas
    quality_threshold = st.slider('Ambang Kualitas', 0.0, 1.0, 0.7)
    
    # Tambahkan tombol untuk menyimpan perubahan
    if st.form_submit_button('Simpan'):
        # Simpan perubahan ke konfigurasi aplikasi
        config.MODES = {'Cepat': {'rounds': 1, 'verify': False, 'max_retries': 0},
                       'Seimbang': {'rounds': 2, 'verify': True, 'max_retries': 1},
                       'Mendalam': {'rounds': 3, 'verify': True, 'max_retries': 2}}
        config.QUALITY_THRESHOLD = quality_threshold
        st.success('Pengaturan berhasil disimpan')