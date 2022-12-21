
import streamlit as st
import streamlit.components.v1 as components
import youtube_dl
import urllib

from nightcorei import download_song,yt_factory,create_video
st.set_page_config(page_title="nightcorerify-app",page_icon=None,layout="wide")


# Always use this sample rate for audio
AUDIO_SAMPLE_RATE = 44100
# Download the original audio as this
AUDIO_FILE_FORMAT = 'mp3'
# Speed up the audio by this much to create the nightcore effect
SPEED_FACTOR = 1.265
# Use mpegts because ffmpeg encodes it quickly and it's designed to be written to stdout
VIDEO_MIME = 'video/MP2T'
CONTAINER_FORMAT = 'mpegts'
REQ_HEADERS = {
    'User-Agent': 'nightcoreify:2.1 '}
# Description to use when uploading to YouTube
YT_DESC = "This nightcore remix was automatically generated by a bot!"

st.write("hello world")
video_url = st.text_input('Paste a youtube URL below')

if video_url:
    # download_song(s_id, YT_URL)
    videocont, pad = st.columns(2)
    with videocont:
        st.video(video_url) 
    if st.button('Nightcorerify it'):
        st.write('Why hello there')

    
        dl_opts = {
                # ytdl can encode the downloaded audio at a specific sample rate
                'format': 'bestaudio[asr=%d]' % AUDIO_SAMPLE_RATE,
                'postprocessors': [{
                    # also, it can create an audio file in whatever format on its own
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': AUDIO_FILE_FORMAT,
                }],
                'audioformat': AUDIO_FILE_FORMAT,
                'outtmpl': "temp.wav",#file_template,
                'noplaylist': True,  # sanity
                'nooverwrites': False,  # sanity
                'cachedir': False,  # ytdl tries to write to ~ which is read-only in lambda
            }

        with youtube_dl.YoutubeDL(dl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            video_url = info_dict.get("url", None)
            video_id = info_dict.get("id", None)
            video_title = info_dict.get('title', None)
            ydl.download([video_id])

        st.write("You selected: ", video_title)

    # (id, title, tags)
        img_url="https://www.publicdomainpictures.net/pictures/300000/velka/abstract-wallpaper-15572324177B2.jpg"
        img_dimensions= (1920 ,1285 )
        img_path="img.jpg"
        with urllib.request.urlopen(urllib.request.Request(img_url, headers=REQ_HEADERS)) as res, open(img_path, 'wb') as file:
            file.write(res.read())

        newAudio = create_video( video_id, str(img_path), img_dimensions)
        st.write('ready')
        st.audio(newAudio, format='audio/ogg')

