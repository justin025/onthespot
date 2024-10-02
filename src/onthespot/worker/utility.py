import os
import queue
import time
from PyQt6.QtCore import QObject, pyqtSignal
from urllib3.exceptions import MaxRetryError, NewConnectionError

from ..otsconfig import config
from ..runtimedata import get_logger, playlist_m3u_queue, downloaded_data, session_pool, unavailable
from ..utils.spotify import get_album_tracks, get_album_name, get_artist_albums, get_show_episodes, get_episode_info, \
    get_song_info, get_tracks_from_playlist, get_playlist_data, sanitize_data
from ..utils.utils import re_init_session, fetch_account_uuid

logger = get_logger("worker.utility")


class PlayListMaker(QObject):
    changed_media = pyqtSignal(str, bool)
    finished = pyqtSignal()
    __stop = False

    def run(self):
        logger.info('Playlist m3u8 builder is running....')
        while not self.__stop:
            downloaded_and_available = set(downloaded_data.keys()).difference(unavailable)
            for play_id in list(playlist_m3u_queue.keys()):
                logger.info(f'Playlist m3u8 checking ID {play_id}')
                # Remove unavailable tracks from playlist items and see if all of its item are available in
                # downloaded_and_available set
                all_downloadable_in_playlist = set(playlist_m3u_queue[play_id]['tracks']).difference(unavailable)
                if all_downloadable_in_playlist.issubset(downloaded_and_available):
                    logger.info(f'Playlist {play_id} has all items ready, making m3u8 playlist at: '
                                f'{{play_queue[play_id]["filename"]}}!')
                    # Write the m3u8 header
                    os.makedirs(os.path.dirname(playlist_m3u_queue[play_id]['filename']), exist_ok=True)
                    with open(playlist_m3u_queue[play_id]['filename'], 'w', encoding='UTF-8') as f:
                        f.write('#EXTM3U\n')
                    tid = 1
                    for track_id in playlist_m3u_queue[play_id]['tracks']:
                        logger.info(f'Playlist: {play_id}, adding track: {track_id} to m3u8')
                        if track_id in unavailable:
                            logger.info(f'Playlist: {play_id}, track: {track_id}  unavailable for adding, skipping')
                            continue
                        with open(playlist_m3u_queue[play_id]['filename'], 'a', encoding='UTF-8') as f:
                            f.write(
                                f'#EXTINF:{tid}, {downloaded_data[track_id]["media_name"]}\n'
                                f'{downloaded_data[track_id]["media_path"]}\n'
                            )
                        tid = tid + 1
                    logger.info(f'Playlist: {play_id} created, removing fro queue list')
                    playlist_m3u_queue.pop(play_id)
                else:
                    logger.info(f"Playlist {play_id} has some items left to download")
            time.sleep(4)
        self.finished.emit()

    def stop(self):
        self.__stop = True


