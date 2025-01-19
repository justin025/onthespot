import re
import requests
import subprocess
import threading
import time
import traceback
import os
from PyQt6.QtCore import QObject, pyqtSignal
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.metadata import TrackId, EpisodeId
from yt_dlp import YoutubeDL
from .accounts import get_account_token
from .api.apple_music import apple_music_get_track_metadata, apple_music_get_decryption_key, apple_music_get_lyrics, apple_music_get_webplayback_info
from .api.bandcamp import bandcamp_get_track_metadata
from .api.deezer import deezer_get_track_metadata, get_song_info_from_deezer_website, genurlkey, calcbfkey, decryptfile
from .api.qobuz import qobuz_get_track_metadata, qobuz_get_file_url
from .api.soundcloud import soundcloud_get_track_metadata
from .api.spotify import spotify_get_track_metadata, spotify_get_episode_metadata, spotify_get_lyrics
from .api.tidal import tidal_get_track_metadata, tidal_get_lyrics, tidal_get_file_url
from .api.youtube_music import youtube_music_get_track_metadata
from .api.generic import generic_get_track_metadata
from .otsconfig import config
from .runtimedata import get_logger, download_queue, download_queue_lock, account_pool, temp_download_path
from .utils import format_track_path, convert_audio_format, embed_metadata, set_music_thumbnail, fix_mp3_metadata, add_to_m3u_file, strip_metadata

logger = get_logger("downloader")


class RetryWorker(QObject):
    progress = pyqtSignal(dict, str, int)
    def __init__(self, gui=False):
        super().__init__()
        self.gui = gui
        self.thread = threading.Thread(target=self.run)
        self.is_running = True


    def start(self):
        logger.info('Starting Retry Worker')
        self.thread.start()


    def run(self):
        while self.is_running:
            if download_queue:
                with download_queue_lock:
                    for local_id in download_queue.keys():
                        logger.debug(f'Retrying : {local_id}')
                        if download_queue[local_id]['item_status'] == "Failed":
                            download_queue[local_id]['item_status'] = "Waiting"
                            if self.gui:
                                download_queue[local_id]['gui']['status_label'].setText(self.tr("Waiting"))
                                download_queue[local_id]['gui']["btn"]['cancel'].show()
                                download_queue[local_id]['gui']["btn"]['retry'].hide()
            time.sleep(config.get('retry_worker_delay') * 60)
            continue


    def stop(self):
        logger.info('Stopping Retry Worker')
        self.is_running = False
        self.thread.join()


