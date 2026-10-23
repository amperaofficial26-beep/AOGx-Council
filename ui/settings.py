import streamlit as st
from config import config

st.title('Pengaturan')
st.write('Halaman pengaturan untuk aplikasi AOGx-Council')

st.subheader('Mode Kedalaman')
mode = st.selectbox('Pilih mode kedalaman', config.MODES.keys())

st.subheader('Ambang Kualitas')
quality_threshold = st.slider('Ambang kualitas', min_value=0.0, max_value=1.0, value=config.QUALITY_THRESHOLD)

st.subheader('Batas Penggunaan')
max_question_chars = st.slider('Batas karakter pertanyaan', min_value=100, max_value=5000, value=config.MAX_QUESTION_CHARS)
max_requests_per_session = st.slider('Batas permintaan per sesi', min_value=10, max_value=100, value=config.MAX_REQUESTS_PER_SESSION)