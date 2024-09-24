import os
import platform
import time
import requests
from librespot.core import Session
import re
from ..otsconfig import config, config_dir
from ..runtimedata import get_logger
from .spotify import search_by_term, get_currently_playing_url
import subprocess
import asyncio
import traceback
import json

if platform.system() == "Windows":
    from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager

logger = get_logger("utils")
media_tracker_last_query = ''


def re_init_session(session_pool: dict, session_uuid: str, wait_connectivity: bool = False,
                    connectivity_test_url: str = 'https://spotify.com', timeout=60) -> bool:
    start = int(time.time())
    session_json_path = os.path.join(os.path.join(config_dir(), 'onthespot', 'sessions'),
                                     f"ots_login_{session_uuid}.json")
    if not os.path.isfile(session_json_path):
        return False
    if wait_connectivity:
        status = 0
        while status != 200 and int(time.time()) - start < timeout:
            try:
                r = requests.get(connectivity_test_url)
                status = r.status_code
                logger.info(f'Connectivity check done ! Status code "{status}" ')
            except:
                logger.info('Connectivity issue ! Waiting ... ')
        if status == 0:
            return False
    try:
        config = Session.Configuration.Builder().set_stored_credential_file(session_json_path).build()
        logger.debug("Session config created")
        session = Session.Builder(conf=config).stored_file(session_json_path).create()
        logger.debug("Session re init done")
        session_pool[session_uuid] = session
    except:
        logger.error('Failed to re init session !')
        return False
    return True


def login_user(username: str, password: str, login_data_dir: str, uuid: str) -> list:
    logger.info(f"logging in user '{username[:4]}*******'")
    # Check the username and if pickled session file exists load the session and append
    # Returns: [Success: Bool, Session: Session, SessionJsonFile: str, premium: Bool]
    session_json_path = os.path.join(login_data_dir, f"ots_login_{uuid}.json")
    os.makedirs(os.path.dirname(session_json_path), exist_ok=True)
    if os.path.isfile(session_json_path):
        logger.info(f"Session file exists for user, attempting to use it '{username[:4]}*******'")
        logger.debug("Restoring user session")
        # Session exists try loading it
        try:
            config = Session.Configuration.Builder().set_stored_credential_file(session_json_path).build()
            logger.debug("Session config created")
            # For some reason initialising session as None prevents premature application exit
            session = None
            session = Session.Builder(conf=config).stored_file(session_json_path).create()
            logger.debug("Session created")
            premium = True if session.get_user_attribute("type") == "premium" else False
            logger.info(f"Login successful for user '{username[:4]}*******'")
            return [True, session, session_json_path, premium, uuid]
        except (RuntimeError, Session.SpotifyAuthenticationException):
            logger.error(f"Failed logging in user '{username[:4]}*******', invalid credentials")
        except Exception as e:
            logger.error(f"Failed logging in user '{username[:4]}*******', unexpected error ! : {str(e)}; {traceback.format_exc()}")
            return [False, None, "", False, uuid]


def remove_user(username: str, login_data_dir: str, config, session_uuid: str, thread_pool: dict,
                session_pool: dict) -> bool:
    logger.info(f"Removing user '{username[:4]}*******' from saved entries, uuid {session_uuid}")
    # Try to stop the thread using this account
    if session_uuid in thread_pool.keys():
        thread_pool[session_uuid][0].stop()
        logger.info(f'Waiting for worker bound to account : {session_uuid} to exit !')
        while not thread_pool[session_uuid][0].is_stopped():
            time.sleep(0.1)
        logger.info(f'Waiting for thread bound to worker bound account : {session_uuid} to exit !')
        while thread_pool[session_uuid][1].isRunning():
            thread_pool[session_uuid][1].quit()
        logger.info(f'Workers and threads associated with account : {session_uuid} cleaned up !')
        thread_pool.pop(session_uuid)
    # Remove from session pool
    if session_uuid in session_pool:
        session_pool.pop(session_uuid)
    session_json_path = os.path.join(login_data_dir, f"ots_login_{session_uuid}.json")
    if os.path.isfile(session_json_path):
        os.remove(session_json_path)
    removed = False
    accounts_copy = config.get("accounts").copy()
    accounts = config.get("accounts")
    for i in range(0, len(accounts)):
        if accounts[i][3] == session_uuid:
            accounts_copy.pop(i)
            removed = True
            break
    if removed:
        logger.info(f"Saved Account user '{username[:4]}*******' found and removed, uuid: {session_uuid}")
        config.set_("accounts", accounts_copy)
        config.update()
    return removed


