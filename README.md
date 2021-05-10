# nightcoreify

## Introduction to the Infinite Nightcore Theorem

![Photorealistic mock-up of the Infinite Nightcore Theorem.](https://i.imgur.com/NeDxKfV.png)

If you are familiar with the concept of [nightcore](https://en.wikipedia.org/wiki/Nightcore), you are more than likely aware of its cut-and-paste nature; such works are nothing more than a heavily glorified speed-shift of a pre-existing track, with anime artwork and a visualizer slapped on top. It is so simple, that we are effectively wasting human minds on the menial task of creating this, shall we say, [modern art](https://en.wikipedia.org/wiki/Comedian_(artwork)). This harsh reality has led me to develop what I have called the _infinite nightcore theorem_, or INT.

At an abstract level, it's based on the (so far, disproven) _[infinite monkey theorem](https://en.wikipedia.org/wiki/Infinite_monkey_theorem)_, or IMT, in that it involves monkeys generating random content, however, this is where the similarities end. I believe the INT to be much more plausible as its domain is severely limited in comparison to the IMT. The INT grants the monkeys only 1) a supply of music content, 2) a supply of anime artwork, 3) a computer with an audio and video editing suite, and 4) a YouTube account with uploading privileges. The subjects (monkeys) will use the computer and two supplies of content to produce nightcore which they will then upload to YouTube. The computer will be locked down through software to ensure nothing but the desired task of producing nightcore can be fulfilled, and the use of macros is encouraged to increase productivity. Learning from the mistakes of the IMT, the monkeys will be under heavy supervision to ensure they do not engage in any task disadvantageous to the goal of producing and uploading nightcore; such tasks include destroying the computer, never or occasionally making any nightcore, creating so much nightcore that YouTube's servers exceed capacity, etc. Breaks from making nightcore are heavily encouraged so the monkeys can engage in more mentally demanding activities, such as mating, which their human counterparts will likely never experience.

This is in stark contrast to the IMT, wherein the monkeys are given a full array of typewriter keys--with zero restrictions on not only what can be typed, but what can be done with the typewriter--and free will. Considering the behavioral characteristics of monkeys, the intended goal of nightcore is, theoretically, more obtainable in a sweatshop-esque environment.

## Proving the theorem

I wish I had the time and money to invest in studying the nightcore abilities of monkeys. This just isn't feasible though.

In the meantime I have written the next best thing, a simple Python script that:

- finds and downloads a random (somewhat, see below) song from YouTube
- finds and downloads a random anime artwork from Reddit (Used to be Pixiv, but their API changes so much. I don't think they want 3rd parties using it)
- renders a new video, using FFmpeg, with sped up audio + image + audio histogram
- uploads the finished product to YouTube

I currently have this script running in an [AWS Lambda](https://aws.amazon.com/lambda/) function, scheduled with an [EventBridge](https://aws.amazon.com/eventbridge/) rule, and uploading [here](https://www.youtube.com/channel/UChMRsMd8YxgwztGrQMG44CQ) every 6 hours. It's deployed on top of [this Lambda layer for FFmpeg](https://github.com/serverlesspub/ffmpeg-aws-lambda-layer).

### Clarification on "random" YouTube videos

There's no easy way to find a totally random video on YouTube, much less one belonging to a certain category (music in my case), at least that I can find. So what the script does is generate a 4-character string, add `v=` to the beginning, add `-nightcore` to the end so it doesn't nightcore any pre-existing nightcore, and search for it in the music category. This returns a bunch of videos with that 4-character string in the name, or with that string at the beginning of their ID (hence the `v=`). Definitely not random, but this is the best method I can think of with what I have.

Also, thanks Google, for making your API so enormous. ;)

## Requirements
- Python 3.8
- [`ffmpeg`](https://ffmpeg.org)
- [`google-api-python-client`](https://github.com/googleapis/google-api-python-client) (and subsequently, a YouTube API key with upload privileges)
- [`youtube_dl`](https://github.com/ytdl-org/youtube-dl)

## Stuff to add in the future

- Better way of finding random videos. The current method tends to return a bunch of videos with seemingly random strings as names, and I want actual songs. Then again, it is [hilarious](https://youtu.be/JgRokRCLVjE) sometimes.
- Only choose YouTube videos that won't get claimed. This could be achieved by searching through a pre-defined set of royalty free music channels, or somehow getting the "Music in this video" data directly from the YouTube Data API (the presence of that data means YT has the song in their DB and they'll claim it). The reason I'm worried about this is this bot is literally a DMCA bomb of nuclear proportions for me.
- A nicer looking audio visualizer.

## License

This software is released under a BSD Zero Clause License.