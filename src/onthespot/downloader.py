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
from .api.spotify import spotify_get_track_metadata, spotify_get_podcast_episode_metadata, spotify_get_lyrics
from .api.tidal import tidal_get_track_metadata, tidal_get_lyrics, tidal_get_file_url
from .api.youtube_music import youtube_music_get_track_metadata
from .api.crunchyroll import crunchyroll_get_episode_metadata, crunchyroll_get_decryption_key, crunchyroll_get_mpd_info, crunchyroll_close_stream
from .api.generic import generic_get_track_metadata
from .otsconfig import config
from .runtimedata import get_logger, download_queue, download_queue_lock, account_pool, temp_download_path
from .utils import format_item_path, convert_audio_format, embed_metadata, set_music_thumbnail, fix_mp3_metadata, add_to_m3u_file, strip_metadata, convert_video_format

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
            if config.get('retry_worker_delay') > 0:
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


    def update_progress(self, item, status, progress_value):
        """Update progress for both GUI and web interface"""
        if self.gui:
            self.progress.emit(item, status, progress_value)
        # Always update the item's progress for web interface
        item['progress'] = progress_value


    def yt_dlp_progress_hook(self, item, d):
        progress = item.get('progress', 0)
        progress_str = re.search(r'(\d+\.\d+)%', d['_percent_str'])
        if progress_str:
            updated_progress_value = round(float(progress_str.group(1))) - 1
            if updated_progress_value >= progress:
                self.update_progress(item, self.tr("Downloading") if self.gui else "Downloading", updated_progress_value)
        if item['item_status'] == 'Cancelled':
            raise Exception("Download cancelled by user.")


    def _find_account_index(self, service, token):
        """Find the index of the account in account_pool that matches the given token"""
        for idx, account in enumerate(account_pool):
            if account.get('service') == service:
                account_token = account.get('login', {}).get('session')
                if account_token is token:
                    return idx
        return None

    def _get_available_accounts(self, service):
        """Get list of available account indices for a service"""
        indices = []
        for idx, account in enumerate(account_pool):
            if account.get('service') == service and account.get('active', True):
                indices.append(idx)
        return indices

    def _try_get_spotify_stream(self, item, item_id, item_type, token, quality, tried_accounts=None):
        """
        Try to get a Spotify stream, with fallback to other accounts if one fails.
        Returns (stream, token, account_index) on success, raises exception on complete failure.
        """
        from .api.spotify import spotify_re_init_session
        
        if tried_accounts is None:
            tried_accounts = set()
        
        if item_type == "track":
            audio_key = TrackId.from_base62(item_id)
        elif item_type == "podcast_episode":
            audio_key = EpisodeId.from_base62(item_id)
        
        # Find current account index
        current_account_idx = self._find_account_index('spotify', token)
        available_accounts = self._get_available_accounts('spotify')
        
        max_retries_per_account = 2
        
        # Try current account first
        if current_account_idx is not None and current_account_idx not in tried_accounts:
            for attempt in range(max_retries_per_account):
                try:
                    stream = token.content_feeder().load(audio_key, VorbisOnlyAudioQuality(quality), False, None)
                    logger.info(f"Successfully got stream from account index {current_account_idx}")
                    return stream, token, current_account_idx
                except (RuntimeError, OSError) as e:
                    error_str = str(e)
                    if any(x in error_str for x in ['Bad file descriptor', 'Cannot get alternative track', 'Unable to']):
                        if attempt < max_retries_per_account - 1:
                            logger.warning(f"Download stream failed (attempt {attempt + 1}) on account {current_account_idx}, reconnecting session: {e}")
                            try:
                                spotify_re_init_session(account_pool[current_account_idx])
                                token = account_pool[current_account_idx]['login']['session']
                                # Refresh quality check with new token
                                if token.get_user_attribute("type") == "premium" and item_type == 'track':
                                    quality = AudioQuality.VERY_HIGH
                                logger.info("Session reconnected successfully, retrying...")
                            except Exception as reinit_err:
                                logger.error(f"Session reinit failed for account {current_account_idx}: {reinit_err}")
                                break  # Try next account
                        else:
                            logger.warning(f"Max retries reached for account {current_account_idx}")
                            break  # Try next account
                    else:
                        raise
            
            tried_accounts.add(current_account_idx)
        
        # Try other available accounts
        for account_idx in available_accounts:
            if account_idx in tried_accounts:
                continue
            
            logger.info(f"Trying fallback account index {account_idx}")
            tried_accounts.add(account_idx)
            
            try:
                # Get token from this account
                fallback_token = account_pool[account_idx]['login']['session']
                
                # Check quality for this account
                fallback_quality = AudioQuality.HIGH
                if fallback_token.get_user_attribute("type") == "premium" and item_type == 'track':
                    fallback_quality = AudioQuality.VERY_HIGH
                
                for attempt in range(max_retries_per_account):
                    try:
                        stream = fallback_token.content_feeder().load(audio_key, VorbisOnlyAudioQuality(fallback_quality), False, None)
                        logger.info(f"Successfully got stream from fallback account index {account_idx}")
                        return stream, fallback_token, account_idx
                    except (RuntimeError, OSError) as e:
                        error_str = str(e)
                        if any(x in error_str for x in ['Bad file descriptor', 'Cannot get alternative track', 'Unable to']):
                            if attempt < max_retries_per_account - 1:
                                logger.warning(f"Fallback account {account_idx} stream failed (attempt {attempt + 1}), reconnecting: {e}")
                                try:
                                    spotify_re_init_session(account_pool[account_idx])
                                    fallback_token = account_pool[account_idx]['login']['session']
                                    logger.info(f"Fallback account {account_idx} reconnected, retrying...")
                                except Exception as reinit_err:
                                    logger.error(f"Fallback account {account_idx} reinit failed: {reinit_err}")
                                    break
                            else:
                                logger.warning(f"Max retries reached for fallback account {account_idx}")
                                break
                        else:
                            raise
            except Exception as e:
                logger.error(f"Fallback account {account_idx} failed completely: {e}")
                continue
        
        # All accounts exhausted
        raise RuntimeError(f"Failed to load audio stream after trying {len(tried_accounts)} account(s)")


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
                self.update_progress(item, self.tr("Downloading") if self.gui else "Downloading", 1)

                token = get_account_token(item_service, rotate=config.get("rotate_active_account_number"))

                try:
                    item_metadata = globals()[f"{item_service}_get_{item_type}_metadata"](token, item_id)

                    # album number shim from enumerated items, i hate youtube
                    if item_service == 'youtube_music' and item.get('parent_category') == 'album':
                        item_metadata.update({'track_number': item['playlist_number']})

                    item_path = format_item_path(item, item_metadata)
                except (Exception, KeyError) as e:
                    logger.error(f"Failed to fetch metadata for '{item_id}', Error: {str(e)}\nTraceback: {traceback.format_exc()}")
                    item['item_status'] = "Failed"
                    self.update_progress(item, self.tr("Failed") if self.gui else "Failed", 0)
                    logger.info(f"DEBUG item_path from format_item_path: {item_path}")
                    self.readd_item_to_download_queue(item)
                    continue

                temp_file_path = ''
                file_path = ''
                if item_service != 'generic':
                    if item_type in ['track', 'podcast_episode']:
                        dl_root = config.get("audio_download_path")
                    elif item_type in ['movie', 'episode']:
                        dl_root = config.get("video_download_path")
                    if temp_download_path:
                        dl_root = temp_download_path[0]
                    file_path = os.path.join(dl_root, item_path)
                    directory, file_name = os.path.split(file_path)

                    # Additional verification of path length limits
                    name, ext = os.path.splitext(file_name)
                    MAX_PATH_LENGTH = 260
                    available_length = MAX_PATH_LENGTH - len(os.path.join(directory, ''))
                    if len(file_name) > available_length:
                        trim_length = available_length - len(ext)
                        name = name[:trim_length]
                        file_name = name + ext
                        file_path = os.path.join(directory, file_name)
                    
                    temp_file_path = os.path.join(directory, '~' + file_name)

                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    logger.info(f"DEBUG full file_path: {file_path}")

                    # Skip download if file exists under different extension
                    file_directory = os.path.dirname(file_path)
                    target_filename = os.path.basename(file_path)
                    
                    logger.info(f"Checking for existing files matching: '{target_filename}.*' in {file_directory}")

                    try:
                        for entry in os.listdir(file_directory):
                            full_path = os.path.join(file_directory, entry)
                            
                            if not os.path.isfile(full_path):
                                continue
                            
                            # Skip subtitle/lyrics files
                            if entry.endswith((".lrc", ".ass", ".srt", ".vtt")):
                                continue
                            
                            # Check if file matches target (strip audio extension)
                            audio_exts = [".mp3", ".flac", ".ogg", ".m4a", ".opus", ".wav", ".aac", ".wma"]
                            entry_base = entry
                            for ext in audio_exts:
                                if entry.endswith(ext):
                                    entry_base = entry[:-len(ext)]
                                    break
                            
                            if entry_base == target_filename:
                                logger.info(f"MATCH FOUND! File '{entry}' matches target '{target_filename}' - Skipping download")
                                item['file_path'] = full_path
                                if item_type in ['track', 'podcast_episode']:
                                    if config.get('overwrite_existing_metadata'):

                                        logger.info('Overwriting Existing Metadata')

                                        # Lyrics
                                        if item_service in ("apple_music", "spotify", "tidal") and config.get('download_lyrics'):
                                            item['item_status'] = 'Getting Lyrics'
                                            self.update_progress(item, self.tr("Getting Lyrics") if self.gui else "Getting Lyrics", 99)
                                            extra_metadata = globals()[f"{item_service}_get_lyrics"](token, item_id, item_type, item_metadata, file_path)
                                            if isinstance(extra_metadata, dict):
                                                item_metadata.update(extra_metadata)

                                        if not config.get('raw_media_download'):
                                            strip_metadata(item)
                                            embed_metadata(item, item_metadata)

                                            # Thumbnail
                                            if config.get('save_album_cover') or config.get('embed_cover'):
                                                item['item_status'] = 'Setting Thumbnail'
                                                self.update_progress(item, self.tr("Setting Thumbnail") if self.gui else "Setting Thumbnail", 99)
                                                set_music_thumbnail(item['file_path'], item_metadata)

                                            if os.path.splitext(item['file_path'])[1] == '.mp3':
                                                fix_mp3_metadata(item['file_path'])
                                        else:
                                            if config.get('save_album_cover'):
                                                item['item_status'] = 'Setting Thumbnail'
                                                self.update_progress(item, self.tr("Setting Thumbnail") if self.gui else "Setting Thumbnail", 99)
                                                set_music_thumbnail(file_path, item_metadata)

                                    # M3U
                                    if config.get('create_m3u_file') and item.get('parent_category') == 'playlist':
                                        item['item_status'] = 'Adding To M3U'
                                        self.update_progress(item, self.tr("Adding To M3U") if self.gui else "Adding To M3U", 99)
                                        add_to_m3u_file(item, item_metadata)

                                if item['item_status'] in ('Downloading', 'Setting Thumbnail', 'Adding To M3U', 'Getting Lyrics'):
                                    self.update_progress(item, self.tr("Already Exists") if self.gui else "Already Exists", 100)
                                item['item_status'] = 'Already Exists'
                                logger.info(f"File already exists (found as {entry}), Skipping download for track by id '{item_id}'")
                                time.sleep(0.2)
                                item['progress'] = 100
                                self.readd_item_to_download_queue(item)
                                break
                    except FileNotFoundError:
                        # Directory doesn't exist yet, will be created later
                        pass

                if item['item_status'] == 'Already Exists':
                    continue

                if not item_metadata['is_playable']:
                    logger.error(f"Track is unavailable, track id '{item_id}'")
                    item['item_status'] = 'Unavailable'
                    self.update_progress(item, self.tr("Unavailable") if self.gui else "Unavailable", 0)
                    self.readd_item_to_download_queue(item)
                    continue

                try:
                    # Audio
                    if item_service == "spotify":

                        default_format = ".ogg"
                        temp_file_path += default_format

                        quality = AudioQuality.HIGH
                        bitrate = "160k"
                        if token.get_user_attribute("type") == "premium" and item_type == 'track':
                            quality = AudioQuality.VERY_HIGH
                            bitrate = "320k"

                        # Use the new helper method for stream acquisition with fallback
                        stream, token, _ = self._try_get_spotify_stream(item, item_id, item_type, token, quality)

                        total_size = stream.input_stream.size
                        downloaded = 0
                        with open(temp_file_path, 'wb') as file:
                            while downloaded < total_size:
                                if item['item_status'] == 'Cancelled':
                                   raise Exception("Download cancelled by user.")
                                data = stream.input_stream.stream().read(config.get("download_chunk_size"))
                                downloaded += len(data)
                                if len(data) != 0:
                                    file.write(data)
                                    progress_pct = int((downloaded / total_size) * 100)
                                    self.update_progress(item, self.tr("Downloading") if self.gui else "Downloading", progress_pct)
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
                            data_chunks = b''

                            for data in file.iter_content(chunk_size=config.get("download_chunk_size")):
                                downloaded += len(data)
                                data_chunks += data

                                if downloaded != total_size:
                                    if item['item_status'] == 'Cancelled':
                                        raise Exception("Download cancelled by user.")
                                    progress_pct = int((downloaded / total_size) * 100)
                                    self.update_progress(item, self.tr("Downloading") if self.gui else "Downloading", progress_pct)

                            key = calcbfkey(song["SNG_ID"])

                            self.update_progress(item, self.tr("Decrypting") if self.gui else "Decrypting", 99)
                            with open(temp_file_path, "wb") as fo:
                                decryptfile(data_chunks, key, fo)

                        else:
                            logger.info(f"Deezer download attempts failed: {file.status_code}")
                            item['item_status'] = "Failed"
                            self.update_progress(item, self.tr("Failed") if self.gui else "Failed", 0)
                            self.readd_item_to_download_queue(item)

                    elif item_service in ("soundcloud", "youtube_music"):
                        item_url = item_metadata['item_url']
                        ydl_opts = {}
                        if item_service == "soundcloud":
                            if token['oauth_token']:
                                ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio'
                                ydl_opts['username'] = 'oauth'
                                ydl_opts['password'] = token['oauth_token']
                            else:
                                default_format = ".mp3"
                                bitrate = "128k"
                                ydl_opts['format'] = 'bestaudio[ext=mp3]'
                        elif item_service == "youtube_music":
                            default_format = '.m4a'
                            bitrate = "128k"
                            ydl_opts['format'] = 'bestaudio[ext=m4a]'
                        ydl_opts['quiet'] = True
                        ydl_opts['no_warnings'] = True
                        ydl_opts['noprogress'] = True
                        ydl_opts['extract_audio'] = True
                        ydl_opts['outtmpl'] = temp_file_path
                        ydl_opts['progress_hooks'] = [lambda d: self.yt_dlp_progress_hook(item, d)]
                        with YoutubeDL(ydl_opts) as video:
                            if item_service == "soundcloud" and token['oauth_token']:
                                info_dict = video.extract_info(item_url)
                                bitrate = f"{info_dict.get('abr')}k"
                                default_format = f".{info_dict.get('audio_ext')}"
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
                            for data in response.iter_content(chunk_size=config.get("download_chunk_size", 1024)):
                                if data:
                                    downloaded += len(data)
                                    data_chunks += data
                                    file.write(data)

                                    if total_size > 0 and downloaded != total_size:
                                        if item['item_status'] == 'Cancelled':
                                            raise Exception("Download cancelled by user.")
                                        progress_pct = int((downloaded / total_size) * 100)
                                        self.update_progress(item, self.tr("Downloading") if self.gui else "Downloading", progress_pct)

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
                        ydl_opts['progress_hooks'] = [lambda d: self.yt_dlp_progress_hook(item, d)]
                        with YoutubeDL(ydl_opts) as video:
                            video.download(stream_url)

                        self.update_progress(item, self.tr("Decrypting") if self.gui else "Decrypting", 99)

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

                    # Video
                    elif item_service == "crunchyroll":
                        ydl_opts = {}
                        ydl_opts['quiet'] = True
                        ydl_opts['no_warnings'] = True
                        ydl_opts['allow_unplayable_formats'] = True
                        ydl_opts['fixup'] = 'never'
                        ydl_opts['allowed_extractors'] = ['generic']
                        ydl_opts['noprogress'] = True
                        ydl_opts['progress_hooks'] = [lambda d: self.yt_dlp_progress_hook(item, d)]

                        # Extract preferred language
                        encrypted_files = []
                        video_files = []
                        subtitle_formats = []
                        for version in item_metadata['versions']:
                            if version['audio_locale'] in config.get('preferred_audio_language').replace(' ', '').split(',') or config.get('download_all_available_audio'):
                                try:
                                    mpd_url, stream_token, audio_locale, headers, versions, additional_subtitle_formats = crunchyroll_get_mpd_info(token, version['guid'])
                                    subtitle_formats += additional_subtitle_formats
                                    decryption_key = crunchyroll_get_decryption_key(token, version['guid'], mpd_url, stream_token)
                                except Exception as e:
                                    logger.error(e)
                                    continue

                                token = get_account_token(item_service)
                                headers['Authorization'] = f'Bearer {token}'
                                ydl_opts['http_headers'] = headers
                                ydl_opts['outtmpl'] = temp_file_path + f' - {version["audio_locale"]}.%(ext)s.%(ext)s'

                                self.update_progress(item, self.tr("Downloading Video") if self.gui else "Downloading Video", 1)
                                ydl_video_opts = ydl_opts
                                ydl_video_opts['format'] = (f'(bestvideo[height<={config.get("preferred_video_resolution")}][ext=mp4]/bestvideo)')
                                with YoutubeDL(ydl_video_opts) as video:
                                    encrypted_files.append({
                                        'path': video.prepare_filename(video.extract_info(mpd_url, download=False)),
                                        'type': 'video',
                                        'decryption_key': decryption_key,
                                        'language': version['audio_locale']
                                    })
                                    video.download(mpd_url)

                                token = get_account_token(item_service)
                                headers['Authorization'] = f'Bearer {token}'
                                ydl_opts['http_headers'] = headers

                                self.update_progress(item, self.tr("Downloading Audio") if self.gui else "Downloading Audio", 1)
                                ydl_audio_opts = ydl_opts
                                ydl_audio_opts['format'] = ('(bestaudio[ext=m4a]/bestaudio)')
                                with YoutubeDL(ydl_audio_opts) as audio:
                                    encrypted_files.append({
                                        'path': audio.prepare_filename(audio.extract_info(mpd_url, download=False)),
                                        'decryption_key': decryption_key,
                                        'type': 'audio',
                                        'language': version['audio_locale']
                                    })
                                    audio.download(mpd_url)

                                crunchyroll_close_stream(token, item_id, stream_token)

                                # Download Chapters
                                if not config.get('raw_media_download') and config.get('download_chapters'):
                                    self.update_progress(item, self.tr("Downloading Chapters") if self.gui else "Downloading Chapters", 1)
                                    chapter_file = temp_file_path + f' - {version["audio_locale"]}.txt'
                                    if not os.path.exists(chapter_file):
                                        resp = requests.get(f'https://static.crunchyroll.com/skip-events/production/{version["guid"]}.json')
                                        if resp.status_code == 200:
                                            chapter_data = resp.json()
                                            with open(chapter_file, 'w', encoding='utf-8') as file:
                                                file.write(';FFMETADATA1\n')
                                                for entry in ['intro', 'credits']:
                                                    if chapter_data.get(entry):
                                                        file.write(f"[CHAPTER]\nTIMEBASE=1/1\nSTART={chapter_data[entry].get('start')}\nEND={chapter_data[entry].get('end')}\ntitle={entry.title()}\nlanguage={version['audio_locale']}\n")
                                            video_files.append({
                                                'path': chapter_file,
                                                'type': 'chapter',
                                                'format': 'txt',
                                                'language': version['audio_locale']
                                            })

                        self.update_progress(item, self.tr("Decrypting") if self.gui else "Decrypting", 99)

                        for encrypted_file in encrypted_files:
                            decrypted_temp_file_path = os.path.splitext(encrypted_file['path'])[0]
                            video_files.append({
                                "path": decrypted_temp_file_path,
                                "format": os.path.splitext(encrypted_file['path'])[1],
                                "type": encrypted_file['type'],
                                "language": encrypted_file.get('language')
                            })

                            command = [
                                config.get('_ffmpeg_bin_path'),
                                "-loglevel", "error",
                                "-y",
                                "-decryption_key", encrypted_file['decryption_key'],
                                "-i", encrypted_file['path'],
                                "-c", "copy",
                                "-movflags",
                                "+faststart",
                                decrypted_temp_file_path
                            ]
                            if os.name == 'nt':
                                subprocess.check_call(command, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                            else:
                                subprocess.check_call(command, shell=False)

                            if os.path.exists(encrypted_file['path']):
                                os.remove(encrypted_file['path'])

                        # Download Subtitles
                        if config.get("download_subtitles"):
                            item['item_status'] = 'Downloading Subtitles'
                            self.update_progress(item, self.tr("Downloading Subtitles") if self.gui else "Downloading Subtitles", 99)

                            finished_sub_langs = []
                            for subtitle_format in subtitle_formats:
                                lang = subtitle_format['language']
                                if lang in finished_sub_langs:
                                    continue
                                finished_sub_langs.append(lang)
                                if lang in config.get('preferred_subtitle_language').split(',') or config.get('download_all_available_subtitles'):
                                    subtitle_file = temp_file_path + f' - {lang}.{subtitle_format["extension"]}'
                                    if not os.path.exists(subtitle_file):
                                        subtitle_data = requests.get(subtitle_format['url']).text
                                        with open(subtitle_file, 'w', encoding='utf-8') as file:
                                            file.write(subtitle_data)
                                    video_files.append({
                                        'path': subtitle_file,
                                        'type': 'subtitle',
                                        'format': subtitle_format['extension'],
                                        'language': lang
                                    })

                    elif item_service == 'generic':
                        temp_file_path = ''
                        ydl_opts = {}
                        ydl_opts['format'] = (f'(bestvideo[height<={config.get("preferred_video_resolution")}][ext=mp4]+bestaudio[ext=m4a])/'
                                            f'(bestvideo[height<={config.get("preferred_video_resolution")}]+bestaudio)/'
                                            f'best')
                        ydl_opts['quiet'] = True
                        ydl_opts['no_warnings'] = True
                        ydl_opts['noprogress'] = True
                        ydl_opts['outtmpl'] = config.get('video_download_path') + os.path.sep + '%(title)s.%(ext)s'
                        ydl_opts['ffmpeg_location'] = config.get('_ffmpeg_bin_path')
                        ydl_opts['postprocessors'] = [{
                            'key': 'FFmpegMetadata',
                        }]
                        ydl_opts['progress_hooks'] = [lambda d: self.yt_dlp_progress_hook(item, d)]
                        with YoutubeDL(ydl_opts) as video:
                            item['file_path'] = video.prepare_filename(video.extract_info(item_id, download=False))
                            video.download(item_id)

                except RuntimeError as e:
                    logger.info(f"Download failed: {item}, Error: {str(e)}\nTraceback: {traceback.format_exc()}")
                    item['item_status'] = 'Failed'
                    self.update_progress(item, self.tr("Failed") if self.gui else "Failed", 0)
                    self.readd_item_to_download_queue(item)
                    continue

                if item_service != 'generic':
                    item['progress'] = 99
                    # Audio Formatting
                    if item_type in ('track', 'podcast_episode'):
                        # Lyrics
                        if item_service in ("apple_music", "spotify", "tidal") and config.get('download_lyrics'):
                            item['item_status'] = 'Getting Lyrics'
                            self.update_progress(item, self.tr("Getting Lyrics") if self.gui else "Getting Lyrics", 99)
                            extra_metadata = globals()[f"{item_service}_get_lyrics"](token, item_id, item_type, item_metadata, file_path)
                            if isinstance(extra_metadata, dict):
                                item_metadata.update(extra_metadata)

                        if config.get('raw_media_download'):
                            file_path += default_format
                        elif item_type == "track":
                            file_path += "." + config.get("track_file_format")
                        elif item_type == "podcast_episode":
                            file_path += "." + config.get("podcast_file_format")

                        os.rename(temp_file_path, file_path)
                        item['file_path'] = file_path

                        # Convert file format and embed metadata
                        if not config.get('raw_media_download'):
                            item['item_status'] = 'Converting'
                            self.update_progress(item, self.tr("Converting") if self.gui else "Converting", 99)

                            if config.get('use_custom_file_bitrate'):
                                bitrate = config.get("file_bitrate")
                            convert_audio_format(file_path, bitrate, default_format)

                            embed_metadata(item, item_metadata)

                            # Thumbnail
                            if config.get('save_album_cover') or config.get('embed_cover'):
                                item['item_status'] = 'Setting Thumbnail'
                                self.update_progress(item, self.tr("Setting Thumbnail") if self.gui else "Setting Thumbnail", 99)
                                set_music_thumbnail(file_path, item_metadata)

                            if os.path.splitext(file_path)[1] == '.mp3':
                                fix_mp3_metadata(file_path)
                        else:
                            if config.get('save_album_cover'):
                                item['item_status'] = 'Setting Thumbnail'
                                self.update_progress(item, self.tr("Setting Thumbnail") if self.gui else "Setting Thumbnail", 99)
                                set_music_thumbnail(file_path, item_metadata)

                        # M3U
                        if config.get('create_m3u_file') and item.get('parent_category') == 'playlist':
                            item['item_status'] = 'Adding To M3U'
                            self.update_progress(item, self.tr("Adding To M3U") if self.gui else "Adding To M3U", 99)
                            add_to_m3u_file(item, item_metadata)

                    # Video Formatting
                    elif item_type in ('movie', 'episode'):
                        for file in video_files:
                            final_path = file['path'].replace('~', '')
                            os.rename(file['path'], final_path)
                            file['path'] = final_path

                        if not config.get("raw_media_download"):
                            item['item_status'] = 'Converting'
                            self.update_progress(item, self.tr("Converting") if self.gui else "Converting", 99)
                            if item_type == "episode":
                                output_format = config.get("show_file_format")
                            elif item_type == "movie":
                                output_format = config.get("movie_file_format")
                            convert_video_format(item, file_path, output_format, video_files, item_metadata)
                            item['file_path'] = file_path + '.' + output_format
                        else:
                            item['file_path'] = file_path + '.mp4'

                item['item_status'] = 'Downloaded'
                logger.info("Item Successfully Downloaded")
                item['progress'] = 100
                self.update_progress(item, self.tr("Downloaded") if self.gui else "Downloaded", 100)
                try:
                    config.set('total_downloaded_data', config.get('total_downloaded_data') + os.path.getsize(item['file_path']))
                    config.set('total_downloaded_items', config.get('total_downloaded_items') + 1)
                    config.save()
                except Exception:
                    pass
                time.sleep(config.get("download_delay"))
                self.readd_item_to_download_queue(item)
                continue
            except Exception as e:
                logger.error(f"Unknown Exception: {str(e)}\nTraceback: {traceback.format_exc()}")
                if item['item_status'] != "Cancelled":
                    item['item_status'] = "Failed"
                    self.update_progress(item, self.tr("Failed") if self.gui else "Failed", 0)
                else:
                    self.update_progress(item, self.tr("Cancelled") if self.gui else "Cancelled", 0)

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
