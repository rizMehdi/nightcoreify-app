import json
import subprocess
import traceback
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
from youtube_dl import YoutubeDL
from datetime import timedelta
from urllib import parse, request
from pathlib import Path
from os import getenv
from uuid import uuid4
from random import choice
from html import unescape
from posixpath import basename
from tempfile import mkdtemp
from time import sleep
from shutil import rmtree

YT_URL = 'https://youtu.be'
REDDIT_URL = 'https://www.reddit.com'
YT_CATEGORY = 10  # music, not like it even matters
# Subreddits to pull img from, name appropriate
M_LADY = ('awwnime', 'Moescape', 'Moescene', 'headpats', 'AnimeBlush', 'Melanime', 'MoeStash', 'TwoDeeArt', 'Patchuu')
# Use the more volatile 'sort by' methods on Reddit to avoid selecting the same image twice.
REDDIT_SORT = ('controversial', 'rising', 'new')
# Log this whenever we filter a video or Reddit post
FILTERED = 'is sus!'
# Don't use videos that are too long (7 minutes)
MAX_VID_LENGTH = 420
# Always use this sample rate for audio
AUDIO_SAMPLE_RATE = 44100
# Speed up the audio by this much to create the nightcore effect
SPEED_FACTOR = 1.265
# I use mpegts because ffmpeg encodes it quickly and it's designed to be written to stdout.
VIDEO_MIME = 'video/MP2T'
CONTAINER_FORMAT = 'mpegts'
# When making http requests, use these headers. UA is required for Reddit
REQ_HEADERS = {
    'User-Agent': 'nightcoreify:2.1 (https://github.com/intrlocutr/nightcoreify)'}
# Description to use when uploading to YouTube
YT_DESC = "This nightcore remix was automatically generated by a bot! Subscribe for more randomly generated " \
          "nightcore.\n\nOriginal song: %(vid_url)s\nImage: %(img_url)s\nI don't own any of the content used here. " \
          "Please contact my administrator at the email in my channel description if you're the owner of this content" \
          " and you'd like it taken down."


def retry(func):
    """Tries the wrapped function up to 3 times,
    in between a delay starting with 3 seconds and multiplying by 2 each time."""

    def inner(*args, **kwargs):
        timeout = 3
        runs = 3
        for n in range(runs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                traceback.print_exc()
                if n < runs - 1:
                    print('Retrying in %d seconds...' % timeout)
                    sleep(timeout)
                    timeout *= 2
                else:
                    print('Giving up.')
                    raise e

    return inner


def main(event=None, context=None):
    """The function that does the things."""

    if event is None and context is None:
        # For local testing only
        from dotenv import load_dotenv
        load_dotenv()
    # The YT credentials will be stored in JSON format in an environment variable.
    credentials = json.loads(getenv('YT_TOKEN'))

    # A temporary directory where we'll store the original song and image.
    tmp_dir = Path(mkdtemp(prefix='nightcoreify'))

    print('Attempting YouTube authentication')
    # Create a YouTube API client
    youtube = googleapiclient.discovery.build(
        'youtube', 'v3', credentials=Credentials(None, **credentials), cache_discovery=False)

    img_path, img_perma, img_dimensions = random_image(tmp_dir)
    s_id, s_title, s_tags = random_song(youtube)

    audio_file_template = str(tmp_dir / '%(id)s.%(ext)s')
    audio_format = 'mp3'
    dl_opts = {
        # ytdl can encode the downloaded audio at a specific sample rate
        'format': 'bestaudio[asr=%d]' % AUDIO_SAMPLE_RATE,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format,
        }],
        'audioformat': audio_format,
        'outtmpl': audio_file_template,
        'noplaylist': True,  # sanity
        'nooverwrites': False,  # sanity
        'cachedir': False,  # ytdl tries to write to ~ which is read-only in lambda
    }

    with YoutubeDL(dl_opts) as ytdl:
        ytdl.download([s_id])
    print('Original song downloaded')

    video = create_video(Path(audio_file_template % {
        'id': s_id, 'ext': audio_format}), img_path, img_dimensions)

    # For testing
    """with open(tmp_dir / 'out.ts', 'wb') as v:
        v.write(video.getvalue())"""

    res = upload_video(video, s_tags, s_title, YT_DESC % {
        'vid_url': parse.urljoin(YT_URL, s_id), 'img_url': img_perma}, youtube)
    del video
    print('Response from YouTube:', json.dumps(res, indent=None))

    print('Cleaning up')
    rmtree(tmp_dir, ignore_errors=True)


