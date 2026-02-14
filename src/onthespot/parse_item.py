import re
import time
import traceback
from .accounts import get_account_token
from .api.apple_music import apple_music_get_album_track_ids, apple_music_get_artist_album_ids, apple_music_get_playlist_data
from .api.bandcamp import bandcamp_get_album_track_ids, bandcamp_get_artist_album_ids
from .api.deezer import deezer_parse_url, deezer_get_album_track_ids, deezer_get_artist_album_ids, deezer_get_playlist_data
from .api.qobuz import qobuz_get_album_track_ids, qobuz_get_artist_album_ids, qobuz_get_label_album_ids, qobuz_get_playlist_data
from .api.soundcloud import soundcloud_parse_url,  soundcloud_get_artist_album_ids, soundcloud_get_album_track_ids, soundcloud_get_playlist_data
from .api.spotify import spotify_get_album_track_ids, spotify_get_artist_album_ids, spotify_get_playlist_items, spotify_get_playlist_data, spotify_get_liked_songs, spotify_get_your_episodes, spotify_get_podcast_episode_ids
from .api.tidal import tidal_get_album_track_ids, tidal_get_artist_album_ids, tidal_get_playlist_data, tidal_get_mix_data
from .api.youtube_music import youtube_music_get_channel_track_ids, youtube_music_get_playlist_data
from .api.generic import generic_get_track_metadata
from .api.crunchyroll import crunchyroll_get_show_episode_ids
from .runtimedata import account_pool, get_logger, parsing, download_queue, pending, parsing_lock, pending_lock
from .utils import format_local_id
from .otsconfig import config
from PyQt6.QtCore import QObject, pyqtSignal
import threading

logger = get_logger('parse_item')
# Audio
APPLE_MUSIC_URL_REGEX = re.compile(r'https?://music.apple.com/([a-z]{2})/(?P<type>album|playlist|artist)(?:/(?P<title>[-a-z0-9]+))?/(?P<id>[\w.-]+)(?:\?i=(?P<track_id>\d+))?(?:&.*)?$')
BANDCAMP_URL_REGEX = re.compile(r'https?://[a-z0-9-]+.bandcamp.com(?:/(?P<type>track|album|music)/[a-z0-9-]+)?')
DEEZER_URL_REGEX = re.compile(r'https?://www.deezer.com/(?:[a-z]{2}/)?(?P<type>album|playlist|track|artist)/(?P<id>\d+)')
DEEZER_SHARE_URL_REGEX = re.compile(r'https?://link.deezer.com/s/([-a-z0-9]+)')
QOBUZ_URL_REGEX = re.compile(r"https?://(www.|play.|open.)?qobuz.com/(?:[a-z]{2}-[a-z]{2}/)?(?P<type>album|playlist|artist|track|label|interpreter)(?:/[^/]+)?(?:/[^/]+)?/(?P<id>[-a-z0-9]+)")
SOUNDCLOUD_URL_REGEX = re.compile(r"https?://(m.)?soundcloud.com/[-\w:/]+")
SPOTIFY_URL_REGEX = re.compile(r"https?://open.spotify.com/(intl-([a-zA-Z]+)/|)(?P<type>track|album|artist|playlist|episode|show)/(?P<id>[0-9a-zA-Z]{22})(\?si=.+?)?$")
TIDAL_URL_REGEX = re.compile(r"https?://(www.|listen.)?tidal.com/(browse/)?(?P<type>album|track|artist|playlist|mix)/(?P<id>[-a-z0-9]+)")
YOUTUBE_MUSIC_URL_REGEX = re.compile(r"https?://music.youtube.com/(watch\?v=(?P<video_id>[a-zA-Z0-9_-]+)|channel/(?P<channel_id>[a-zA-Z0-9_-]+)|playlist\?list=(?P<playlist_id>[a-zA-Z0-9_-]+))")
# Video
#YOUTUBE_URL_REGEX = re.compile(r"https?://(www.|music.)?youtube.com/(watch\?v=(?P<video_id>[a-zA-Z0-9_-]+)|channel/(?P<channel_id>[a-zA-Z0-9_-]+)|playlist\?list=(?P<playlist_id>[a-zA-Z0-9_-]+))")
CRUNCHYROLL_URL_REGEX = re.compile(r"https?://(www.)?crunchyroll.com/(?P<type>watch|series)/(musicvideo/)?(?P<id>[-A-Z0-9]+)/(?P<title>[-a-z0-9]+)")