class DownloadWorker(QObject):
    progress = pyqtSignal(dict, str, int)
    def __init__(self, gui=False):
        super().__init__()
        self.gui = gui
        self.thread = threading.Thread(target=self.run)
        self.is_running = True
        self.cleaned_directory = False


    def start(self):
        logger.info('Starting Download Worker')
        self.thread.start()


    def readd_item_to_download_queue(self, item):
        with download_queue_lock:
            try:
                local_id = item['local_id']
                del download_queue[local_id]
                download_queue[local_id] = item
                download_queue[local_id]['available'] = True
            except (KeyError):
                # Item likely cleared from queue
                return


    def yt_dlp_progress_hook(self, item, d):
        progress = item['gui']['progress_bar'].value()
        progress_str = re.search(r'(\d+\.\d+)%', d['_percent_str'])
        updated_progress_value = round(float(progress_str.group(1))) - 1
        if updated_progress_value >= progress:
            self.progress.emit(item, self.tr("Downloading"), updated_progress_value)
        if item['item_status'] == 'Cancelled':
            raise Exception("Download cancelled by user.")


    def run(self):
        while self.is_running:
            try:
                try:
                    if download_queue:
                        with download_queue_lock:

                            # Mark item as unavailable for other download workers
                            iterator = iter(download_queue)
                            while True:
                                local_id = next(iterator)
                                if download_queue[local_id]['available'] is False:
                                    continue
                                download_queue[local_id]['available'] = False
                                item = download_queue[local_id]
                                break
                    else:
                        time.sleep(0.2)
                        continue

                    item_service = item['item_service']
                    item_type = item['item_type']
                    item_id = item['item_id']

                    if item['item_status'] in (
                        "Cancelled",
                        "Failed",
                        "Unavailable",
                        "Downloaded",
                        "Already Exists",
                        "Deleted"
                    ):
                        time.sleep(0.2)
                        self.readd_item_to_download_queue(item)
                        continue
                except (RuntimeError, OSError, StopIteration):
                    time.sleep(0.2)
                    continue

                item['item_status'] = "Downloading"
                if self.gui:
                    self.progress.emit(item, self.tr("Downloading"), 1)

                token = get_account_token(item_service)

                try:
                    item_metadata = globals()[f"{item_service}_get_{item_type}_metadata"](token, item_id)

                    # album number shim from enumerated items, i hate youtube
                    if item_service == 'youtube_music' and item.get('parent_category', '') == 'album':
                        item_metadata.update({'track_number': item['playlist_number']})

                    item_path = format_track_path(item, item_metadata)
                except (Exception, KeyError) as e:
                    logger.error(f"Failed to fetch metadata for '{item_id}', Error: {str(e)}\nTraceback: {traceback.format_exc()}")
                    item['item_status'] = "Failed"
                    self.tr("Failed")
                    if self.gui:
                        self.progress.emit(item, self.tr("Failed"), 0)
                    self.readd_item_to_download_queue(item)
                    continue

                temp_file_path = ''
                file_path = ''
                if item_service != 'generic':
                    dl_root = config.get("download_root")
                    if temp_download_path:
                        dl_root = temp_download_path[0]
                    file_path = os.path.join(dl_root, item_path)
                    directory, file_name = os.path.split(file_path)
                    temp_file_path = os.path.join(directory, '~' + file_name)

                    # Clear the directory if it exists at the beginning
                    if config.get("delete_removed", False) and not self.cleaned_directory:
                        if os.path.exists(os.path.dirname(file_path)):
                            for file_name in os.listdir(os.path.dirname(file_path)):
                                file_path_to_delete = os.path.join(os.path.dirname(file_path), file_name)
                                try:
                                    if os.path.isfile(file_path_to_delete):
                                        os.remove(file_path_to_delete)
                                    elif os.path.isdir(file_path_to_delete):
                                        os.rmdir(file_path_to_delete)
                                except Exception as e:
                                    logger.error(f"Error while cleaning {file_path_to_delete}: {e}")
                        self.cleaned_directory = True  # Marque le nettoyage comme effectué

                    # Create the directory if it doesn't exist
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)

                    # Skip download if file exists under different extension
                    file_directory = os.path.dirname(file_path)
                    base_filename = os.path.basename(file_path)

                    for entry in os.listdir(file_directory):
                        full_path = os.path.join(file_directory, entry)  # Construct the full file path

                        # Check if the entry is a file and if its name matches the base filename
                        if os.path.isfile(full_path) and os.path.splitext(entry)[0] == base_filename and os.path.splitext(entry)[1] != '.lrc':

                            item['file_path'] = os.path.join(file_directory, entry)

                            if config.get('overwrite_existing_metadata'):

                                logger.info('Overwriting Existing Metadata')

                                # Lyrics
                                if item_service in ("spotify", "tidal"):
                                    item['item_status'] = 'Getting Lyrics'
                                    if self.gui:
                                        self.progress.emit(item, self.tr("Getting Lyrics"), 99)
                                    extra_metadata = globals()[f"{item_service}_get_lyrics"](token, item_id, item_type, item_metadata, file_path)
                                    if isinstance(extra_metadata, dict):
                                        item_metadata.update(extra_metadata)

                                if not config.get('force_raw'):
                                    strip_metadata(item)
                                    embed_metadata(item, item_metadata)

                                    # Thumbnail
                                    if config.get('save_album_cover') or config.get('embed_cover'):
                                        item['item_status'] = 'Setting Thumbnail'
                                        if self.gui:
                                            self.progress.emit(item, self.tr("Setting Thumbnail"), 99)
                                        set_music_thumbnail(item['file_path'], item_metadata)

                                    if os.path.splitext(item['file_path'])[1] == '.mp3':
                                        fix_mp3_metadata(item['file_path'])
                                else:
                                    if config.get('save_album_cover'):
                                        item['item_status'] = 'Setting Thumbnail'
                                        if self.gui:
                                            self.progress.emit(item, self.tr("Setting Thumbnail"), 99)
                                        set_music_thumbnail(file_path, item_metadata)

                            # M3U
                            if config.get('create_m3u_playlists') and item.get('parent_category') == 'playlist':
                                item['item_status'] = 'Adding To M3U'
                                if self.gui:
                                    self.progress.emit(item, self.tr("Adding To M3U"), 1)
                                    add_to_m3u_file(item, item_metadata)

                            if self.gui and item['item_status'] in ('Downloading', 'Setting Thumbnail', 'Adding To M3U'):
                                self.progress.emit(item, self.tr("Already Exists"), 100)
                            item['item_status'] = 'Already Exists'
                            logger.info(f"File already exists, Skipping download for track by id '{item_id}'")
                            time.sleep(0.2)
                            self.readd_item_to_download_queue(item)
                            break

                if item['item_status'] == 'Already Exists':
                    continue

                if not item_metadata['is_playable']:
                    logger.error(f"Track is unavailable, track id '{item_id}'")
                    item['item_status'] = 'Unavailable'
                    if self.gui:
                        self.progress.emit(item, self.tr("Unavailable"), 0)
                    self.readd_item_to_download_queue(item)
                    continue

                # Downloading the file here is necessary to animate progress bar through pyqtsignal.
                # Could at some point just update the item manually inside the api file by passing
                # item['gui']['progressbar'] and self.gui into a download_track function.
                try:
                    if item_service == "spotify":

                        default_format = ".ogg"
                        temp_file_path += default_format
                        if item_type == "track":
                            audio_key = TrackId.from_base62(item_id)
                        elif item_type == "episode":
                            audio_key = EpisodeId.from_base62(item_id)

                        quality = AudioQuality.HIGH
                        bitrate = "160k"
                        if token.get_user_attribute("type") == "premium" and item_type == 'track':
                            quality = AudioQuality.VERY_HIGH
                            bitrate = "320k"

                        stream = token.content_feeder().load(audio_key, VorbisOnlyAudioQuality(quality), False, None)
                        total_size = stream.input_stream.size
                        downloaded = 0
                        with open(temp_file_path, 'wb') as file:
                            while downloaded < total_size:
                                if item['item_status'] == 'Cancelled':
                                   raise Exception("Download cancelled by user.")
                                data = stream.input_stream.stream().read(config.get("chunk_size"))
                                downloaded += len(data)
                                if len(data) != 0:
                                    file.write(data)
                                    if self.gui:
                                        self.progress.emit(item, self.tr("Downloading"), int((downloaded / total_size) * 100))
                                if len(data) == 0:
                                    break
                        stream.input_stream.stream().close()
                        stream_internal = stream.input_stream.stream()
                        del stream_internal, stream.input_stream


                    elif item_service == 'deezer':
                        song = get_song_info_from_deezer_website(token, item['item_id'])

                        song_quality = 1
                        song_format = 'MP3_128'
                        bitrate = "128k"
                        default_format = ".mp3"
                        if int(song.get("FILESIZE_FLAC")) > 0:
                            song_quality = 9
                            song_format ='FLAC'
                            bitrate = "1411k"
                            default_format = ".flac"
                        elif int(song.get("FILESIZE_MP3_320")) > 0:
                            song_quality = 3
                            song_format = 'MP3_320'
                            bitrate = "320k"
                        elif int(song.get("FILESIZE_MP3_256")) > 0:
                            song_quality = 5
                            song_format = 'MP3_256'
                            bitrate = "256k"
                        temp_file_path += default_format

                        headers = {
                            'Origin': 'https://www.deezer.com',
                            'Accept-Encoding': 'utf-8',
                            'Referer': 'https://www.deezer.com/login',
                        }

                        track_data = token['session'].post(
                            "https://media.deezer.com/v1/get_url",
                            json={
                                'license_token': token['license_token'],
                                'media': [{
                                    'type': "FULL",
                                    'formats': [
                                        { 'cipher': "BF_CBC_STRIPE", 'format': song_format }
                                    ]
                                }],
                                'track_tokens': [song["TRACK_TOKEN"]]
                            },
                            headers = headers
                        ).json()

                        try:
                            logger.debug(track_data)
                            url = track_data['data'][0]['media'][0]['sources'][0]['url']
                        except KeyError as e:
                            # Fallback to lowest quality
                            logger.error(f'Unable to select Deezer quality, falling back to 128kbps. Error: {str(e)}\nTraceback: {traceback.format_exc()}')
                            song_quality = 1
                            song_format = 'MP3_128'
                            bitrate = "128k"
                            default_format = ".mp3"
                            urlkey = genurlkey(song["SNG_ID"], song["MD5_ORIGIN"], song["MEDIA_VERSION"], song_quality)
                            url = "https://e-cdns-proxy-%s.dzcdn.net/mobile/1/%s" % (song["MD5_ORIGIN"][0], urlkey.decode())

                        file = requests.get(url, stream=True)

                        if file.status_code == 200:
                            total_size = int(file.headers.get('content-length', 0))
                            downloaded = 0
                            data_chunks = b''  # empty bytes object

                            for data in file.iter_content(chunk_size=config.get("chunk_size")):
                                downloaded += len(data)
                                data_chunks += data

                                if downloaded != total_size:
                                    if item['item_status'] == 'Cancelled':
                                        raise Exception("Download cancelled by user.")
                                    if self.gui:
                                        self.progress.emit(item, self.tr("Downloading"), int((downloaded / total_size) * 100))

                            key = calcbfkey(song["SNG_ID"])

                            if self.gui:
                                self.progress.emit(item, self.tr("Decrypting"), 99)
                            with open(temp_file_path, "wb") as fo:
                                decryptfile(data_chunks, key, fo)

                        else:
                            logger.info(f"Deezer download attempts failed: {file.status_code}")
                            item['item_status'] = "Failed"
                            if self.gui:
                                self.progress.emit(item, self.tr("Failed"), 0)
                            self.readd_item_to_download_queue(item)


                    elif item_service in ("soundcloud", "youtube_music"):
                        if item_service == "soundcloud":
                            default_format = ".mp3"
                            bitrate = "128k"
                            item_url = item_metadata['item_url']
                        elif item_service == "youtube_music":
                            default_format = '.opus'
                            bitrate = "256k"
                            item_url = f'https://music.youtube.com/watch?v={item["item_id"]}'
                        ydl_opts = {}
                        ydl_opts['quiet'] = True
                        ydl_opts['no_warnings'] = True
                        ydl_opts['noprogress'] = True
                        ydl_opts['extract_audio'] = True
                        ydl_opts['format'] = 'bestaudio'
                        ydl_opts['outtmpl'] = temp_file_path
                        if self.gui:
                            ydl_opts['progress_hooks'] = [lambda d: self.yt_dlp_progress_hook(item, d)]
                        with YoutubeDL(ydl_opts) as video:
                            video.download(item_url)


                    elif item_service in ("bandcamp", "qobuz", "tidal"):
                        if item_service in ("qobuz", "tidal"):
                            default_format = '.flac'
                            bitrate = "1411k"
                            file_url = globals()[f"{item_service}_get_file_url"](token, item_id)
                        elif item_service == 'bandcamp':
                            default_format = '.mp3'
                            bitrate = "128k"
                            file_url = item_metadata['file_url']
                        response = requests.get(file_url, stream=True)
                        total_size = int(response.headers.get('Content-Length', 0))
                        downloaded = 0
                        data_chunks = b''
                        with open(temp_file_path, 'wb') as file:
                            for data in response.iter_content(chunk_size=config.get("chunk_size", 1024)):
                                if data:
                                    downloaded += len(data)
                                    data_chunks += data
                                    file.write(data)

                                    if total_size > 0 and downloaded != total_size:
                                        if item['item_status'] == 'Cancelled':
                                            raise Exception("Download cancelled by user.")
                                        if self.gui:
                                            self.progress.emit(item, self.tr("Downloading"), int((downloaded / total_size) * 100))

                    elif item_service == "apple_music":
                        default_format = '.m4a'
                        bitrate = "256k"
                        webplayback_info = apple_music_get_webplayback_info(token, item_id)

                        stream_url = None
                        for asset in webplayback_info["assets"]:
                            if asset["flavor"] == "28:ctrp256":
                                stream_url = asset["URL"]

                        if not stream_url:
                            logger.error(f'Apple music playback info invalid: {webplayback_info}')
                            continue

                        decryption_key = apple_music_get_decryption_key(token, stream_url, item_id)

                        ydl_opts = {}
                        ydl_opts['quiet'] = True
                        ydl_opts['no_warnings'] = True
                        ydl_opts['outtmpl'] = temp_file_path
                        ydl_opts['allow_unplayable_formats'] = True
                        ydl_opts['fixup'] = 'never'
                        ydl_opts['allowed_extractors'] = ['generic']
                        ydl_opts['noprogress'] = True
                        if self.gui:
                            ydl_opts['progress_hooks'] = [lambda d: self.yt_dlp_progress_hook(item, d)]
                        with YoutubeDL(ydl_opts) as video:
                            video.download(stream_url)

                        if self.gui:
                            self.progress.emit(item, self.tr("Decrypting"), 99)

                        decrypted_temp_file_path = temp_file_path + '.m4a'
                        command = [
                            config.get('_ffmpeg_bin_path'),
                            "-loglevel", "error",
                            "-y",
                            "-decryption_key", decryption_key,
                            "-i", temp_file_path,
                            "-c", "copy",
                            "-movflags",
                            "+faststart",
                            decrypted_temp_file_path
                        ]
                        if os.name == 'nt':
                            subprocess.check_call(command, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                        else:
                            subprocess.check_call(command, shell=False)

                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                        os.rename(decrypted_temp_file_path, temp_file_path)

                    elif item_service == 'generic':
                        temp_file_path = ''
                        ydl_opts = {}
                        # Prefer bestvideo in mp4 with specified resolution, then
                        # just best video with specified resolution, and if neither
                        # exist just go with best.
                        ydl_opts['format'] = (f'(bestvideo[height<={config.get("maximum_generic_resolution")}][ext=mp4]+bestaudio[ext=m4a])/'
                                            f'(bestvideo[height<={config.get("maximum_generic_resolution")}]+bestaudio)/'
                                            f'best')
                        ydl_opts['quiet'] = True
                        ydl_opts['no_warnings'] = True
                        ydl_opts['noprogress'] = True
                        ydl_opts['outtmpl'] = config.get('generic_download_root') + os.path.sep + '%(title)s.%(ext)s'
                        ydl_opts['ffmpeg_location'] = config.get('_ffmpeg_bin_path')
                        ydl_opts['postprocessors'] = [{
                            'key': 'FFmpegMetadata',  # Enables embedding metadata
                        }]
                        if self.gui:
                            ydl_opts['progress_hooks'] = [lambda d: self.yt_dlp_progress_hook(item, d)]
                        with YoutubeDL(ydl_opts) as video:
                            item['file_path'] = video.prepare_filename(video.extract_info(item_id, download=False))
                            video.download(item_id)

                except RuntimeError as e:
                    # Likely Ratelimit
                    logger.info(f"Download failed: {item}, Error: {str(e)}\nTraceback: {traceback.format_exc()}")
                    item['item_status'] = 'Failed'
                    if self.gui:
                        self.progress.emit(item, self.tr("Failed"), 0)
                    self.readd_item_to_download_queue(item)
                    continue

                # Lyrics
                if item_service in ("apple_music", "spotify", "tidal"):
                    item['item_status'] = 'Getting Lyrics'
                    if self.gui:
                        self.progress.emit(item, self.tr("Getting Lyrics"), 99)
                    extra_metadata = globals()[f"{item_service}_get_lyrics"](token, item_id, item_type, item_metadata, file_path)
                    if isinstance(extra_metadata, dict):
                        item_metadata.update(extra_metadata)

                if item_service != 'generic':
                    if config.get('force_raw'):
                        file_path += default_format
                    elif item_type == "track":
                        file_path += "." + config.get("media_format")
                    elif item_type == "episode":
                        file_path += "." + config.get("podcast_media_format")

                    os.rename(temp_file_path, file_path)
                    item['file_path'] = file_path

                if item_service != 'generic':
                    # Convert file format and embed metadata
                    if not config.get('force_raw'):
                        item['item_status'] = 'Converting'
                        if self.gui:
                            self.progress.emit(item, self.tr("Converting"), 99)

                        convert_audio_format(file_path, default_format)

                        embed_metadata(item, item_metadata)

                        # Thumbnail
                        if config.get('save_album_cover') or config.get('embed_cover'):
                            item['item_status'] = 'Setting Thumbnail'
                            if self.gui:
                                self.progress.emit(item, self.tr("Setting Thumbnail"), 99)
                            set_music_thumbnail(file_path, item_metadata)

                        if os.path.splitext(file_path)[1] == '.mp3':
                            fix_mp3_metadata(file_path)
                    else:
                        if config.get('save_album_cover'):
                            item['item_status'] = 'Setting Thumbnail'
                            if self.gui:
                                self.progress.emit(item, self.tr("Setting Thumbnail"), 99)
                            set_music_thumbnail(file_path, item_metadata)

                    # M3U
                    if config.get('create_m3u_playlists') and item.get('parent_category') == 'playlist':
                        item['item_status'] = 'Adding To M3U'
                        if self.gui:
                            self.progress.emit(item, self.tr("Adding To M3U"), 1)
                            add_to_m3u_file(item, item_metadata)

                item['item_status'] = 'Downloaded'
                logger.info("Item Successfully Downloaded")
                if self.gui:
                    self.progress.emit(item, self.tr("Downloaded"), 100)

                time.sleep(config.get("download_delay"))
                self.readd_item_to_download_queue(item)
                continue
            except Exception as e:
                logger.error(f"Unknown Exception: {str(e)}\nTraceback: {traceback.format_exc()}")
                if item['item_status'] != "Cancelled":
                    item['item_status'] = "Failed"
                    if self.gui:
                        self.progress.emit(item, self.tr("Failed"), 0)
                else:
                    if self.gui:
                        self.progress.emit(item, self.tr("Cancelled"), 0)

                time.sleep(config.get("download_delay"))
                self.readd_item_to_download_queue(item)

                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                if isinstance(item['file_path'], str) and os.path.exists(item['file_path']):
                    os.remove(item['file_path'])
                continue


    def stop(self):
        logger.info('Stopping Download Worker')
        self.is_running = False
        self.thread.join()