class ParsingQueueProcessor(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    enqueue = pyqtSignal(dict)
    __queue = None
    __stop = True

    def enqueue_tracks(self, track_list, enqueue_part_cfg, log_id='', item_type=''):
        for track in track_list:
            logger.info(f'PQP parsing {log_id} <-> track item: {track["name"]}:{track["id"]}')
            exp = config.get("explicit_label") if track['explicit'] else ''
            self.enqueue.emit(
                {
                    'item_id': track['id'],
                    'item_title': f'{exp} {track["name"]}',
                    'item_by_text': f"{config.get('metadata_seperator').join([artist['name'] for artist in track.get('artists', [])])}",
                    'item_type_text': item_type,
                    'dl_params': {
                        'media_type': 'track',
                        'extra_paths': enqueue_part_cfg.get('extra_paths', ''),
                        'extra_path_as_root': bool(enqueue_part_cfg.get('extra_path_as_root', False)),
                        'playlist_name': enqueue_part_cfg.get('playlist_name', ''),
                        'playlist_owner': enqueue_part_cfg.get('playlist_owner', ''),
                        'playlist_desc': enqueue_part_cfg.get('playlist_desc', ''),
                    }
                }
            )

    def run(self):
        logger.info('Parsing queue processor is active !')
        while not self.__stop:
            logger.info('Waiting for new item to parse')
            item = self.__queue.get()
            download = False
            selected_uuid = fetch_account_uuid(download)
            logger.debug(f'Got data to parse: {str(item)}')
            try:
                session = session_pool[selected_uuid]
                logger.info(f'{session}')
                enqueue_part_cfg = {
                        'extra_paths': item['data'].get('dl_path', ''),
                        'extra_path_as_root': item['data'].get('dl_path_is_root', False),
                }
                if item['media_type'] == 'album':
                    artist, album_release_date, album_name, total_tracks = get_album_name(session, item['media_id'])
                    item_name = item['data'].get('media_title', album_name)
                    if not item['data'].get('hide_dialogs', False):
                        self.progress.emit(
                            self.tr('Tracks in album {0} is being parsed and will be added to download queue shortly !'
                        ).format(item_name))
                    tracks = get_album_tracks(session, item['media_id'])
                    logger.info("Passing control to track downloader.py for album tracks downloading !!")
                    self.enqueue_tracks(tracks, enqueue_part_cfg=enqueue_part_cfg,
                                        log_id=f'{album_name}:{item["media_id"]}',
                                        item_type=f"Album [{album_release_date}][{album_name}]")
                    if not item['data'].get('hide_dialogs', False):
                        self.progress.emit(self.tr("Added album {0} to download queue !").format(album_name))
                elif item['media_type'] == 'artist':
                    item_name = item['data'].get('media_title', 'the artist')
                    if not item['data'].get('hide_dialogs', False):
                        self.progress.emit(self.tr("All albums by {0} are being parsed and will be added to download queue soon!").format(item_name))
                    albums = get_artist_albums(session, item['media_id'])
                    for album_id in albums:
                        artist, album_release_date, album_name, total_tracks = get_album_name(session, album_id)
                        item_name = artist
                        tracks = get_album_tracks(session, album_id)
                        logger.info("Passing control to track downloader.py for album artist downloading !!")
                        self.enqueue_tracks(tracks, enqueue_part_cfg=enqueue_part_cfg,
                                            log_id=f'{artist}:{item["media_id"]}', item_type=f"Artist [{item_name}]")
                    if not item['data'].get('hide_dialogs', False):
                        self.progress.emit(self.tr("Added tracks by artist '{0}' to download queue !").format(item_name))
                elif item['media_type'] == 'podcast':
                    show_name = ''
                    if not item['data'].get('hide_dialogs', False):
                        self.progress.emit(self.tr('Episodes are being parsed and will be added to download queue shortly !'))
                    for episode_id in get_show_episodes(session, item['media_id']):
                        show_name, episode_name, thumbnail, release_date, total_episodes, artist, language, description, copyright = get_episode_info(session, episode_id)
                        logger.info(
                            f"PQP parsing podcast : {show_name}:{item['media_id']}, "
                            f"episode item: {episode_name}:{episode_id}"
                        )
                        # TODO: Use new enqueue method
                        self.enqueue.emit(
                            {
                                'item_id': episode_id,
                                'item_title': episode_name,
                                'item_by_text': '',
                                'item_type_text': f"Podcast [{show_name}]",
                                'dl_params': {
                                    'media_type': 'episode',
                                    'extra_paths': item['data'].get('dl_path', ''),
                                    'extra_path_as_root': item['data'].get('dl_path_is_root', False),
                                }
                            }
                        )
                    if not item['data'].get('hide_dialogs', False):
                        self.progress.emit(self.tr("Added show {0} to download queue!").format(show_name))
                elif item['media_type'] == 'episode':
                    podcast_name, episode_name, thumbnail, release_date, total_episodes, artist, language, description, copyright = get_episode_info(session, item['media_id'])
                    logger.info(f"PQP parsing podcast episode : {episode_name}:{item['media_id']}")
                    if not item['data'].get('hide_dialogs', False):
                        self.progress.emit(self.tr("Adding episode {0} to download queue !").format(episode_name))
                    # TODO: Use new enqueue method
                    self.enqueue.emit(
                        {
                            'item_id': item['media_id'],
                            'item_title': episode_name,
                            'item_by_text': '',
                            'item_type_text': f"Podcast [{podcast_name}]",
                            'dl_params': {
                                'media_type': 'episode',
                                'extra_paths': item['data'].get('dl_path', ''),
                                'extra_path_as_root': item['data'].get('dl_path_is_root', False),
                            }
                        }
                    )
                    if not item['data'].get('hide_dialogs', False):
                        self.progress.emit(self.tr("Added {0} to download queue!").format(podcast_name))
                elif item['media_type'] == "playlist":
                    enable_m3u = config.get('create_m3u_playlists', False)
                    name, owner, description, url = get_playlist_data(session, item["media_id"])
                    item_name = item['data'].get('media_title', name)
                    if not item['data'].get('hide_dialogs', False):
                        self.progress.emit(self.tr("Tracks in playlist '{0}' are being parsed \n and will be added to download queue shortly!").format(item_name))
                    playlist_songs = get_tracks_from_playlist(session,
                                                              item['media_id'])
                    enqueue_part_cfg.update({
                        'playlist_name': name,
                        'playlist_owner': owner,
                        'playlist_desc': description
                    })
                    if enable_m3u:
                        playlist_m3u_queue[item['media_id']] = {
                            'filename': os.path.abspath(
                                os.path.join(
                                    config.get('download_root'),
                                    config.get('m3u_name_formatter').format(name=name, owner=owner,
                                                                                 description=description) + ".m3u8")
                            ),
                            'tracks': []
                        }
                    for song in playlist_songs:
                        if song['track']['id'] is not None:
                            if enable_m3u:
                                playlist_m3u_queue[item['media_id']]['tracks'].append(song['track']['id'])
                            self.enqueue_tracks([song['track']], enqueue_part_cfg=enqueue_part_cfg,
                                                log_id=f'{item_name}:{item["media_id"]}', item_type=f"Playlist [{name}]")
                    if not item['data'].get('hide_dialogs', False):
                        self.progress.emit(self.tr("Added playlist '{0}' to download queue !").format(item_name))
                elif item['media_type'] == 'track':
                    song_info = get_song_info(session, item['media_id'])
                    name = song_info['name']
                    if not item['data'].get('hide_dialogs', False):
                        self.progress.emit(self.tr("Adding track '{0}' to download queue !").format(name))
                    track_obj = {
                        'id': item['media_id'],
                        'name': song_info['name'],
                        'explicit': False,
                        'artists': [{'name': name} for name in song_info['artists']]
                    }
                    self.enqueue_tracks([track_obj], enqueue_part_cfg=enqueue_part_cfg,
                                        log_id=f'{name}:{item["media_id"]}', item_type="Track")
                    if not item['data'].get('hide_dialogs', False):
                        self.progress.emit(self.tr("Added track '{0}' to download queue !").format(name))
                logger.info('Finished parsing this item !')
            except (OSError, queue.Empty, MaxRetryError, NewConnectionError, ConnectionError):
                # Internet disconnected ?
                logger.error('Item parsing failed.. Connection error ! Trying to re init parsing account session ! ')
                re_init_session(session_pool, selected_uuid, wait_connectivity=True, timeout=60)
                self.__queue.put(item)
        logger.warning('Parsing queue processor is stopping !')

    def setup(self, queue):
        self.__queue = queue
        self.__stop = 0
