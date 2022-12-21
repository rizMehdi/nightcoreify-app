# nightcoreify

[Nightcore](https://en.wikipedia.org/wiki/Nightcore) is mind-numbingly simple. It's just a speed-shift of a pre-existing track, with anime artwork and a visualizer slapped on top. The harsh reality is, we are wasting human minds on the creation of such low-effort "music."

This is the streamlit app for nightcoreify.

It works as following:
- Paste a URL for a song from YouTube
- finds and downloads a random anime artwork from USplash
<> - finds and downloads a random anime artwork from Reddit - I broke tradition and went with Reddit rather than Pixiv because their API is so much friendlier.
- Render a new video, using FFmpeg, with sped up audio + image + audio visualizer
- Uploads the finished product to YouTube

<> I currently have this script running in an [AWS Lambda](https://aws.amazon.com/lambda/) function, scheduled with an [EventBridge (https://aws.amazon.com/eventbridge/) rule, and uploading [here](https://youtube.com/c/nightcoreify) every 6 hours. It's deployed on top of [this Lambda layer for FFmpeg](https://github.com/serverlesspub/ffmpeg-aws-lambda-layer).



## Requirements
- Python 3.8
- [`ffmpeg`](https://ffmpeg.org)
- [`google-api-python-client`](https://github.com/googleapis/google-api-python-client) (and subsequently, a YouTube API key with upload privileges)
- [`youtube_dl`](https://github.com/ytdl-org/youtube-dl)


## License

This software is released under a MIT License.
