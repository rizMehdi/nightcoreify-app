import json
import subprocess
import traceback
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from youtube_dl import YoutubeDL
from datetime import timedelta
from urllib import parse, request
from pathlib import Path
from re import match
from os import getenv
from uuid import uuid4
from random import choice
from html import unescape
from posixpath import basename
from tempfile import mkdtemp

YT_URL = 'https://youtu.be'
REDDIT_URL = 'https://www.reddit.com'
YT_CATEGORY = 10  # music, not like it even matters
# Subreddits to pull img from, name appropriate
M_LADY = ('awwnime', 'Moescape', 'Moescene', 'headpats', 'AnimeBlush', 'Melanime', 'MoeStash',
          'AnimeSketch', 'TwoDeeArt', 'Patchuu')
# Use the more volatile 'sort by' methods on Reddit to avoid selecting the same image twice.
REDDIT_SORT = ('controversial', 'rising', 'new')
FILTERED = ' is sus!'
MAX_VID_LENGTH = 240
FRAME_RATE = 24
AUDIO_SAMPLE_RATE = 44100
SPEED_FACTOR = 1.265
REQ_HEADERS = {
    'User-Agent': 'nightcoreify:2.1 (https://github.com/intrlocutr/nightcoreify)'}


def main(event=None, context=None):
    """The function that does the things"""

    if event == None:
        # This is for local testing. In AWS, envvars will be set (and encrypted) on the Lambda console.
        from dotenv import load_dotenv
        load_dotenv()
    credentials = json.loads(getenv('YT_TOKEN'))

    tmp_dir = Path(mkdtemp(prefix='nightcoreify'))

    try:
        print('Attempting YouTube authentication')
        youtube = googleapiclient.discovery.build(
            'youtube', 'v3', credentials=Credentials(None, **credentials), cache_discovery=False)

        img_path, img_perma = random_image(tmp_dir)
        s_id, s_title, s_tags = random_song(youtube)

        audio_file_template = str(tmp_dir / '%(id)s.%(ext)s')
        audio_codec = 'wav'
        dl_opts = {
            'format': 'bestaudio[asr=%d]' % AUDIO_SAMPLE_RATE,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_codec,
            }],
            'audioformat': audio_codec,
            'outtmpl': audio_file_template,
            'noplaylist': True,
            'nooverwrites': False,
            'cachedir': False,  # ytdl tries to write to ~ which is read-only in lambda
        }
        out_file = tmp_dir / 'out.mp4'

        with YoutubeDL(dl_opts) as ytdl:
            ytdl.download([s_id])

        print('Video downloaded')

        vid_size = create_video(Path(audio_file_template % {
            'id': s_id, 'ext': audio_codec}), img_path, out_file)
        print('Video size: %d bytes' % vid_size)

        if vid_size > 0:
            desc = "This nightcore remix was automatically generated by a bot! Subscribe for more randomly generated nightcore. " + \
                "\n\nOriginal song: " + parse.urljoin(YT_URL, s_id) + "\nImage: " + img_perma + "\nI don't own any of the content used here. " + \
                "Please contact my Senpai at the email in my channel description if you're the owner of this content and you'd like it taken down."

            res = upload_video(str(out_file), s_tags, s_title, desc, youtube)
            print(str(res))
        else:
            raise FileNotFoundError('A blank file is useless.')

    except:
        traceback.print_exc()
        print('I am done with this cruel world.')
    finally:
        if not getenv('KEEP_TEMP'):
            from shutil import rmtree
            rmtree(tmp_dir, ignore_errors=True)


def random_image(dir: Path) -> tuple:
    """Finds and downloads a random image, and saves it to the directory `dir` (`Path`). Returns a 2-tuple (`Path` to saved image, permalink)"""

    reddit_json_url = parse.urljoin(REDDIT_URL, 'r/%s/%s.json' %
                                    (choice(M_LADY), choice(REDDIT_SORT)))
    print('Reddit, do your thing!!1! Load ' + reddit_json_url)
    with request.urlopen(request.Request(reddit_json_url, headers=REQ_HEADERS)) as res:
        data = json.loads(res.read())

    if data.get('error') is not None:
        raise Exception('Error %d from Reddit' % data['error'])

    print('Got %d posts' % len(data['data']['children']))

    def post_filter(post):
        """Filter out posts not matching these criteria:

        - Is an image
        - Is not NSFW
        - Is not a GIF"""
        ret = post['data'].get('post_hint') == 'image' and not post['data'].get(
            'over_18') and '.gif' not in post['data']['url'].lower()
        if not ret:
            print(post['data'].get('name') + FILTERED)
        return ret
    posts = list(filter(post_filter, data['data']['children']))
    print('After filtering results, %d remain' % len(posts))

    my_pic = choice(posts)
    permalink = parse.urljoin(REDDIT_URL, my_pic['data']['permalink'])
    pic_url = my_pic['data']['url']
    pic_path = dir / Path(basename(parse.urlsplit(pic_url).path))

    print('Selected image ' + permalink)
    print('Load ' + pic_url)

    with request.urlopen(request.Request(pic_url, headers=REQ_HEADERS)) as res, open(pic_path, 'wb') as file:
        file.write(res.read())

    return (pic_path, permalink)


