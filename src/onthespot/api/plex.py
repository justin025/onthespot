import os
import time
import requests
from urllib.parse import urljoin, quote
from ..otsconfig import config
from ..runtimedata import get_logger

logger = get_logger('api.plex')

# Plex API constants
PLEX_TV_URL = 'https://plex.tv'
PLEX_CLIENT_IDENTIFIER = 'onthespot-plex-integration'
PLEX_PRODUCT_NAME = 'OnTheSpot'
PLEX_VERSION = '1.0'


def plex_request_pin():
    """
    Request a PIN from Plex.tv for OAuth authentication
    Returns dict with 'id', 'code', and 'url' or None on error
    """
    try:
        headers = {
            'X-Plex-Product': PLEX_PRODUCT_NAME,
            'X-Plex-Version': PLEX_VERSION,
            'X-Plex-Client-Identifier': PLEX_CLIENT_IDENTIFIER,
            'Accept': 'application/json'
        }

        response = requests.post(
            f'{PLEX_TV_URL}/api/v2/pins',
            headers=headers,
            params={'strong': 'true'},
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            pin_id = data.get('id')
            pin_code = data.get('code')

            logger.info(f"Plex PIN requested: {pin_code}")

            return {
                'id': pin_id,
                'code': pin_code,
                'url': f'https://plex.tv/link'
            }
        else:
            logger.error(f"Failed to request Plex PIN: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Error requesting Plex PIN: {str(e)}")
        return None


def plex_check_pin(pin_id):
    """
    Check if a PIN has been authorized
    Returns auth token if authorized, None if not yet authorized, False on error
    """
    try:
        headers = {
            'X-Plex-Client-Identifier': PLEX_CLIENT_IDENTIFIER,
            'Accept': 'application/json'
        }

        response = requests.get(
            f'{PLEX_TV_URL}/api/v2/pins/{pin_id}',
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            auth_token = data.get('authToken')

            if auth_token:
                logger.info("Plex PIN authorized successfully")
                return auth_token
            else:
                # Not yet authorized
                return None
        else:
            logger.error(f"Failed to check Plex PIN: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Error checking Plex PIN: {str(e)}")
        return False


def plex_get_user_info(token):
    """
    Get user information from Plex
    Returns dict with user info or None on error
    """
    try:
        headers = {
            'X-Plex-Token': token,
            'X-Plex-Client-Identifier': PLEX_CLIENT_IDENTIFIER,
            'Accept': 'application/json'
        }

        response = requests.get(
            f'{PLEX_TV_URL}/api/v2/user',
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return {
                'username': data.get('username'),
                'email': data.get('email'),
                'thumb': data.get('thumb')
            }
        else:
            logger.error(f"Failed to get user info: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return None


def plex_get_servers(token):
    """
    Get list of Plex servers available to the user
    Returns list of servers or None on error
    """
    try:
        headers = {
            'X-Plex-Token': token,
            'X-Plex-Client-Identifier': PLEX_CLIENT_IDENTIFIER,
            'Accept': 'application/json'
        }

        response = requests.get(
            f'{PLEX_TV_URL}/api/v2/resources',
            headers=headers,
            params={'includeHttps': 1, 'includeRelay': 0},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            servers = []

            for resource in data:
                if resource.get('product') == 'Plex Media Server' and resource.get('owned'):
                    connections = resource.get('connections', [])
                    # Get the first local connection, or first connection if no local
                    server_url = None
                    for conn in connections:
                        if conn.get('local'):
                            server_url = conn.get('uri')
                            break
                    if not server_url and connections:
                        server_url = connections[0].get('uri')

                    if server_url:
                        servers.append({
                            'name': resource.get('name'),
                            'url': server_url,
                            'owned': resource.get('owned', False)
                        })

            logger.info(f"Found {len(servers)} Plex servers")
            return servers
        else:
            logger.error(f"Failed to get Plex servers: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Error getting Plex servers: {str(e)}")
        return None


def plex_test_connection(server_url, token):
    """
    Test connection to Plex server
    Returns True if successful, False otherwise
    """
    try:
        if not server_url or not token:
            logger.error("Plex server URL and token are required")
            return False

        # Clean up URL
        server_url = server_url.rstrip('/')

        # Test connection
        headers = {
            'X-Plex-Token': token,
            'Accept': 'application/json'
        }

        response = requests.get(
            urljoin(server_url, '/'),
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            logger.info("Successfully connected to Plex server")
            return True
        else:
            logger.error(f"Failed to connect to Plex server: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Error testing Plex connection: {str(e)}")
        return False


def plex_get_library_sections(server_url, token):
    """
    Get all library sections from Plex server
    Returns list of sections with id and name, or None on error
    """
    try:
        if not server_url or not token:
            logger.error("Plex server URL and token are required")
            return None

        server_url = server_url.rstrip('/')

        headers = {
            'X-Plex-Token': token,
            'Accept': 'application/json'
        }

        response = requests.get(
            urljoin(server_url, '/library/sections'),
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            sections = []

            if 'MediaContainer' in data and 'Directory' in data['MediaContainer']:
                for section in data['MediaContainer']['Directory']:
                    # Only include music libraries
                    if section.get('type') == 'artist':
                        sections.append({
                            'id': section.get('key'),
                            'title': section.get('title'),
                            'type': section.get('type')
                        })

            logger.info(f"Found {len(sections)} music library sections")
            return sections
        else:
            logger.error(f"Failed to get library sections: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Error getting library sections: {str(e)}")
        return None


def plex_import_m3u(server_url, token, library_section_id, m3u_path):
    """
    Import M3U playlist to Plex
    Returns True if successful, False otherwise
    """
    try:
        if not server_url or not token or not library_section_id or not m3u_path:
            logger.error("All parameters are required for M3U import")
            return False

        if not os.path.exists(m3u_path):
            logger.error(f"M3U file not found: {m3u_path}")
            return False

        server_url = server_url.rstrip('/')

        # Build the upload URL
        url = f"{server_url}/playlists/upload"
        params = {
            'sectionID': library_section_id,
            'path': m3u_path,
            'X-Plex-Token': token
        }

        logger.info(f"Importing M3U to Plex: {m3u_path}")

        response = requests.post(
            url,
            params=params,
            timeout=30
        )

        if response.status_code == 200:
            logger.info(f"Successfully imported M3U to Plex: {m3u_path}")
            return True
        else:
            logger.error(f"Failed to import M3U: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Error importing M3U to Plex: {str(e)}")
        return False


def plex_save_settings(server_url, token, library_section_id=""):
    """
    Save Plex settings to config
    """
    config.set('plex_server_url', server_url)
    config.set('plex_token', token)
    config.set('plex_library_section_id', library_section_id)
    config.save()
    logger.info("Plex settings saved")


def plex_get_m3u_files():
    """
    Get list of all M3U files in the M3U directory
    Returns list of M3U file paths
    """
    try:
        audio_path = config.get("audio_download_path")
        m3u_formatter = config.get("m3u_path_formatter")

        # Extract the M3U directory from the formatter
        # Default is "M3U/{playlist_name} by {playlist_owner}"
        m3u_dir_parts = m3u_formatter.split(os.path.sep)
        if len(m3u_dir_parts) > 0:
            m3u_dir = m3u_dir_parts[0]
        else:
            m3u_dir = "M3U"

        m3u_path = os.path.join(audio_path, m3u_dir)

        if not os.path.exists(m3u_path):
            logger.info(f"M3U directory not found: {m3u_path}")
            return []

        m3u_files = []
        m3u_format = config.get("m3u_format", "m3u8")

        for root, dirs, files in os.walk(m3u_path):
            for file in files:
                if file.endswith(f'.{m3u_format}') or file.endswith('.m3u'):
                    full_path = os.path.join(root, file)
                    m3u_files.append(full_path)

        logger.info(f"Found {len(m3u_files)} M3U files")
        return sorted(m3u_files)

    except Exception as e:
        logger.error(f"Error getting M3U files: {str(e)}")
        return []
