
import streamlit as st
import streamlit.components.v1 as components
import youtube_dl
from nightcorei import download_song,yt_factory
st.set_page_config(page_title="nightcorerify-app",page_icon=None,layout="wide")

st.write("hello world")
video = st.text_input('Paste a youtube URL below')

with YoutubeDL(youtube_dl_opts) as ydl:
      info_dict = ydl.extract_info(video, download=False)
      video_url = info_dict.get("url", None)
      video_id = info_dict.get("id", None)
      video_title = info_dict.get('title', None)

st.write(video_title)
# download_song(s_id, YT_URL)

if st.button('Nightcorerify it'):
    st.write('Why hello there')