def random_song(youtube: googleapiclient.discovery.Resource) -> tuple:
    """Finds a random song on `youtube`. Returns a 3-tuple (id, title, tags)"""

    q = 'v=%s -nightcore' % str(uuid4())[:4]
    print('Search for ' + q)
    req_vid = youtube.search().list(
        part='snippet',
        maxResults=50,
        q=q,
        type='video',
        videoCategoryId=YT_CATEGORY
    )
    res_vid = req_vid.execute()
    print('Got %d videos' % len(res_vid['items']))

    req_det = youtube.videos().list(
        # gets tags and duration of the videos returned by previous search
        part='snippet,contentDetails',
        id=','.join(vid['id']['videoId'] for vid in res_vid['items'])
    )
    res_det = req_det.execute()

    def vid_filter(item):
        """Filter out videos not matching these criteria:

        - Video must not be longer than `MAX_VID_LENGTH`
        - Uploader channel must not end in " - Topic" as those are instant copyclaims, not like it matters."""
        ret = parse_isoduration(item['contentDetails']['duration']) <= MAX_VID_LENGTH \
            and not match(r'^.* - Topic$', item['snippet']['channelTitle'])
        if not ret:
            print(item['id'] + FILTERED)
        return ret
    items_det = list(filter(vid_filter, res_det['items']))
    print('After filtering videos, %d remain' % len(items_det))

    my_choice = choice(items_det)
    #url = parse.urljoin(YT_URL, my_choice['id'])
    id = my_choice['id']
    print(id + ' it is!')
    title = unescape(my_choice['snippet']['title'])
    tags = list(unescape(tag) for tag in my_choice['snippet'].get('tags', []))

    return (id, title, tags)


def create_video(audio_file: Path, img_path: Path, out_to: Path) -> int:
    """Creates a new nightcore video from the unprocessed audio file at `audio_file` and the image at `img_path`,
    and writes the video to `out_to`. Returns the size of the new video file"""

    cmd = [
        getenv('FFMPEG_BIN', 'ffmpeg'),
        '-loop', '1',
        '-i', str(img_path),
        '-i', str(audio_file),
        '-shortest',
        '-filter_complex',  # Scale the input image (-2 ensures height is even)
                            '[0:v]scale=1280:-2[i];' +
                            # Increase the sample rate of the audio (to increase pitch & tempo),
                            # downsample to original rate (sanity measure), split to 2 streams
                            '[1:a]asetrate={rate}*{speed},aresample={rate},asplit[a][a_waves];'.format(rate=AUDIO_SAMPLE_RATE, speed=SPEED_FACTOR) +
                            # One of the audio streams will be used for generating the waveform,
                            # other is for final output.
                            '[a_waves]showwaves=size=1280x150:mode=cline:r=%d:colors=Black[waves];' % FRAME_RATE +
                            # Overlay waveform on original image. Also make final duration as short as possible.
                            '[i][waves]overlay=x=(W-w):y=(H-h):shortest=1',
        '-map', '[a]',
        '-r', str(FRAME_RATE),
        '-pix_fmt', 'yuv420p',
        '-preset', 'ultrafast',
        '-y',
        str(out_to)
    ]
    # touch the file we are outputting to so if ffmpeg throws a fit, at least we'll know because the size will be 0.
    # depending on when error is thrown ffmpeg may or may not create a blank file
    out_to.touch()
    print('ffmpeg command: ' + ' '.join(cmd))
    # Will write to stderr, which is where ffmpeg logs to.
    ffmpeg = subprocess.Popen(cmd, shell=False)
    ffmpeg.communicate()
    print('encoding done')

    return out_to.stat().st_size


def upload_video(vid_path: str, o_tags: list, title: str, desc: str, youtube: googleapiclient.discovery.Resource):
    """Uploads the video"""

    title = title.strip()
    tags = create_tags(o_tags, title)

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
    print(json.dumps(body, indent=None))
    req = youtube.videos().insert(
        part=','.join(body.keys()) + ',id',
        body=body,
        media_body=MediaFileUpload(vid_path),

    )
    return req.execute()


def create_tags(o_tags: list, title: str) -> list:
    """Prepares tags for a new upload"""

    # Use a set to remove duplicates
    tags_set = set(tag.strip().lower() for tag in o_tags)
    tags_set.add('nightcore')
    if len(title) <= 30:
        tags_set.add(title.lower())
    tags = []
    length = 0
    for tag in tags_set:
        length += len(tag)
        if length < 400:
            tags.append(tag)
        else:
            break

    return tags


def parse_isoduration(s: str) -> int:
    """Converts ISO 8601 duration to seconds"""
    # Borrowed code from https://stackoverflow.com/a/64232786

    # Remove prefix
    s = s.split('P')[-1]

    def get_isosplit(s, split):
        if split in s:
            n, s = s.split(split)
        else:
            n = 0
        return n, s

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


def truncate(s, l: int):
    """Truncates sequence `s` to length `l`"""

    return s[:l] if len(s) > l else s


if __name__ == '__main__':
    main()
