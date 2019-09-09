if (!!(process.env.LAMBDA_TASK_ROOT || false)) { // if we're running in AWS Lambda, set the handler function
    exports.handler = main;
} else {
    main();
}

async function main() {
    require('dotenv').config();
    var fs = require('fs'), decode = require('unescape'), ffmpeg = require('fluent-ffmpeg'), tmp = require('tmp'), mm = require('music-metadata'),
        ytdl = require('ytdl-core'), pixiv = require('pixiv-api-client'), got = require('got'), { google } = require('googleapis');

    var pixivlink = '', timesDlImageCalled = 0, timesGetVideoCalled = 0, video, videotitle = '', service,
        auth, timesDlCalled = 0, img, sampleRate;
    var videos, videoi = 0; // video search results, index in videos array

    var flv = tmp.fileSync({ postfix: '.flv' }), mp4 = tmp.fileSync({ postfix: '.mp4' }),
        mp3 = tmp.fileSync({ postfix: '.mp3' }), jpg = tmp.fileSync({ postfix: '.jpg' });

    try {
        ffmpeg.setFfmpegPath(process.cwd() + '/ffmpeg');
        ytAuth();
        await getImage();
        await dlImage();
        await getVideo();
        await dlVideo();
        await encodeAudio();
        await encodeVideo();
        await uploadVideo();
        flv.removeCallback();
        mp4.removeCallback();
        jpg.removeCallback();
        mp3.removeCallback();
    } catch (err) {
        console.log(err);
        console.log('Self isekai time');
        process.exit(1);
        return;
    }

    function ytAuth() {
        var OAuth2 = google.auth.OAuth2;

        var credentials = JSON.parse(process.env.YT_SECRET);
        var clientSecret = credentials.installed.client_secret;
        var clientId = credentials.installed.client_id;
        var redirectUrl = credentials.installed.redirect_uris[0];
        auth = new OAuth2(clientId, clientSecret, redirectUrl);

        auth.credentials = JSON.parse(process.env.YT_TOKEN);
        service = google.youtube({ version: 'v3', 'auth': auth });
    }

    function getImage() {
        const pix = new pixiv();
        console.log('Finding an image');
        return new Promise((resolve) => {
            pix.login(process.env.PIXIV_USER, process.env.PIXIV_PASS).then(() => {
                pix.illustRecommended().then(json => { // Search recommended
                    var i = 0;
                    img = json.illusts[i].image_urls.large;
                    while (typeof img == 'undefined') { // Look for an image we can actually use
                        i++;
                        img = json.illusts[i].image_urls.large;
                    }
                    console.log('Image id: ' + json.illusts[i].id);
                    console.log('Image url: ' + img);
                    pixivlink = 'https://www.pixiv.net/member_illust.php?mode=medium&illust_id=' + json.illusts[i].id;
                    resolve();
                });
            });
        });
    }

    function dlImage() {
        return new Promise((resolve, reject) => {
            timesDlImageCalled++;
            if (timesDlImageCalled > 3) {
                reject("For some reason the image won't download");
                return;
            }
            const gotStream = got.stream(img, { encoding: null, headers: { Referer: 'http://www.pixiv.net/' } });
            gotStream.on('error', async function (e) {
                console.log('Error downloading image');
                console.log(e);
                await dlImage();
            });

            gotStream.pipe(fs.createWriteStream(jpg.name)).on('close', () => {
                console.log('Downloaded');
                console.log('jpg size: ' + fs.statSync(jpg.name).size);
                resolve();
            });
        });
    }

    function searchVideo(q, maxResults, meOnly) {
        return new Promise((resolve, reject) => {
            var options;
            if (meOnly) {
                options = {
                    auth: auth,
                    part: 'snippet',
                    maxResults: maxResults,
                    q: q,
                    type: 'video',
                    forMine: true
                };
            } else {
                options = {
                    auth: auth,
                    part: 'snippet',
                    maxResults: maxResults,
                    q: q,
                    type: 'video',
                    videoCategoryId: 10
                };
            }
            service.search.list(options, function (err, results) {
                if (err) { // error searching for video
                    reject('The YouTube API returned an error: ' + err);
                    return;
                }
                if (meOnly !== true) { // If we're not searching for our own videos we need to make sure nothing's too long
                    console.log('Looking for videos that are too long');
                    var ids = [];
                    for (var i = 0; i < results.data.items.length; i++) {
                        ids.push(results.data.items[i].id.videoId);
                    }
                    service.videos.list({
                        auth: auth,
                        part: 'contentDetails',
                        id: ids.join(',')
                    }, function (err, results2) {
                        if (err) {
                            reject('The YouTube API returned an error: ' + err);
                            return;
                        }
                        var i = results2.data.items.length, removeids = [];
                        while (i--) {
                            if (parseDuration(results2.data.items[i].contentDetails.duration) > 360) { // longer than 6 minutes
                                console.log(results2.data.items[i].id + ' is way too long');
                                removeids.push(results2.data.items[i].id);
                                results2.data.items.splice(i, 1);
                            }
                        }
                        if (removeids.length > 0) {
                            i = results.data.items.length;
                            while (i--) {
                                if (removeids.indexOf(results.data.items[i].id.videoId) !== -1) {
                                    results.data.items.splice(i, 1);
                                }
                            }
                        }
                        resolve(results.data.items);
                    });
                } else resolve(results.data.items);
            });
        });
    }

    function getVideo() {
        return new Promise(async (resolve, reject) => {
            timesGetVideoCalled++;
            if (timesGetVideoCalled > 5) {
                reject('getVideo called too many times');
                return;
            }
            let results = await searchVideo('v=' + randomid() + ' -nightcore', 50); // find a random video id
            if (results.length == 0) { // none found
                console.log('No videos found.');
                await getVideo(); // try again
            } else {
                video = results[0].id.videoId;
                videos = results;
                console.log('Found video id ' + video);
                findUniqueId();
                async function findUniqueId() { // See if we've uploaded a video with this id in the desc
                    let r = await searchVideo(video, 1, true);
                    if (r.length == 0) {
                        console.log('This is a unique video, I\'ll use this one.');
                        videotitle = decode(videos[videoi].snippet.title);
                        console.log(JSON.stringify(videos[videoi]));
                        resolve();
                    } else {
                        console.log('I\'ve used this one before, trying again.');
                        ++videoi;
                        if (videoi > results.length) {
                            reject("This shouldn't even happen");
                            process.exit(1);
                            return;
                        }
                        video = videos[videoi].id.videoId;
                        findUniqueId();
                    }
                }
            }
        });
    }

    function dlVideo() {
        return new Promise((resolve, reject) => {
            if (timesDlCalled > 3) {
                reject('Download called too many times.');
                return;
            }
            timesDlCalled++;
            ytdl('http://www.youtube.com/watch?v=' + video, { quality: 'highestaudio' }).pipe(fs.createWriteStream(flv.name))
                .on('finish', function () {
                    console.log('Downloaded');
                    console.log('flv size: ' + fs.statSync(flv.name).size);
                    resolve();
                })
                .on('error', async function (err) {
                    console.log(err);
                    await dlVideo();
                });
        });
    }

    function encodeAudio() {
        return new Promise((resolve, reject) => {
            console.log('Encoding to mp3');
            ffmpeg(flv.name)
                .output(mp3.name)
                .on('end', function (stdout) {
                    console.log('Converted to mp3');
                    console.log('mp3 size: ' + fs.statSync(mp3.name).size);
                    console.log(stdout);
                    mm.parseFile(mp3.name, { native: true }).then(metadata => {
                        sampleRate = metadata.format.sampleRate;
                        console.log('mp3 sample rate: ' + sampleRate);
                        resolve();
                    }).catch(err => {
                        reject(err);
                    });
                })
                .on('error', function (err) {
                    reject(err);
                })
                .run();
        });
    }

    function encodeVideo() {
        return new Promise((resolve, reject) => {
            console.log('Encoding to mp4');
            ffmpeg(jpg.name)
                .loop()
                .addInput(mp3.name)
                .videoCodec('libx264')
                .videoFilter('pad=ceil(iw/2)*2:ceil(ih/2)*2')
                .audioCodec('aac')
                .audioFilters('asetrate=' + (sampleRate * 1.265))
                .addOptions([
                    '-tune', 'stillimage',
                    '-pix_fmt', 'yuv420p',
                    '-preset', 'ultrafast',
                    '-shortest',
                ])
                .output(mp4.name)
                .on('end', function (stdout) {
                    console.log('Converted to mp4');
                    console.log('mp4 size: ' + fs.statSync(mp4.name).size);
                    console.log(stdout);
                    resolve();
                })
                .on('error', function (err) {
                    reject(err);
                })
                .run();
        });
    }

    function uploadVideo() {
        return new Promise((resolve, reject) => {
            var options = {
                part: 'id,snippet,status',
                notifySubscribers: true,
                requestBody: {
                    snippet: {
                        title: truncateTitle('Nightcore - ' + videotitle),
                        description: "This nightcore remix was automatically generated by a bot! I don't own any of the content used here.\n\nOriginal song: http://youtu.be/" + video + '\nImage: ' + pixivlink,
                        tags: ['nightcore'],
                        categoryId: 10
                    },
                    status: {
                        privacyStatus: 'public'
                    },
                },
                media: {
                    body: fs.createReadStream(mp4.name)
                },
            };
            console.log(JSON.stringify(options));
            service.videos.insert(
                options, {},
                function (err, res) {
                    if (err) {
                        reject(err);
                        return;
                    } else {
                        console.log(JSON.stringify(res));
                        resolve();
                    }
                });
        });
    }
}

function parseDuration(d) {
    var iso8601DurationRegex = /(-)?P(?:([.,\d]+)Y)?(?:([.,\d]+)M)?(?:([.,\d]+)W)?(?:([.,\d]+)D)?T(?:([.,\d]+)H)?(?:([.,\d]+)M)?(?:([.,\d]+)S)?/;
    var matches = d.match(iso8601DurationRegex);
    return Number(matches[4] === undefined ? 0 : matches[4] * 604800) + // weeks (yes weeks :/)
        Number(matches[5] === undefined ? 0 : matches[5] * 86400) +     // days
        Number(matches[6] === undefined ? 0 : matches[6] * 3600) +      // hours
        Number(matches[7] === undefined ? 0 : matches[7] * 60) +        // minutes
        Number(matches[8] === undefined ? 0 : matches[8]);              // seconds
}

function truncateTitle(s) {
    if (s.length >= 100) {
        return s.substring(0, 97) + '...';
    }
    return s;
}

function randomid() {
    var result = '';
    var characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
    var charactersLength = characters.length;
    for (var i = 0; i < 4; i++) {
        result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }
    return result;
}