@retry
def random_image(to_dir: Path) -> tuple:
    """Finds and downloads a random image, and saves it to the directory `to_dir` (`Path`). Returns a 3-tuple (`Path` to
    saved image, permalink, (width, height))."""

    # Get json w/ random sorting method of random subreddit
    reddit_json_url = parse.urljoin(REDDIT_URL, 'r/%s/%s.json' %
                                    (choice(M_LADY), choice(REDDIT_SORT)))
    print('Reddit, do your thing!!1! Load', reddit_json_url)
    with request.urlopen(request.Request(reddit_json_url, headers=REQ_HEADERS)) as res:
        data = json.load(res)

    if data.get('error') is not None:
        raise Exception('Error %d from Reddit' % data['error'])

    initial_posts = len(data['data']['children'])
    print('Got %d posts' % initial_posts)
    if initial_posts < 1:
        raise Exception('No posts found.')
    del initial_posts

    def post_filter(post):
        """Filter out posts not matching these criteria:

        - Is an image
        - Is not NSFW
        - Is not a GIF"""
        ret = post['data'].get('post_hint') == 'image' and not post['data'].get(
            'over_18') and '.gif' not in post['data']['url'].lower()
        if not ret:
            print(post['data'].get('name'), FILTERED)
        return ret

    posts = list(filter(post_filter, data['data']['children']))
    num_posts = len(posts)
    print('After filtering results, %d remain' % num_posts)
    if num_posts < 1:
        raise Exception('No suitable posts found.')
    del num_posts

    my_pic = choice(posts)
    permalink = parse.urljoin(REDDIT_URL, my_pic['data']['permalink'])
    pic_url = my_pic['data']['url']
    # Create a Path to the image from its base file name in the url we are about to download it from.
    pic_path = to_dir / Path(basename(parse.urlsplit(pic_url).path))
    dimensions = (my_pic['data']['preview']['images'][0]['source']['width'],
                  my_pic['data']['preview']['images'][0]['source']['height'])

    print('Selected image', permalink)
    print('Load', pic_url)

    with request.urlopen(request.Request(pic_url, headers=REQ_HEADERS)) as res, open(pic_path, 'wb') as file:
        file.write(res.read())

    return pic_path, permalink, dimensions


@retry
def random_song(youtube: googleapiclient.discovery.Resource) -> tuple:
    """Finds a random song on `youtube`. Returns a 3-tuple (id, title, tags)."""

    # From what I've found, "v=XXXX" will return videos whose ID matches XXXX, or a whose title closely matches
    # that string, but the former is more common. Basically, we are at the mercy of the YouTube algorithm.
    # "-nightcore" makes sure we don't find any existing nightcore.
    # The random "ID" is the first 4 characters of a UUID4. Any more than 4 characters tends to return less videos.
    q = 'v=%s -nightcore' % str(uuid4())[:4]
    print('Search for', q)
    req_vid = youtube.search().list(
        part='snippet',
        maxResults=50,
        q=q,
        type='video',
        videoCategoryId=YT_CATEGORY
    )
    res_vid = req_vid.execute()
    res_len = len(res_vid['items'])
    print('Got %d videos' % res_len)
    if res_len < 1:
        raise Exception('No videos found.')
    del res_len

    req_det = youtube.videos().list(
        # gets tags and duration of the videos returned by previous search
        part='snippet,contentDetails',
        id=','.join(vid['id']['videoId'] for vid in res_vid['items'])
    )
    res_det = req_det.execute()

    def vid_filter(item):
        """Filter out videos not matching these criteria:

        - Video must not be longer than `MAX_VID_LENGTH`"""
        ret = parse_isoduration(item['contentDetails']['duration']) <= MAX_VID_LENGTH
        if not ret:
            print(item['id'], FILTERED)
        return ret

    items_det = list(filter(vid_filter, res_det['items']))
    filtered = len(items_det)
    print('After filtering videos, %d remain' % filtered)
    if filtered < 1:
        raise Exception('No suitable videos found.')
    del filtered

    my_choice = choice(items_det)
    v_id = my_choice['id']
    print(v_id, 'it is!')
    title = unescape(my_choice['snippet']['title'])

    tags = my_choice['snippet'].get('tags')
    if tags:
        tags = list(unescape(tag) for tag in tags)
    else:
        tags = list()

    return v_id, title, tags


