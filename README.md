# nightcoreify

Simple(ish) node script that:

- finds and downloads a random (kinda) song from YouTube
- finds and downloads a recommended image from Pixiv
- uses ffmpeg to encode the video and image into an mp4
- increases the audio sample rate by 26.5% (nightcore!)
- uploads the finished product to YouTube

Ok, so there's no easy way to find a totally random video on YouTube, much less one belonging to a certain category (music in my case), at least that I can find. So what I do is generate a 4-character string, add `v=` to the beginning, add `-nightcore` to the end so it doesn't nightcore nightcore, and search for it in the music category. What this does is return a bunch of videos with that 4-character string in the name, or with that string at the beginning of their ID (hence the `v=`). It's by no means random, but YouTube wants to be difficult, so I'll play their game.

I currently have this script running in an AWS Lambda function, scheduled with a CloudWatch rule, and uploading [here](https://www.youtube.com/channel/UChMRsMd8YxgwztGrQMG44CQ) every 6 hours.