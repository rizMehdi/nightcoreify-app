# nightcoreify

Simple(ish) node script that:

- finds and downloads a random song from YouTube
- finds and downloads a random image from Pixiv
- uses ffmpeg to encode the video and image into an mp4
- increases the audio sample rate by 26.5% (nightcore!)
- uploads the finished product to YouTube

It's currently running in an AWS Lambda function, scheduled with a CloudWatch rule, and uploads [here](https://www.youtube.com/channel/UChMRsMd8YxgwztGrQMG44CQ).