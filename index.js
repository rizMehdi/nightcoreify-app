if (!!(process.env.LAMBDA_TASK_ROOT || false)) { // if we're running in AWS Lambda, set the handler
    exports.handler = main;
} else {
    main();
}

async function main() {
    require('dotenv').config();
    var fs = require('fs'), decode = require('unescape'), ffmpeg = require('fluent-ffmpeg'), tmp = require('tmp'), mm = require('music-metadata'),
        ytdl = require('ytdl-core'), pixiv = require('pixiv-api-client'), got = require('got'), { google } = require('googleapis');

    var pixivlink = '', timesDlImageCalled = 0, video, videotitle = '', service,
        auth, timesDlCalled = 0, img, sampleRate, ogtags;
    var videos, videoi; // video search results, index in videos array

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
        return new Promise((resolve, reject) => {
            pix.login(process.env.PIXIV_USER, process.env.PIXIV_PASS).then(() => {
                console.log('Logged into pixiv');
                pix.illustRecommended().then(json => { // Search recommended
                    var attempts = 0;
                    do { // Look for an image we can actually use
                        i = random(json.illusts.length);
                        attempts++;
                        if (attempts == json.illusts.length) {
                            reject('No valid images!');
                            return;
                        }
                        img = json.illusts[i].image_urls.large;
                    } while(typeof img == 'undefined' && attempts < json.illusts.length);
                    console.log('Image id: ' + json.illusts[i].id);
                    console.log('Image url: ' + img);
                    pixivlink = 'https://www.pixiv.net/member_illust.php?mode=medium&illust_id=' + json.illusts[i].id;
                    resolve();
                });
            }).catch((e) => {
                reject(e);
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
            const gotStream = got.stream(img, { headers: { Referer: 'http://www.pixiv.net/' } });
            gotStream.on('error', async (e) => {
                console.log('Error downloading image');
                console.log(e);
                await dlImage();
            });

            gotStream.pipe(fs.createWriteStream(jpg.name)).on('close', () => {
                console.log('Downloaded image');
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
            console.log('Searching for query "' + q + '"' + (meOnly ? ' on my channel' : ''));
            service.search.list(options, (err, results) => {
                if (err) { // error searching for video
                    reject('The YouTube API returned an error: ' + err);
                    return;
                }
                console.log('Returned ' + results.data.items.length + ' videos');
                if (results.data.items.length !== 0 && meOnly !== true) { // If we're not searching for our own videos we need to make sure nothing's too long
                    console.log('Looking for videos that are too long');
                    var ids = [];
                    for (var i = 0; i < results.data.items.length; i++) {
                        ids.push(results.data.items[i].id.videoId);
                    }
                    service.videos.list({
                        auth: auth,
                        part: 'contentDetails',
                        id: ids.join(',')
                    }, (err, results2) => {
                        if (err) {
                            reject('The YouTube API returned an error: ' + err);
                            return;
                        }
                        var i = results2.data.items.length, removeids = [];
                        while (i--) {
                            var d = parseDuration(results2.data.items[i].contentDetails.duration);
                            if (d > 390) { // longer than 6 minutes 30 seconds
                                console.log(results2.data.items[i].id + ' is way too long (' + d + 's)');
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
                        console.log('New array length is ' + results.data.items.length);
                        resolve(results.data.items);
                    });
                } else resolve(results.data.items);
            });
        });
    }

    function getVideo() {
        return new Promise(async (resolve, reject) => {
            var results, timesSearched = 0;
            do {
                results = await searchVideo('v=' + randomid() + ' -nightcore', 50); // find a random video id and no nightcore
                timesSearched++;
            } while (results.length === 0 && timesSearched <= 4);
            if (results.length === 0) {
                reject('Literally zero videos were found :(');
                return;
            }
            videoi = random(results.length - 1);
            video = results[videoi].id.videoId;
            videos = results;
            findUniqueId();
            async function findUniqueId() { // See if we've uploaded a video with this id in the desc
                let r = await searchVideo(video, 1, true);
                if (r.length == 0) {
                    console.log(video + ' is a unique video');
                    videotitle = decode(videos[videoi].snippet.title);
                    console.log(JSON.stringify(videos[videoi]));
                    service.videos.list({ // this search returns the tags of the videos
                        auth: auth,
                        part: 'snippet',
                        id: video
                    }, (err, results3) => {
                        if (err) {
                            reject('The YouTube API returned an error: ' + err);
                            return;
                        }
                        ogtags = results3.data.items[0].snippet.tags;
                        if (typeof ogtags == 'undefined') {
                            ogtags = [];
                            console.log('No tags found'); // in case someone has the AUDACITY to not tag their video
                        } else {
                            for (var i = 0; i < ogtags.length; i++) {
                                ogtags[i] = decode(ogtags[i]);
                            }
                            console.log('Found tags: ' + ogtags.join(', '));
                        }
                        resolve();
                    });
                } else {
                    console.log('Uploaded ' + video + ' before, looking for a new video');
                    videoi = random(results.length - 1);
                    video = videos[videoi].id.videoId;
                    findUniqueId();
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
                .on('finish', () => {
                    console.log('Downloaded video');
                    console.log('flv size: ' + fs.statSync(flv.name).size);
                    resolve();
                })
                .on('error', async (err) => {
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
                .on('end', (stdout, stderr) => {
                    console.log('Converted to mp3');
                    console.log('mp3 size: ' + fs.statSync(mp3.name).size);
                    console.log(stdout + stderr);
                    mm.parseFile(mp3.name, { native: true }).then(metadata => {
                        sampleRate = metadata.format.sampleRate;
                        console.log('mp3 sample rate: ' + sampleRate);
                        resolve();
                    }).catch(err => {
                        reject(err);
                    });
                })
                .on('error', (err) => {
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
                .audioCodec('aac')
                .addOptions([
                    /* 1: pad image so the dimensions are guaranteed to be even
                    2: set sample rate to 1.265 * current sample rate
                    3: split newly sped up audio into 2 outputs (one is mapped to the final audio track, one is used for the histogram)
                    4: create histogram
                    5: scale histogram to height 100px
                    6: negate histogram so it's black (most pixiv images are light colored)
                    7: overlay histogram over image */
                    '-filter_complex', '[0:v]pad=ceil(iw/2)*2:ceil(ih/2)*2[pv];[1:a]asetrate=' + (sampleRate * 1.265) + '[n];[n]asplit[nh][no];' +
                        '[nh]ahistogram=rheight=1[h];[h][pv]scale2ref=h=ih*0.1[hs][pv];[hs]negate[hn];[pv][hn]overlay=(W-w)/2:H-h:shortest=1',
                    '-map', '[no]',
                    '-tune', 'stillimage',
                    '-pix_fmt', 'yuv420p',
                    '-preset', 'ultrafast',
                    '-shortest',
                ])
                .output(mp4.name)
                .on('end', (stdout, stderr) => {
                    console.log('Converted to mp4');
                    console.log('mp4 size: ' + fs.statSync(mp4.name).size);
                    console.log(stdout + stderr);
                    resolve();
                })
                .on('error', (err) => {
                    reject(err);
                })
                .run();
        });
    }

    function uploadVideo() {
        return new Promise((resolve, reject) => {
            var tags = createTags(ogtags, videotitle);
            console.log('Tags: ' + tags.join(', '));
            var options = {
                part: 'id,snippet,status',
                notifySubscribers: true,
                requestBody: {
                    snippet: {
                        title: truncate('Nightcore - ' + videotitle, 100),
                        description: 'This nightcore remix was automatically generated by a bot! Subscribe for more randomly generated nightcore. ' +
                            "\n\nOriginal song: http://youtu.be/" + video + '\nImage: ' + pixivlink + "\nI don't own any of the content used here. " +
                            "Please contact my Senpai at the email in my channel description if you're the owner of this content and you'd like it taken down.",
                        tags: tags,
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
                (err, res) => {
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
    var regex = /(-)?P(?:([.,\d]+)Y)?(?:([.,\d]+)M)?(?:([.,\d]+)W)?(?:([.,\d]+)D)?T(?:([.,\d]+)H)?(?:([.,\d]+)M)?(?:([.,\d]+)S)?/;
    var matches = d.match(regex);
    return Number(matches[4] === undefined ? 0 : matches[4] * 604800) + // weeks (yes weeks :/)
        Number(matches[5] === undefined ? 0 : matches[5] * 86400) +     // days
        Number(matches[6] === undefined ? 0 : matches[6] * 3600) +      // hours
        Number(matches[7] === undefined ? 0 : matches[7] * 60) +        // minutes
        Number(matches[8] === undefined ? 0 : matches[8]);              // seconds
}

function truncate(s, l) {
    if (s.length >= l) {
        return s.substring(0, l);
    }
    return s;
}

function createTags(t, title) {
    var tags = ['nightcore', truncate(title, 30)];
    if (t.length > 0) {
        for (var i = 0; i < t.length; i++) {
            if (typeof t[i] == "undefined") {
                t.splice(i, 1);
            }
        }
        tags = tags.concat(t);
        var length = 0;
        for (var i = 0; i < tags.length; i++) {
            tags[i] = tags[i].toLowerCase();
            length += tags[i].length;
            if (length >= 400) {
                tags = tags.slice(0, i - 1);
                break;
            }
        }
        return tags.filter((item, index) => {
            return tags.indexOf(item) >= index;
        });
    } else {
        return tags;
    }
}

function random(max) {
    return Math.floor(Math.random() * (max + 1));
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