def parse_url(url):
    # Audio
    if re.match(APPLE_MUSIC_URL_REGEX, url):
        match = re.search(APPLE_MUSIC_URL_REGEX, url)
        item_id = match.group("id")
        item_type = match.group("type")
        item_service = 'apple_music'
        if match.group("track_id"):
            item_id = match.group("track_id")
            item_type = 'track'

    elif re.match(BANDCAMP_URL_REGEX, url):
        match = re.search(BANDCAMP_URL_REGEX, url)
        item_id = url
        item_service = 'bandcamp'
        if not match.group("type") or match.group("type") == 'music':
            item_type = 'artist'
        else:
            item_type = match.group("type")

    elif re.match(DEEZER_URL_REGEX, url):
        match = re.search(DEEZER_URL_REGEX, url)
        item_id = match.group("id")
        item_type = match.group("type")
        item_service = 'deezer'

    elif re.match(DEEZER_SHARE_URL_REGEX, url):
        deezer_parse_url(url)
        return True

    elif re.match(QOBUZ_URL_REGEX, url):
        match = re.search(QOBUZ_URL_REGEX, url)
        item_id = match.group("id")
        item_type = match.group("type")
        item_service = 'qobuz'
        if item_type == 'interpreter':
            item_type = 'artist'

    elif re.match(SOUNDCLOUD_URL_REGEX, url):
        token = get_account_token('soundcloud')
        item_type, item_id = soundcloud_parse_url(url, token)
        item_service = "soundcloud"

    elif re.match(SPOTIFY_URL_REGEX, url):
        match = re.search(SPOTIFY_URL_REGEX, url)
        item_id = match.group("id")
        item_type = match.group("type")
        item_service = "spotify"
        if item_type == 'episode':
            item_type = 'podcast_episode'
        elif item_type == 'show':
            item_type = 'podcast'
    elif url == 'https://open.spotify.com/collection/tracks':
        item_id = None
        item_type = 'liked_songs'
        item_service = "spotify"
    elif url == 'https://open.spotify.com/collection/your-episodes':
        item_id = None
        item_type = 'your_episodes'
        item_service = "spotify"

    elif re.match(TIDAL_URL_REGEX, url):
        match = re.search(TIDAL_URL_REGEX, url)
        if match:
            item_service = 'tidal'
            item_type = match.group('type')
            item_id = match.group('id')

    elif re.match(YOUTUBE_MUSIC_URL_REGEX, url):
        match = re.search(YOUTUBE_MUSIC_URL_REGEX, url)
        if match:
            item_service = 'youtube_music'
            if match.group('video_id'):
                item_type = 'track'
                item_id = match.group('video_id')
            if match.group('channel_id'):
                item_type = 'artist'
                item_id = match.group('channel_id')
            if match.group('playlist_id'):
                item_type = 'playlist'
                item_id = match.group('playlist_id')

    # Video
    elif re.match(CRUNCHYROLL_URL_REGEX, url):
        match = re.search(CRUNCHYROLL_URL_REGEX, url)
        if match:
            item_service = 'crunchyroll'
            item_id = match.group('id') + '/' + match.group('title')
            if match.group('type') == 'watch':
                item_type = 'episode'
            elif match.group('type') == 'series':
                item_type = 'show'
            if match.group('id').startswith('MV'):
                # Music Video
                pass
    else:
        # Check if generic account is in account pool and if so
        # parse url using yt-dlp, else return 'Invalid Url'.
        try:
            generic_enabled = False
            for account in account_pool:
                if account['service'] == 'generic':
                    generic_enabled = True
            if generic_enabled:
                logger.info(f'Unable to parse url falling back to yt-dlp: {url}')
                # Check if yt-dlp can parse track
                item_metadata = generic_get_track_metadata('', url)
                # Returns false if playlist, currently not supported
                if item_metadata:
                    item_service = 'generic'
                    item_type = 'track'
                    item_id = url
                else:
                    return True
            else:
                logger.info(f'Invalid Url: {url}')
                return False
        except Exception as e:
            logger.info(f'Error Possibly Invalid Url: {url}, "{e}"')
            return False
    with parsing_lock:
        parsing[item_id] = {
            'item_url': url,
            'item_service': item_service,
            'item_type': item_type,
            'item_id': item_id
        }


