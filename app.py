
import streamlit as st
import streamlit.components.v1 as components
import youtube_dl
from nightcorei import download_song,yt_factory
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


st.write("hello world")
video = st.text_input('Paste a youtube URL below')

if video:
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
        info_dict = ydl.extract_info(video, download=False)
        video_url = info_dict.get("url", None)
        video_id = info_dict.get("id", None)
        video_title = info_dict.get('title', None)
        downloadedvideo=ydl.download([video])
   
    st.write("You selected: ", video_title)
    # download_song(s_id, YT_URL)
    videocont, pad = st.columns(2)
    with videocont:
        st.video(video) 


    # img_url="https://www.publicdomainpictures.net/pictures/300000/velka/abstract-wallpaper-15572324177B2.jpg"
    # img_dimensions= (1920 ,1285 )
    # pic_path="img.jpg"
    # with urllib.request.urlopen(urllib.request.Request(pic_url, headers=REQ_HEADERS)) as res, open(pic_path, 'wb') as file:
    #     file.write(res.read())

    # if st.button('Nightcorerify it'):
    #     st.write('Why hello there')
    #     newvideo = create_video( downloadedvideo, str(pic_path), img_dimensions)