def regex_input_for_urls(search_input):
    logger.info(f"Parsing url '{search_input}'")
    track_uri_search = re.search(
        r"^spotify:track:(?P<TrackID>[0-9a-zA-Z]{22})$",
        search_input
    )
    track_url_search = re.search(
        r"^(https?://)?open\.spotify\.com/track/(?P<TrackID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
        search_input
    )
    album_uri_search = re.search(
        r"^spotify:album:(?P<AlbumID>[0-9a-zA-Z]{22})$",
        search_input
    )
    album_url_search = re.search(
        r"^(https?://)?open\.spotify\.com/album/(?P<AlbumID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
        search_input
    )
    playlist_uri_search = re.search(
        r"^spotify:playlist:(?P<PlaylistID>[0-9a-zA-Z]{22})$",
        search_input
    )
    playlist_url_search = re.search(
        r"^(https?://)?open\.spotify\.com/playlist/(?P<PlaylistID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
        search_input
    )
    episode_uri_search = re.search(
        r"^spotify:episode:(?P<EpisodeID>[0-9a-zA-Z]{22})$",
        search_input
    )
    episode_url_search = re.search(
        r"^(https?://)?open\.spotify\.com/episode/(?P<EpisodeID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
        search_input
    )
    show_uri_search = re.search(
        r"^spotify:show:(?P<ShowID>[0-9a-zA-Z]{22})$",
        search_input
    )
    show_url_search = re.search(
        r"^(https?://)?open\.spotify\.com/show/(?P<ShowID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
        search_input,
    )
    artist_uri_search = re.search(
        r"^spotify:artist:(?P<ArtistID>[0-9a-zA-Z]{22})$",
        search_input
    )
    artist_url_search = re.search(
        r"^(https?://)?open\.spotify\.com/artist/(?P<ArtistID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
        search_input
    )

    if track_uri_search is not None or track_url_search is not None:
        track_id_str = (track_uri_search
                        if track_uri_search is not None else
                        track_url_search).group("TrackID")
    else:
        track_id_str = None

    if album_uri_search is not None or album_url_search is not None:
        album_id_str = (album_uri_search
                        if album_uri_search is not None else
                        album_url_search).group("AlbumID")
    else:
        album_id_str = None

    if playlist_uri_search is not None or playlist_url_search is not None:
        playlist_id_str = (playlist_uri_search
                           if playlist_uri_search is not None else
                           playlist_url_search).group("PlaylistID")
    else:
        playlist_id_str = None

    if episode_uri_search is not None or episode_url_search is not None:
        episode_id_str = (episode_uri_search
                          if episode_uri_search is not None else
                          episode_url_search).group("EpisodeID")
    else:
        episode_id_str = None

    if show_uri_search is not None or show_url_search is not None:
        show_id_str = (show_uri_search
                       if show_uri_search is not None else
                       show_url_search).group("ShowID")
    else:
        show_id_str = None

    if artist_uri_search is not None or artist_url_search is not None:
        artist_id_str = (artist_uri_search
                         if artist_uri_search is not None else
                         artist_url_search).group("ArtistID")
    else:
        artist_id_str = None
    return track_id_str, album_id_str, playlist_id_str, episode_id_str, show_id_str, artist_id_str


def get_url_data(url):
    track_id_str, album_id_str, playlist_id_str, episode_id_str, show_id_str, artist_id_str = regex_input_for_urls(url)
    if track_id_str is not None:
        logger.info(f"Parse result for url '{url}'-> track, {track_id_str}")
        return "track", track_id_str
    elif album_id_str is not None:
        logger.info(f"Parse result for url '{url}'-> album, {album_id_str}")
        return "album", album_id_str
    elif playlist_id_str is not None:
        logger.info(f"Parse result for url '{url}'-> playlist, {playlist_id_str}")
        return "playlist", playlist_id_str
    elif episode_id_str is not None:
        logger.info(f"Parse result for url '{url}'-> episode, {episode_id_str}")
        return "episode", episode_id_str
    elif show_id_str is not None:
        logger.info(f"Parse result for url '{url}'-> podcast, {show_id_str}")
        return "podcast", show_id_str
    elif artist_id_str is not None:
        logger.info(f"Parse result for url '{url}'-> artist, {artist_id_str}")
        return "artist", artist_id_str
    else:
        logger.error(f"Parse result for url '{url}' failed, invalid spotify url !")
        return None, None


