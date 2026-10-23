import streamlit as st
from config import QUALITY_THRESHOLD, MAX_QUESTION_CHARS, MAX_REQUESTS_PER_SESSION

st.title('Pengaturan')
st.write('Pengaturan aplikasi')

with st.form('pengaturan'):
    col1, col2 = st.columns(2)
    with col1:
        quality_threshold = st.number_input('Ambang Kualitas', min_value=0.0, max_value=1.0, value=QUALITY_THRESHOLD)
    with col2:
        max_question_chars = st.number_input('Maks Karakter Pertanyaan', min_value=1, value=MAX_QUESTION_CHARS)
    col1, col2 = st.columns(2)
    with col1:
        max_requests_per_session = st.number_input('Maks Permintaan per Sesi', min_value=1, value=MAX_REQUESTS_PER_SESSION)
    submit_button = st.form_submit_button(label='Simpan')