class ParsingWorker(QObject):
    # Signal to emit errors to UI
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_running = True
        self.thread = threading.Thread(target=self.run)

    def start(self):
        self.thread.start()

    def run(self):
        while self.is_running:
            if parsing:
                try:
                    item_id = next(iter(parsing))
                    with parsing_lock:
                        item = parsing.pop(item_id)
                    logger.info(f"Parsing: {item}")

                    current_service = item['item_service']
                    current_type = item['item_type']
                    current_id = item['item_id']
                    current_url = item['item_url']
                    token = get_account_token(current_service)

                    if current_service == "spotify":
                        if current_type == "playlist":
                            try:
                                items = spotify_get_playlist_items(token, current_id)
                                playlist_name, playlist_by = spotify_get_playlist_data(token, current_id)
                            except Exception as playlist_error:
                                error_str = str(playlist_error)
                                if "404" in error_str or "not found" in error_str.lower():
                                    error_msg = f"Playlist not found: The Spotify playlist was not found, was created by Spotify (unavailable in the Web API) or is private.\n\nPlaylist ID: {current_id}\n\nPlease verify:\n• The playlist URL is correct\n• The playlist was NOT created by Spotify\n• The playlist is public or you have access\n• You're logged into the correct Spotify account"
                                else:
                                    error_msg = f"Failed to load Spotify playlist: {error_str}\n\nPlaylist ID: {current_id}"

                                self.error.emit(error_msg)
                                logger.error(f"Playlist fetch failed: {traceback.format_exc()}")
                                continue  # Skip to next item in parsing queue

                            for index, item in enumerate(items):
                                try:
                                    item_id = item['track']['id']
                                    item_type = item['track']['type']
                                    local_id = format_local_id(item_id)
                                    with pending_lock:
                                        pending[local_id] = {
                                            'local_id': local_id,
                                            'item_service': 'spotify',
                                            'item_type': item_type,
                                            'item_id': item_id,
                                            'parent_category': 'playlist',
                                            'playlist_name': playlist_name,
                                            'playlist_by': playlist_by,
                                            'playlist_number': str(index + 1)
                                            }
                                except TypeError:
                                    logger.error(f'TypeError for {item}')
                            continue
                        elif current_type == "liked_songs":
                            tracks = spotify_get_liked_songs(token)
                            for index, track in enumerate(tracks):
                                item_id = track['track']['id']
                                local_id = format_local_id(item_id)
                                with pending_lock:
                                    pending[local_id] = {
                                        'local_id': local_id,
                                        'item_service': 'spotify',
                                        'item_type': 'track',
                                        'item_id': item_id,
                                        'parent_category': 'playlist',
                                        'playlist_name': 'Liked Songs',
                                        'playlist_by': 'me',
                                        'playlist_number': str(index + 1)
                                        }
                            continue
                        elif current_type == "your_episodes":
                            tracks = spotify_get_your_episodes(token)
                            for index, track in enumerate(tracks):
                                item_id = track['episode']['id']
                                if item_id:
                                    local_id = format_local_id(item_id)
                                    with pending_lock:
                                        pending[local_id] = {
                                            'local_id': local_id,
                                            'item_service': 'spotify',
                                            'item_type': 'podcast_episode',
                                            'item_id': item_id,
                                            'parent_category': 'playlist',
                                            'playlist_name': 'Your Episodes',
                                            'playlist_by': 'me',
                                            'playlist_number': str(index + 1)
                                            }
                            continue

                    if current_service == 'youtube_music' and current_type == 'artist':
                        track_ids = youtube_get_channel_track_ids(token, current_id)
                        for track_id in track_ids:
                            local_id = format_local_id(track_id)
                            with pending_lock:
                                pending[local_id] = {
                                    'local_id': local_id,
                                    'item_service': current_service,
                                    'item_type': 'track',
                                    'item_id': track_id,
                                    'parent_category': 'album'
                                    }
                            continue
                        continue

                    if current_type in ["track", "podcast_episode", "movie", "episode"]:
                        local_id = format_local_id(item_id)
                        with pending_lock:
                            pending[local_id] = {
                                'local_id': local_id,
                                'item_service': current_service,
                                'item_type': current_type,
                                'item_id': item_id,
                                'parent_category': current_type
                                }
                        continue

                    elif current_type in ["podcast", "audiobook"]:
                        item_ids = globals()[f"{current_service}_get_{current_type}_episode_ids"](token, current_id)
                        for item_id in item_ids:
                            local_id = format_local_id(item_id)
                            with pending_lock:
                                pending[local_id] = {
                                    'local_id': local_id,
                                    'item_service': current_service,
                                    'item_type': 'podcast_episode',
                                    'item_id': item_id,
                                    'parent_category': current_type
                                    }
                        continue

                    elif current_type in ["album", "playlist", "mix"]:
                        playlist_name = ''
                        playlist_by = ''
                        try:
                            if current_type == "album":
                                track_ids = globals()[f"{current_service}_get_{current_type}_track_ids"](token, current_id)
                            else:
                                playlist_name, playlist_by, track_ids = globals()[f"{current_service}_get_{current_type}_data"](token, current_id)
                        except Exception as collection_error:
                            error_str = str(collection_error)
                            service_name = current_service.replace('_', ' ').title()
                            if "404" in error_str or "not found" in error_str.lower():
                                if current_type == "playlist" or current_type == "mix":
                                    error_msg = f"{current_type.title()} not found: The {service_name} {current_type} was not found or is private.\n\n{current_type.title()} ID: {current_id}\n\nPlease verify:\n• The {current_type} URL is correct\n• The {current_type} is public or you have access\n• You're logged into the correct {service_name} account"
                                elif current_type == "album":
                                    error_msg = f"Album not found: The {service_name} album was not found or is unavailable.\n\nAlbum ID: {current_id}"
                            else:
                                error_msg = f"Failed to load {service_name} {current_type}: {error_str}\n\n{current_type.title()} ID: {current_id}"

                            self.error.emit(error_msg)
                            logger.error(f"{current_type.title()} fetch failed for {current_service}: {traceback.format_exc()}")
                            continue  # Skip to next item in parsing queue

                        if current_type == 'mix':
                            current_type = 'playlist'
                        if current_service == 'youtube' and not playlist_by:
                            current_type = 'album'

                        for index, track_id in enumerate(track_ids):
                            local_id = format_local_id(track_id)
                            with pending_lock:
                                pending[local_id] = {
                                    'local_id': local_id,
                                    'item_service': current_service,
                                    'item_type': 'track',
                                    'item_id': track_id,
                                    'parent_category': current_type,
                                    'playlist_name': playlist_name,
                                    'playlist_by': playlist_by,
                                    'playlist_number': str(index + 1)
                                    }
                        continue

                    elif current_type in ["artist", "label"]:
                        item_ids = globals()[f"{current_service}_get_{current_type}_album_ids"](token, current_id)
                        for item_id in item_ids:
                            local_id = format_local_id(item_id)
                            with parsing_lock:
                                parsing[item_id] = {
                                    'item_url': '',
                                    'item_service': current_service,
                                    'item_type': 'album',
                                    'item_id': item_id
                                }

                    elif current_type in ['show', 'season']:
                        item_ids = globals()[f"{current_service}_get_{current_type}_episode_ids"](token, current_id)
                        for item_id in item_ids:
                            local_id = format_local_id(item_id)
                            with pending_lock:
                                pending[local_id] = {
                                    'local_id': local_id,
                                    'item_service': current_service,
                                    'item_type': 'episode',
                                    'item_id': item_id,
                                    'parent_category': current_type
                                    }
                        continue
                except Exception as e:
                    error_str = str(e)
                    error_msg = None

                    # Check for 404 errors (playlist/album not found)
                    if "404" in error_str or "not found" in error_str.lower():
                        if current_type == "playlist":
                            error_msg = f"Failed to load playlist: The playlist was not found or is private.\n\nPlaylist ID: {current_id}\n\nPlease verify:\n• The playlist URL is correct\n• The playlist is public or you have access\n• You're logged into the correct {current_service.replace('_', ' ').title()} account"
                        elif current_type == "album":
                            error_msg = f"Failed to load album: The album was not found or is unavailable.\n\nDetails: {current_url}"
                        elif current_type == "artist":
                            error_msg = f"Failed to load artist: The artist was not found.\n\nDetails: {current_url}"
                        else:
                            error_msg = f"Failed to load {current_type}: Item was not found.\n\nDetails: {current_url}"

                    # Check for rate limiting
                    elif "429" in error_str or "rate limit" in error_str.lower():
                        error_msg = f"Rate limit exceeded for {current_service.replace('_', ' ').title()}. Too many requests - please wait before adding more items.\n\nTip: Try disabling metadata options in Settings to reduce API calls."

                    # Check for max retries exhausted
                    elif "Max retries" in error_str or "exhausted" in error_str:
                        error_msg = f"Failed to load {current_type} after multiple retries. The service may be unavailable.\n\nDetails: {error_str}"

                    # Generic error
                    else:
                        error_msg = f"Error parsing {current_type}: {error_str}\n\nURL: {current_url}"

                    # Emit error to UI
                    if error_msg:
                        self.error.emit(error_msg)

                    logger.error(f"Unknown Exception: {str(e)}\nTraceback: {traceback.format_exc()}")
                    continue
            else:
                time.sleep(0.2)

    def stop(self):
        logger.info('Stopping Parsing Worker')
        self.is_running = False
        self.thread.join()
