
import streamlit as st
import streamlit.components.v1 as components
st.set_page_config(page_title="nightcorerify-app",page_icon=None,layout="wide")

st.write("hello world")
YT_URL = st.text_input('Paste a youtube URL below')

if st.button('Nightcorerify it'):
    st.write('Why hello there')


