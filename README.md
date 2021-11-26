# nightcoreify

![This is what most nightcore "artists" look like.](https://i.imgur.com/NeDxKfV.png)

[Nightcore](https://en.wikipedia.org/wiki/Nightcore) is mind-numbingly simple. It's just a speed-shift of a pre-existing track, with anime artwork and a visualizer slapped on top. The harsh reality is, we are wasting human minds on the creation of such low-effort "music." I decided to take matters into my own hands and automate the process. This is a Python script that:

- finds and downloads a random (somewhat, see below) song from YouTube
- finds and downloads a random anime artwork from Reddit
    - I broke tradition and went with Reddit rather than Pixiv because their API is so much friendlier.
- renders a new video, using FFmpeg, with sped up audio + image + audio visualizer
- uploads the finished product to YouTube

I currently have this script running in an [AWS Lambda](https://aws.amazon.com/lambda/) function, scheduled with an [EventBridge](https://aws.amazon.com/eventbridge/) rule, and uploading [here](https://youtube.com/c/nightcoreify) every 6 hours. It's deployed on top of [this Lambda layer for FFmpeg](https://github.com/serverlesspub/ffmpeg-aws-lambda-layer).

### Clarification on "random" YouTube videos

There's no easy way to find a totally random video on YouTube, much less one belonging to a certain category (music in my case), at least that I can find. So what the script does is generate a 4-character string, add `v=` to the beginning, add `-nightcore` to the end so it doesn't nightcore any pre-existing nightcore, and search for it in the music category. This returns a bunch of videos with that 4-character string in the name, or with that string at the beginning of their ID (hence the `v=`). Definitely not random, but this is the best method I can think of with what I have.

## Requirements
- Python 3.8
- [`ffmpeg`](https://ffmpeg.org)
- [`google-api-python-client`](https://github.com/googleapis/google-api-python-client) (and subsequently, a YouTube API key with upload privileges)
- [`youtube_dl`](https://github.com/ytdl-org/youtube-dl)

Side note: if you dig through the commits in this repo, you'll find that this used to be a Node.js script. I originally wrote it in Node to keep my options open in terms of cloud providers, but rewrote it in Python after I was sure I'd stick with Lambda--and good riddance! Node sucks!

## License

This software is released under a BSD Zero Clause License, mostly because I want you to be able to rip off my FFmpeg command. FFmpeg is cool, but it's really annoying to get it to work the way you want it to. Hopefully the hours of hair-pulling that went into writing that command can be useful to someone else as well.