def create_video(audio_file: Path, img_path: Path, img_dimensions: tuple) -> BytesIO:
    """Creates a new nightcore video from the unprocessed audio file at `audio_file` and the image file at `img_path`.
    `img_dimensions` must be a 2-tuple (width, height). Returns the new video."""

    # Height of the waves will be 25% of the height of the image rounded to the nearest integer.
    # In this formula we account for the scaling of the image to width 1280 retaining aspect ratio.
    waves_height = round(img_dimensions[1] / img_dimensions[0] * 1280 * 0.25)

    cmd = [
        getenv('FFMPEG_BIN', 'ffmpeg'),
        # Loop the...
        '-loop', '1',
        # ...image...
        '-i', str(img_path),
        '-i', str(audio_file),
        # ...until the shortest stream (i.e., the audio) ends
        '-shortest',
        '-filter_complex',
                    # Scale the input image (keeping aspect ratio) to width 1280 and nearest even height (-2);
                    # even dimensions are required by the encoder
                    '[0:v]scale=1280:-2[i];' +
                    # Increase the sample rate of the audio (to increase pitch & tempo),
                    # resample at original rate (sanity measure), split to 2 streams
                    '[1:a]asetrate={rate}*{speed},aresample={rate},asplit[a][a_waves];'.format(
                        rate=AUDIO_SAMPLE_RATE, speed=SPEED_FACTOR) +
                    # One of the audio streams will be used for generating the waveform here,
                    # other is for final output.
                    '[a_waves]showwaves=size=1280x%i:mode=cline:colors=Black[waves];' % waves_height +
                    # Overlay waveform on original image. Also make final duration as short as possible.
                    '[i][waves]overlay=x=(W-w):y=(H-h):shortest=1',
        # Use this audio stream for the output
        '-map', '[a]',
        # Default audio codec for mpegts is mp2 (bleh)
        '-c:a', 'mp3',
        # Setting the pixel format is more of a sanity measure for YouTube
        '-pix_fmt', 'yuv420p',
        # We need to explicity set the container because the final contents are being written to stdout
        '-f', CONTAINER_FORMAT,
        # Write to stdout
        '-',
    ]

    # Log the ffmpeg command for debugging
    print('ffmpeg command:', ' '.join(cmd))
    ffmpeg = subprocess.run(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    # ffmpeg logs to stderr
    print(ffmpeg.stderr.decode('utf-8'))

    vid_size = len(ffmpeg.stdout)
    print('Encoding done, new video is %d bytes' % vid_size)
    if vid_size > 0:
        return BytesIO(ffmpeg.stdout)
    else:
        raise Exception('Video is blank.')


def upload_video(video: BytesIO, o_tags: list, title: str, desc: str, youtube: googleapiclient.discovery.Resource):
    """Uploads the video, returns response from `youtube` service."""

    title = title.strip()
    tags = create_tags(o_tags)

    body = {
        'snippet': {
            'title': truncate('Nightcore - ' + title, 100),
            'description': desc,
            'tags': tags,
            'categoryId': YT_CATEGORY
        },
        'status': {
            'privacyStatus': 'public'
        }
    }
    req = youtube.videos().insert(
        part=','.join(body.keys()) + ',id',
        body=body,
        media_body=MediaIoBaseUpload(
            video, VIDEO_MIME, chunksize=1024 * 1024, resumable=True),
    )
    return req.execute()


def create_tags(tags: list) -> list:
    """Prepares tags for a new upload. Keeps as many old tags as possible while adding a "nightcore" tag."""

    to_add = 'nightcore'
    # The total number of characters in YouTube video tags can't exceed 400.
    # We're adding the "nightcore" tag, so we'll only keep this many characters of the original tags.
    target_len = 400 - len(to_add)

    new_tags = []
    length = 0
    # Keep tags up until they can no longer fit within our target.
    for tag in tags:
        length += len(tag)
        if length < target_len:
            new_tags.append(tag)
        else:
            break

    new_tags.append(to_add)

    return new_tags


def parse_isoduration(s: str) -> int:
    """Converts ISO 8601 duration to seconds."""
    # Borrowed code from https://stackoverflow.com/a/64232786

    # Remove prefix
    s = s.split('P')[-1]

    def get_isosplit(t, split):
        if split in t:
            n, t = t.split(split)
        else:
            n = 0
        return n, t

    # Step through letter dividers
    days, s = get_isosplit(s, 'D')
    _, s = get_isosplit(s, 'T')
    hours, s = get_isosplit(s, 'H')
    minutes, s = get_isosplit(s, 'M')
    seconds, s = get_isosplit(s, 'S')

    # Convert all to seconds
    dt = timedelta(days=int(days), hours=int(hours),
                   minutes=int(minutes), seconds=int(seconds))
    return int(dt.total_seconds())


def truncate(s, length: int):
    """Truncates sequence `s` to length `l`."""

    return s[:length] if len(s) > length else s


if __name__ == '__main__':
    main()
