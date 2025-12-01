import os
import re
from .accounts import get_account_token
from .api.apple_music import apple_music_get_search_results
from .api.bandcamp import bandcamp_get_search_results
from .api.deezer import deezer_get_search_results
from .api.qobuz import qobuz_get_search_results
from .api.soundcloud import soundcloud_get_search_results
from .api.spotify import spotify_get_search_results, spotify_get_item_by_id
from .api.tidal import tidal_get_search_results
from .api.youtube_music import youtube_music_get_search_results
from .api.crunchyroll import crunchyroll_get_search_results
from .otsconfig import config
from .parse_item import parse_url
from .runtimedata import account_pool, get_logger

logger = get_logger("search")

# Regex patterns for Spotify ID detection
SPOTIFY_ID_REGEX = re.compile(r'^[0-9a-zA-Z]{22}$')
SPOTIFY_URI_REGEX = re.compile(r'^spotify:(?P<type>track|album|artist|playlist|episode|show):(?P<id>[0-9a-zA-Z]{22})$')


def get_search_results(search_term, content_types=None):
    if len(account_pool) <= 0:
        return None

    if search_term == '':
        logger.warning(f"Returning empty data as query is empty !")
        return False

    # Check for Spotify URI format (spotify:type:id)
    uri_match = re.match(SPOTIFY_URI_REGEX, search_term)
    if uri_match:
        spotify_type = uri_match.group('type')
        spotify_id = uri_match.group('id')
        # Convert episode/show to podcast_episode/podcast for internal use
        if spotify_type == 'episode':
            spotify_type = 'podcast_episode'
        elif spotify_type == 'show':
            spotify_type = 'podcast'
        logger.info(f"Detected Spotify URI format: {spotify_type}:{spotify_id}")

        # Get token and fetch item details to show in search results
        service = account_pool[config.get('active_account_number')]['service']
        if service == 'spotify':
            try:
                token = get_account_token(service)
                return spotify_get_item_by_id(token, spotify_id, spotify_type)
            except (ConnectionError, ConnectionRefusedError, OSError, TimeoutError) as e:
                logger.error(f"Connection error while fetching Spotify URI: {e}")
                logger.error("This may be due to temporary network issues or Spotify rate limiting. Please try again in a moment.")
                return False
            except Exception as e:
                logger.error(f"Error fetching Spotify URI: {e}")
                return False
        else:
            logger.warning(f"Spotify ID detected but active account is {service}")
            return False

    # Check for bare Spotify ID (22 alphanumeric characters) - default to playlist
    if re.match(SPOTIFY_ID_REGEX, search_term):
        logger.info(f"Detected bare Spotify ID, assuming playlist: {search_term}")

        # Get token and fetch playlist details to show in search results
        service = account_pool[config.get('active_account_number')]['service']
        if service == 'spotify':
            try:
                token = get_account_token(service)
                return spotify_get_item_by_id(token, search_term, 'playlist')
            except (ConnectionError, ConnectionRefusedError, OSError, TimeoutError) as e:
                logger.error(f"Connection error while fetching Spotify ID: {e}")
                logger.error("This may be due to temporary network issues or Spotify rate limiting. Please try again in a moment.")
                return False
            except Exception as e:
                logger.error(f"Error fetching Spotify ID: {e}")
                return False
        else:
            logger.warning(f"Spotify ID detected but active account is {service}")
            return False

    if search_term.startswith('https://') or search_term.startswith('http://'):
        logger.info(f"Search clicked with value with url {search_term}")
        result = parse_url(search_term)
        if result is False:
            return False
        return True
    else:
        if os.path.isfile(search_term):
            with open(search_term, 'r', encoding='utf-8') as sf:
                links = sf.readlines()
                for link in links:
                    link = link.strip()
                    if link.startswith("https://"):
                        logger.debug(f'Parsing link from {search_term}: {link}')
                        parse_url(link)
            return True

        logger.info(f"Search clicked with value term {search_term}")
        service = account_pool[config.get('active_account_number')]['service']
        if search_term and service != 'generic':
            try:
                token = get_account_token(service)
                return globals()[f"{service}_get_search_results"](token, search_term, content_types)
            except (ConnectionError, ConnectionRefusedError, OSError, TimeoutError) as e:
                logger.error(f"Connection error during search: {e}")
                logger.error("This may be due to temporary network issues or Spotify rate limiting. Please try again in a moment.")
                return False
            except Exception as e:
                logger.error(f"Unexpected error during search: {e}")
                return False
        else:
            return False
