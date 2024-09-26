import os
import queue
import socket
import subprocess
import time
import traceback

import requests
from PyQt6.QtCore import QObject, pyqtSignal
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.metadata import TrackId, EpisodeId
from urllib3.exceptions import MaxRetryError, NewConnectionError

from ..otsconfig import config
from ..runtimedata import get_logger, cancel_list, failed_downloads, unavailable, session_pool
from ..utils.spotify import check_premium, get_song_info, convert_audio_format, set_music_thumbnail, set_audio_tags, \
    get_episode_info, get_track_lyrics
from ..utils.utils import re_init_session, fetch_account_uuid


class DownloadWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(list)

    name = None
    logger = None
    __session_uuid = None
    __queue = None
    __stop = False
    __last_cancelled = False
    __stopped = False

    def download_track(self, session, track_id_str, extra_paths="", extra_path_as_root=False,
                       playlist_name='', playlist_owner='', playlist_desc=''):
        trk_track_id_str = track_id_str
        self.logger.debug(
            f"Downloading track by id '{track_id_str}', extra_paths: '{extra_paths}', "
            f"extra_path_as_root: '{extra_path_as_root}' ")
        if trk_track_id_str in cancel_list:
            self.logger.info(f'The media : {trk_track_id_str} was cancelled !')
            self.progress.emit([trk_track_id_str, self.tr("Cancelled"), [0, 100]])
            cancel_list.pop(trk_track_id_str)
            failed_downloads[trk_track_id_str] = {}
            self.__last_cancelled = True
            return False
        skip_existing_file = True
        chunk_size = config.get("chunk_size")
        quality = AudioQuality.HIGH
        if check_premium(session) or config.get('force_premium'):
            quality = AudioQuality.VERY_HIGH

        try:
            song_info = get_song_info(session, track_id_str)

            if config.get("translate_file_path"):
                from googletrans import Translator
                _name = Translator().translate(song_info['name'], src="auto", dest=config.get("language")).text
                _album = Translator().translate(song_info['album_name'], src="auto", dest=config.get("language")).text
            else:
                _name = song_info['name']
                _album=song_info['album_name']

            _artist = song_info['artists'][0]

            if playlist_name != None and config.get("use_playlist_path"):
                song_name = config.get("playlist_path_formatter").format(
                    artist=_artist,
                    album=_album,
                    name=_name,
                    rel_year=song_info['release_year'],
                    disc_number=song_info['disc_number'],
                    track_number=song_info['track_number'],
                    spotid=song_info['scraped_song_id'],
                    genre=song_info['genre'][0] if len(song_info['genre']) > 0 else '',
                    label=song_info['label'],
                    explicit=str(config.get('explicit')) if song_info['explicit'] else '',
                    trackcount=song_info['total_tracks'],
                    disccount=song_info['total_discs'],
                    playlist_name=playlist_name,
                    playlist_owner=playlist_owner,
                    playlist_desc=playlist_desc
                )
            else:
                song_name = config.get("track_path_formatter").format(
                    artist=_artist,
                    album=_album,
                    name=_name,
                    rel_year=song_info['release_year'],
                    disc_number=song_info['disc_number'],
                    track_number=song_info['track_number'],
                    spotid=song_info['scraped_song_id'],
                    genre=song_info['genre'][0] if len(song_info['genre']) > 0 else '',
                    label=song_info['label'],
                    explicit=str(config.get('explicit')) if song_info['explicit'] else '',
                    trackcount=song_info['total_tracks'],
                    disccount=song_info['total_discs'],
                    playlist_name=playlist_name,
                    playlist_owner=playlist_owner,
                    playlist_desc=playlist_desc
                )

            if not config.get("force_raw"):
                song_name = song_name + "." + config.get("media_format")
            else:
                song_name = song_name + ".ogg"

            dl_root = os.path.abspath(extra_paths) if extra_path_as_root else config.get("download_root")
            # If extra path as root is enabled, extra path is already set as DL root, unset it
            extra_paths = '' if extra_path_as_root else extra_paths.strip()
            filename = os.path.join(dl_root, extra_paths, song_name)
        except Exception:
            self.logger.error(
                f"Metadata fetching failed for track by id '{trk_track_id_str}', {traceback.format_exc()}")
            self.progress.emit([trk_track_id_str, self.tr("Get metadata failed"), [0, 100]])
            return False
        try:
            if not song_info['is_playable']:
                self.logger.error(f"Track is unavailable, track id '{trk_track_id_str}'")
                self.progress.emit([trk_track_id_str, self.tr("Unavailable"), [0, 100]])
                unavailable.add(trk_track_id_str)
                # Do not wait for n second before next download
                self.__last_cancelled = True
                return False
            else:
                if os.path.isfile(filename) and os.path.getsize(filename) and skip_existing_file:
                    self.progress.emit([trk_track_id_str, self.tr("Already exists"), [100, 100],
                                        filename,
                                        f'{song_info["name"]} [{_artist} - {song_info["album_name"]}:{song_info["release_year"]}].f{config.get("media_format")}'])
                    self.logger.info(f"File already exists, Skipping download for track by id '{trk_track_id_str}'")
                    self.__last_cancelled = True
                    return True
                else:
                    if track_id_str != song_info['scraped_song_id']:
                        track_id_str = song_info['scraped_song_id']

                    track_id = TrackId.from_base62(track_id_str)
                    stream = session.content_feeder().load(track_id, VorbisOnlyAudioQuality(quality), False, None)
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                    total_size = stream.input_stream.size
                    downloaded = 0
                    _CHUNK_SIZE = chunk_size
                    fail = 0
                    with open(filename, 'wb') as file:
                        while downloaded < total_size:
                            if trk_track_id_str in cancel_list:
                                self.progress.emit([trk_track_id_str, self.tr("Cancelled"), [0, 100]])
                                cancel_list.pop(trk_track_id_str)
                                self.__last_cancelled = True
                                if os.path.exists(filename):
                                    file.close()
                                    os.remove(filename)
                                return False
                            self.logger.debug(
                                f"Reading chunk of {_CHUNK_SIZE} bytes from stream  track by id '{trk_track_id_str}'")
                            data = stream.input_stream.stream().read(_CHUNK_SIZE)
                            self.logger.debug(
                                f"Got {len(data)} bytes of data for track by id '{trk_track_id_str}'")
                            downloaded += len(data)
                            if len(data) != 0:
                                file.write(data)
                                self.progress.emit([trk_track_id_str, None, [downloaded, total_size]])
                            if len(data) == 0 and _CHUNK_SIZE > config.get("dl_end_padding_bytes"):
                                self.logger.error(
                                    f"PD Error for track by id '{trk_track_id_str}', "
                                    f"while reading chunk size: {_CHUNK_SIZE}"
                                )
                                fail += 1
                            elif len(data) == 0 and _CHUNK_SIZE <= config.get("dl_end_padding_bytes"):
                                break
                            if (total_size - downloaded) < _CHUNK_SIZE:
                                _CHUNK_SIZE = total_size - downloaded
                            if fail > config.get("max_retries"):
                                self.progress.emit([trk_track_id_str, self.tr("RETRY ") + str(fail + 1), None])
                                self.logger.error(f"Max retries exceed for track by id '{trk_track_id_str}'")
                                self.progress.emit([trk_track_id_str, self.tr("PD error. Will retry"), None])
                                if os.path.exists(filename):
                                    os.remove(filename)
                                return None
                            self.progress.emit([trk_track_id_str, None, [downloaded, total_size]])
                    if not config.get("force_raw"):
                        self.progress.emit([trk_track_id_str, self.tr("Converting"), None])
                        convert_audio_format(filename, quality)
                        self.progress.emit([trk_track_id_str, self.tr("Writing metadata"), None])
                        set_audio_tags(filename, song_info, trk_track_id_str)
                        self.progress.emit([trk_track_id_str, self.tr("Setting thumbnail"), None])
                        set_music_thumbnail(filename, song_info['image_url'])
                    else:
                        self.logger.warning(
                            f"Force raw is disabled for track by id '{trk_track_id_str}', "
                            f"media converting and tagging will be done !"
                        )
                    self.logger.info(f"Downloaded track by id '{trk_track_id_str}'")
                    if config.get('inp_enable_lyrics'):
                        self.progress.emit([trk_track_id_str, self.tr("Getting Lyrics"), None])
                        self.logger.info(f'Fetching lyrics for track id: {trk_track_id_str}, '
                                         f'{config.get("only_synced_lyrics")}')
                        try:
                            lyrics = get_track_lyrics(session, trk_track_id_str, song_info, config.get('only_synced_lyrics'))
                            if lyrics:
                                self.logger.info(f'Found lyrics for: {trk_track_id_str}, writing...')
                                if config.get('use_lrc_file'):
                                    with open(filename[0:-len(config.get('media_format'))] + 'lrc', 'w',
                                              encoding='utf-8') as f:
                                        f.write(lyrics)
                                if config.get('embed_lyrics'):
                                    set_audio_tags(filename, {'lyrics': lyrics}, trk_track_id_str)
                                self.logger.info(f'lyrics saved for: {trk_track_id_str}')
                        except Exception:
                            self.logger.error(f'Could not get lyrics for {trk_track_id_str}, '
                                              f'unexpected error: {traceback.format_exc()}')
                    self.progress.emit([trk_track_id_str, self.tr("Downloaded"), [100, 100],
                                        filename,
                                        f'{song_info["name"]} [{_artist} - {song_info["album_name"]}:{song_info["release_year"]}].f{config.get("media_format")}'])
                    return True
        except queue.Empty:
            if os.path.exists(filename):
                os.remove(filename)
            self.logger.error(
                f"Network timeout from spotify for track by id '{trk_track_id_str}', download will be retried !")
            self.progress.emit([trk_track_id_str, self.tr("Timeout. Will retry"), None])
            return None
        except subprocess.CalledProcessError as exc:
            if os.path.exists(filename):
                os.remove(filename)
            self.logger.error(
                f"Decoding error for track by id '{trk_track_id_str}', "
                f"possibly due to use of rate limited spotify account ! {exc.returncode} | {exc.output}"
            )
            self.progress.emit([trk_track_id_str, self.tr("Decode error. Will retry"), None])
            traceback.print_exc()
            return None
        except Exception:
            if os.path.exists(filename):
                os.remove(filename)
            self.progress.emit([trk_track_id_str, self.tr("Failed"), [0, 100]])
            self.logger.error(
                f"Download failed for track by id '{trk_track_id_str}', Unexpected error: {traceback.format_exc()} !")
            return False

    def download_episode(self, session, episode_id_str, extra_paths="", extra_path_as_root=False):
        self.logger.info(f"Downloading episode by id '{episode_id_str}'")
        quality = AudioQuality.HIGH
        podcast_name, episode_name, thumbnail, release_date, total_episodes, artist, language, description, copyright = get_episode_info(session, episode_id_str)
        skip_existing_file = True
        if extra_paths == "":
            extra_paths = os.path.join(extra_paths, podcast_name)
        if podcast_name is None:
            self.progress.emit([episode_id_str, self.tr("Not Found"), [0, 100]])
            self.logger.error(f"Download failed for episode by id '{episode_id_str}', Not found")
            return False
        else:
            try:
                filename = podcast_name + " - " + episode_name
                episode_id = EpisodeId.from_base62(episode_id_str)
                stream = session.content_feeder().load(episode_id, VorbisOnlyAudioQuality(quality), False, None)
                total_size = stream.input_stream.size
                downloaded = 0
                _CHUNK_SIZE = config.get("chunk_size")
                fail = 0

                audio_name = config.get("podcast_path_formatter").format(
                    artist=artist,
                    podcast_name=podcast_name,
                    episode_name=episode_name,
                    episode_id=episode_id,
                    release_date=release_date,
                    total_episodes=total_episodes,
                    language=language
                )

                if not config.get("force_raw"):
                    audio_name = audio_name + "." + config.get("podcast_media_format")
                else:
                    audio_name = audio_name + ".ogg"

                extra_paths = '' if extra_path_as_root else extra_paths
                file_path = os.path.abspath(extra_paths) if extra_path_as_root else os.path.join(config.get("download_root"), audio_name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                if os.path.isfile(file_path) and os.path.getsize(file_path) and skip_existing_file:
                    self.logger.info(f"Episode by id '{episode_id_str}', already exists.. Skipping ")
                    self.progress.emit([episode_id_str, self.tr("Downloaded"), [100, 100], file_path, filename])
                    return True
                with open(file_path, 'wb') as file:
                    while downloaded <= total_size:
                        if episode_id_str in cancel_list:
                            self.progress.emit([episode_id_str, self.tr("Cancelled"), [0, 100]])
                            cancel_list.pop(episode_id_str)
                            self.__last_cancelled = True
                            if os.path.exists(file_path):
                                file.close()
                                os.remove(file_path)
                            return False
                        data = stream.input_stream.stream().read(_CHUNK_SIZE)
                        downloaded += len(data)
                        file.write(data)
                        self.progress.emit([episode_id_str, None, [downloaded, total_size], file_path, filename])
                        if (total_size - downloaded) < _CHUNK_SIZE:
                            _CHUNK_SIZE = total_size - downloaded
                        if len(data) == 0:
                            fail += 1
                        if fail > config.get("max_retries"):
                            self.progress.emit([episode_id_str, self.tr("RETRY ") + str(fail + 1), None])
                            break
                self.logger.info(f"Episode by id '{episode_id_str}', downloaded")
                if not config.get("force_raw"):
                    self.progress.emit([episode_id_str, self.tr("Converting"), None, file_path, filename])
                    convert_audio_format(file_path, quality)
                self.logger.info(f'Writing metadata for episode "{episode_id_str}" ')
                self.progress.emit([episode_id_str, self.tr("Writing metadata"), None, file_path, filename])
                set_audio_tags(
                    file_path,
                    {
                        'name': episode_name,
                        'album_name': podcast_name,
                        'release_year': release_date,
                        'total_tracks': total_episodes,
                        'artists': [artist],
                        'genre': ['Podcast'],
                        'language': language,
                        'description': description,
                        'copyright': copyright
                    },
                    episode_id_str
                )
                self.progress.emit([episode_id_str, self.tr("Setting thumbnail"), None, file_path, filename])
                self.logger.info(f'Setting thumbnail for episode "{episode_id_str}" ')
                set_music_thumbnail(file_path, thumbnail)
                self.progress.emit([episode_id_str, self.tr("Downloaded"), [100, 100], file_path, filename])
                return True
            except subprocess.CalledProcessError as exc:
                if os.path.exists(file_path):
                    os.remove(file_path)
                self.logger.error(
                    f"Decoding error for track by id '{episode_id_str}', "
                    f"possibly due to use of rate limited spotify account ! {exc.returncode} | {exc.output}"
                )
                self.progress.emit([episode_id_str, self.tr("Decode error. Will retry"), None])
                traceback.print_exc()
                return None
            except Exception:
                self.logger.error(
                    f"Downloading failed for episode by id "
                    f"'{episode_id_str}', Unexpected Exception: {traceback.format_exc()}"
                )
                self.progress.emit([episode_id_str, self.tr("Failed"), [0, 100]])
                return False

    def run(self):
        self.logger.info(f"Download worker {self.name} is running ")
        while not self.__stop:
            item = None
            while not self.__stop :
                try:
                    item = self.__queue.get(timeout=0.2)
                    break
                except queue.Empty:
                    pass
            if self.__stop:
                break
            attempt = 0
            self.__last_cancelled = status = False
            while attempt < config.get("max_retries") and status is not True and item is not None:
                self.logger.info(f"Processing download for track by id '{item['media_id']}', Attempt: {attempt}/{config.get('max_retries')}")
                attempt = attempt + 1
                status = False
                download = True
                selected_uuid = fetch_account_uuid(download)
                self.progress.emit([item['media_id'], self.tr("Downloading"), None])
                try:
                    if item['media_type'] == "track":
                        status = self.download_track(
                            session=session_pool[selected_uuid],
                            track_id_str=item['media_id'],
                            extra_paths=item['extra_paths'],
                            extra_path_as_root=item['extra_path_as_root'],
                            playlist_name=item['playlist_name'],
                            playlist_owner=item['playlist_owner'],
                            playlist_desc=item['playlist_desc'],
                        )
                    elif item['media_type'] == "episode":
                        status = self.download_episode(
                            session=session_pool[selected_uuid],
                            episode_id_str=item['media_id'],
                            extra_paths=item['extra_paths'],
                            extra_path_as_root=item['extra_path_as_root'],
                        )
                    else:
                        attempt = 1000 + config.get("max_retries")
                except (OSError, queue.Empty, MaxRetryError, NewConnectionError, ConnectionError, socket.gaierror,
                        ConnectionResetError):
                    # Internet disconnected ?
                    self.logger.error(f'DL failed.. Connection error ! Trying to re init account session {self.__session_uuid} ! ')
                    re_init_session(session_pool, self.__session_uuid, wait_connectivity=True, timeout=120)

                if status is None:  # This needs to be cleaned up, current versions retry for False too
                    if attempt < config.get("max_retries"):  # 2 < 2
                        wait_ = int(time.time()) + config.get("recoverable_fail_wait_delay")
                        while wait_ - int(time.time()) > 0:
                            self.logger.error(f"Retrying '{item['media_id']}' in {wait_ - int(time.time())} sec")
                            self.progress.emit(
                                [item['media_id'], self.tr("Retrying in {0} sec").format(wait_ - int(time.time())), [0, 100]]
                            )
                            time.sleep(1)
                    else:
                        status = False
                if status is False:
                    self.logger.error(f"Download process returned false: {item['media_id']}")
                    if attempt >= config.get("max_retries") or self.__last_cancelled:
                        self.logger.debug('Download was failed or cancelled make it available for retry then leave')
                        if attempt == 1000 + config.get("max_retries"):
                            # This was invalid media download type item on queue, to not retry
                            break
                        else:
                            failed_downloads[item['media_id']] = item
                        break
                    # Else, It was not cancelled, download just failed ! Retry until we hit max retries
            if not self.__last_cancelled:
                time.sleep(config.get("download_delay"))
        self.__stopped = True
        self.logger.info(f"Download worker {self.name} is stopping ")
        self.finished.emit()

    def setup(self, thread_name, session_uuid, queue_tracks):
        self.name = thread_name
        self.__session_uuid = session_uuid
        self.__queue = queue_tracks
        self.logger = get_logger(f"worker.downloader.{thread_name}")

    def stop(self):
        self.logger.warn('Got signal to stop, signaling main func to stop right after current job')
        self.__stop = True

    def is_stopped(self):
        return self.__stopped