def get_now_playing_local(session):
    global media_tracker_last_query
    if platform.system() == "Linux":
        logger.debug("Linux detected ! Use playerctl to get current track information..")
        try:
            playerctl_out = subprocess.check_output(["playerctl", "-p", "spotify", "metadata", "xesam:url"])
        except subprocess.CalledProcessError:
            logger.debug("Spotify not running. Fetching track via api..")
            return get_currently_playing_url(session)
        spotify_url = playerctl_out.decode()
        return spotify_url
    elif platform.system() == "Windows":
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.debug("Windows detected ! Using unreliable search method to get media info")
        info_dict = None
        sessions = loop.run_until_complete(MediaManager.request_async())
        current_session = sessions.get_current_session()
        if current_session:
            if current_session.source_app_user_model_id == "Spotify.exe":
                logger.debug("Spotify running..")
                info = loop.run_until_complete(current_session.try_get_media_properties_async())
                info_dict = {song_attr: info.__getattribute__(song_attr) for song_attr in dir(info) if
                             song_attr[0] != '_'}
                info_dict['genres'] = list(info_dict['genres'])
        if info_dict:
            query_str = f"{info_dict['title']} {info_dict['artist']} {info_dict['album_title']}".strip()
            logger.debug(f"Spotify running and playing {query_str}")
            if media_tracker_last_query == query_str:
                return ""
            results = search_by_term(session, query_str, max_results=1, content_types=["track"])
            media_tracker_last_query = query_str
            if len(results["tracks"]) > 0:
                try:
                    link = results["tracks"][0]["external_urls"]["spotify"]
                    logger.debug(f"Spotify now playing {link}")
                    return link
                except (KeyError, IndexError):
                    logger.debug("KeyError. Fetching track via api..")
                    return get_currently_playing_url(session)
            else:
                logger.debug("No result for currently playing track. Fetching track via api..")
                return get_currently_playing_url(session)
        else:
            logger.debug("Event loop failed. Fetching track via api..")
            return get_currently_playing_url(session)
    else:
        logger.debug("Unsupported platform for auto download. Fetching track via api..")
        return get_currently_playing_url(session)



def name_by_from_sdata(d_key: str, item: dict):
    item_name = item_by = None
    if d_key == "tracks":
        item_name = f"{'[ E ]' if item['explicit'] else '       '} {item['name']}"
        item_by = f"{','.join([artist['name'] for artist in item['artists']])}"
    elif d_key == "albums":
        rel_year = re.search(r'(\d{4})', item['release_date']).group(1)
        item_name = f"[Y:{rel_year}] [T:{item['total_tracks']}] {item['name']}"
        item_by = f"{','.join([artist['name'] for artist in item['artists']])}"
    elif d_key == "playlists":
        item_name = f"{item['name']}"
        item_by = f"{item['owner']['display_name']}"
    elif d_key == "artists":
        item_name = item['name']
        if f"{'/'.join(item['genres'])}" != "":
            item_name = item['name'] + f"  |  GENERES: {'/'.join(item['genres'])}"
        item_by = f"{item['name']}"
    return item_name, item_by

def fetch_account_uuid(download):
    if config.get("rotate_acc_sn") == True:
         try:
             parsing_index = config.get("parsing_acc_sn")
             return config.get('accounts')[parsing_index][3]
         except IndexError as e:
             parsing_index = 0
             return config.get('accounts')[parsing_index][3]
         if download == True:
             config.set_('parsing_acc_sn', parsing_index + 1)
    else:
        return config.get('accounts')[ config.get('parsing_acc_sn') - 1 ][3]

def latest_release():
    url = "https://api.github.com/repos/justin025/onthespot/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        current_version = str(config.get("version")).replace('v', '').replace('.', '')
        latest_version = response.json()['name'].replace('v', '').replace('.', '')
        if int(latest_version) > int(current_version):
            logger.info(f"Update Available: {int(latest_version)} > {int(current_version)}")
            return False

def open_item(item):
    if platform.system() == 'Windows':
        os.startfile(item)
    elif platform.system() == 'Darwin':  # For MacOS
        subprocess.Popen(['open', item])
    else:  # For Linux and other Unix-like systems
        subprocess.Popen(['xdg-open', item])
