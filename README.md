# nightcoreify

Simple(ish) node script that:

- finds and downloads a random (kinda) song from YouTube
- finds and downloads a random image from the recommended page on Pixiv
- uses ffmpeg to encode the video and image into an mp4 with a histogram
- increases the audio sample rate by 26.5% (nightcore!)
- uploads the finished product to YouTube

I currently have this script running in an AWS Lambda function, scheduled with a CloudWatch rule, and uploading [here](https://www.youtube.com/channel/UChMRsMd8YxgwztGrQMG44CQ) every 6 hours.

### Clarification on "random" YouTube videos

There's no easy way to find a totally random video on YouTube, much less one belonging to a certain category (music in my case), at least that I can find. So what the script does is generate a 4-character string, add `v=` to the beginning, add `-nightcore` to the end so it doesn't nightcore any pre-existing nightcore, and search for it in the music category. What this does is return a bunch of videos with that 4-character string in the name, or with that string at the beginning of their ID (hence the `v=`). Definitely not random, but this is the best method I can think of with what I have.