# nightcoreify

Simple Python script that:

- finds and downloads a random (somewhat, see below) song from YouTube
- finds and downloads a random anime artwork from Reddit (Used to be Pixiv, but their API changes so much. I don't think they want 3rd parties using it)
- renders a new video, using FFmpeg, with sped up audio + image + audio histogram
- uploads the finished product to YouTube

I currently have this script running in an AWS Lambda function, scheduled with a CloudWatch rule, and uploading [here](https://www.youtube.com/channel/UChMRsMd8YxgwztGrQMG44CQ) every 6 hours. It's deployed on top of [this Lambda layer for FFmpeg](https://github.com/serverlesspub/ffmpeg-aws-lambda-layer).

### Clarification on "random" YouTube videos

There's no easy way to find a totally random video on YouTube, much less one belonging to a certain category (music in my case), at least that I can find. So what the script does is generate a 4-character string, add `v=` to the beginning, add `-nightcore` to the end so it doesn't nightcore any pre-existing nightcore, and search for it in the music category. This returns a bunch of videos with that 4-character string in the name, or with that string at the beginning of their ID (hence the `v=`). Definitely not random, but this is the best method I can think of with what I have.

Also, thanks Google, for making your API so enormous. ;)

## Stuff to add in the future

- Better way of finding random videos. The current method tends to return a bunch of videos with seemingly random strings as names, and I want actual songs.
- ~~Experiment with FFmpeg options to get a faster encode time. The thought of "experimenting with FFmpeg" is giving me flashbacks.~~ The audio visualizer is what's taking so long. I don't want to get rid of it though, it looks cool.
- Only choose YouTube videos that won't get claimed. This could be achieved by searching through a pre-defined set of royalty free music channels, or somehow getting the "Music in this video" data directly from the YouTube Data API (the presence of that data means YT has the song in their DB and they'll claim it). The reason I'm worried about this is this bot is literally a DMCA bomb of nuclear proportions for me.
- A nicer looking audio visualizer.

## License

This software is released under a BSD Zero Clause License.