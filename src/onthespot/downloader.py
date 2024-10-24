import os
import traceback
import time
import subprocess
from requests.exceptions import MissingSchema
from PyQt6.QtCore import QThread, pyqtSignal
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.metadata import TrackId, EpisodeId
from .runtimedata import get_logger, download_queue
from .otsconfig import config
from .post_download import convert_audio_format, set_audio_tags, set_music_thumbnail
from .api.spotify import spotify_get_token, spotify_get_track_metadata, spotify_get_episode_metadata, spotify_get_lyrics
from .api.soundcloud import soundcloud_get_token, soundcloud_get_track_metadata
from .accounts import get_account_token
from .utils import sanitize_data, conv_list_format, format_track_path

logger = get_logger("spotify.downloader")


class DownloadWorker(QThread):
    progress = pyqtSignal(dict, str, int)
    def __init__(self, gui=False):
        self.gui = gui
        super().__init__()


    def run(self):
        while True:
            if download_queue:
                try:
                    try:
                        item = download_queue.pop(next(iter(download_queue)))
                        item_service = item['item_service']
                        item_type = item['item_type']
                        item_id = item['item_id']
                        # Move item to bottom of download list after processing
                        download_queue[item_id] = item
                        status = item['gui']['status_label'].text()
                        if status in (
                            self.tr("Cancelled"),
                            self.tr("Failed"),
                            self.tr("Unavailable"),
                            self.tr("Downloaded"),
                            self.tr("Already Exists")
                        ):
                            time.sleep(1)
                            continue
                    except (RuntimeError, OSError):
                        # Item likely cleared from download queue.
                        continue

                    if self.gui:
                        self.progress.emit(item, self.tr("Downloading"), 0)

                    token = get_account_token(download=True)

                    try:
                        item_metadata = globals()[f"{item_service}_get_{item_type}_metadata"](token, item_id)

                        item_path = format_track_path(item_metadata, item_service, item_type, item['is_playlist_item'], item['playlist_name'], item['playlist_by'])

                    except (Exception, KeyError):
                        logger.error(
                            f"Metadata fetching failed for track by id '{item_id}', {traceback.format_exc()}")
                        self.progress.emit(item, self.tr("Failed"), 0)
                        continue

                    dl_root = config.get("download_root")
                    file_path = os.path.join(dl_root, item_path)

                    os.makedirs(os.path.dirname(file_path), exist_ok=True)

                    item['file_path'] = file_path

                    # M3U
                    if config.get('create_m3u_playlists') and item.get('is_playlist_item', False):
                        if self.gui:
                            self.progress.emit(item, self.tr("Adding To M3U"), 0)

                        path = config.get("m3u_name_formatter")
                        m3u_file = path.format(
                        playlist_name=sanitize_data(item['playlist_name']),
                        playlist_owner=sanitize_data(item['playlist_by']),
                        )

                        m3u_file += "." + config.get("m3u_format")

                        dl_root = config.get("download_root")
                        m3u_path = os.path.join(dl_root, m3u_file)

                        os.makedirs(os.path.dirname(m3u_path), exist_ok=True)

                        if not os.path.exists(m3u_path):
                            with open(m3u_path, 'w') as m3u_file:
                                m3u_file.write("#EXTM3U\n")

                        # Check if the item_path is already in the M3U file  
                        with open(m3u_path, 'r') as m3u_file:
                            m3u_contents = m3u_file.readlines()

                            if file_path not in [line.strip() for line in m3u_contents]:
                                with open(m3u_path, 'a') as m3u_file:
                                    m3u_file.write(f"#EXTINF:-1, {item_metadata['artists']} - {item_metadata['title']}\n{file_path}\n")


                    # Skip download if file exists under different extension
                    file_directory = os.path.dirname(file_path)
                    base_file_path = os.path.splitext(os.path.basename(file_path))[0]

                    try:
                        files_in_directory = os.listdir(file_directory)  # Attempt to list files  
                        matching_files = [file for file in files_in_directory if file.startswith(base_file_path) and not file.endswith('.lrc')]
                        
                        if matching_files:
                            if self.gui:
                                if item['gui']['status_label'].text() == self.tr("Downloading"):
                                    self.progress.emit(item, self.tr("Already Exists"), 100)  # Emit progress
                            logger.info(f"File already exists, Skipping download for track by id '{item_id}'")
                            time.sleep(1)
                            continue
                    except FileNotFoundError:
                        logger.info(f"File does not already exist.")

                    if not item_metadata['is_playable']:
                        logger.error(f"Track is unavailable, track id '{item_id}'")
                        if self.gui:
                            self.progress.emit(item, self.tr("Unavailable"), 0)
                        continue

                    # Downloading the file here is necessary to animate progress bar through pyqtsignal.
                    # Could at some point just update the item manually inside the api file by passing
                    # item['gui']['progressbar'] and self.gui into a download_track function.
                    try:
                        if item_service == "spotify":
                            if item_type == "track":
                                audio_key = TrackId.from_base62(item_id)
                            elif item_type == "episode":
                                audio_key = EpisodeId.from_base62(item_id)

                            quality = AudioQuality.HIGH
                            if token.get_user_attribute("type") == "premium" and item_type == 'track':
                                quality = AudioQuality.VERY_HIGH

                            stream = token.content_feeder().load(audio_key, VorbisOnlyAudioQuality(quality), False, None)

                            total_size = stream.input_stream.size
                            downloaded = 0
                            _CHUNK_SIZE = config.get("chunk_size")

                            with open(file_path, 'wb') as file:
                                while downloaded < total_size:
                                    data = stream.input_stream.stream().read(_CHUNK_SIZE)
                                    downloaded += len(data)
                                    if len(data) != 0:
                                        file.write(data)
                                        if self.gui:
                                            self.progress.emit(item, self.tr("Downloading"), int((downloaded / total_size) * 100))
                                    if len(data) == 0:
                                        break  # Exit if no more data is being read  
                            default_format = ".ogg"
                            bitrate = "320k" if quality == AudioQuality.VERY_HIGH else "160k"

                        elif item_service == "soundcloud":
                            command = [config.get('_ffmpeg_bin_path'), "-loglevel", "error", "-i", f"{item_metadata['file_url']}", "-c", "copy", file_path]
                            if os.name == 'nt':
                                subprocess.check_call(command, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                            else:
                                subprocess.check_call(command, shell=False)


                            default_format = ".mp3"
                            bitrate = "128k"

                    except (RuntimeError):
                        # Likely Ratelimit
                        logger.info("Download failed: {item}")
                        self.progress.emit(item, self.tr("Failed"), 0)
                        continue

                    # Convert File Format
                    if self.gui:
                        self.progress.emit(item, self.tr("Converting"), 99)
                    convert_audio_format(file_path, bitrate, default_format)

                    # Set Audio Tags
                    if self.gui:
                        self.progress.emit(item, self.tr("Embedding Metadata"), 99)
                    set_audio_tags(file_path, item_metadata, item_id)

                    # Thumbnail
                    if self.gui:
                        self.progress.emit(item, self.tr("Setting Thumbnail"), 99)
                    try:
                        set_music_thumbnail(file_path, item_metadata['image_url'])
                    except MissingSchema:
                        self.progress.emit(item, self.tr("Failed To Set Thumbnail"), 99)

                    # Lyrics
                    if item_service == "spotify":
                        if self.gui:
                            self.progress.emit(item, self.tr("Getting Lyrics"), 99)
                        globals()[f"{item_service}_get_lyrics"](token, item_id, item_type, item_metadata, file_path)

                    if self.gui:
                        self.progress.emit(item, self.tr("Downloaded"), 100)
                    time.sleep(config.get("download_delay"))
                except Exception as e:
                    self.progress.emit(item, self.tr("Failed"), 0)
                    logger.error(f"Unknown Exception: {str(e)}")
                    continue
            else:
                time.sleep(1)
