import requests
import time
import logging
from ..otsconfig import config
from ..runtimedata import get_logger

logger = get_logger("api.plex")
logger.setLevel(logging.DEBUG)


class PlexAPI:
    """Plex API client for authentication and playlist management"""

    BASE_URL = "https://plex.tv"
    CLIENT_IDENTIFIER = "onthespot-music-downloader"

    def __init__(self):
        self.auth_token = config.get('plex_auth_token', None)
        self.server_url = config.get('plex_server_url', 'http://127.0.0.1:32400')
        self.library_section_id = config.get('plex_library_section_id', None)

    def request_pin(self):
        """Request a PIN for authentication"""
        try:
            headers = {
                'Accept': 'application/json',
                'X-Plex-Product': 'OnTheSpot',
                'X-Plex-Client-Identifier': self.CLIENT_IDENTIFIER
            }

            response = requests.post(
                f"{self.BASE_URL}/api/v2/pins",
                headers=headers,
                params={'strong': 'true'}
            )
            response.raise_for_status()
            data = response.json()

            return {
                'pin_id': data['id'],
                'pin_code': data['code'],
                'auth_url': f"https://app.plex.tv/auth#?clientID={self.CLIENT_IDENTIFIER}&code={data['code']}"
            }
        except Exception as e:
            logger.error(f"Failed to request PIN: {str(e)}")
            return None

    def check_pin(self, pin_id):
        """Check if PIN has been authorized and return auth token"""
        try:
            headers = {
                'Accept': 'application/json',
                'X-Plex-Client-Identifier': self.CLIENT_IDENTIFIER
            }

            response = requests.get(
                f"{self.BASE_URL}/api/v2/pins/{pin_id}",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            if data.get('authToken'):
                self.auth_token = data['authToken']
                config.set('plex_auth_token', self.auth_token)
                config.save()
                logger.info("Plex authentication successful")
                return self.auth_token
            return None
        except Exception as e:
            logger.error(f"Failed to check PIN: {str(e)}")
            return None

    def get_libraries(self):
        """Get all libraries from Plex server"""
        if not self.auth_token:
            logger.error("No auth token available")
            return None

        try:
            headers = {
                'Accept': 'application/json',
                'X-Plex-Token': self.auth_token
            }

            response = requests.get(
                f"{self.server_url}/library/sections",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            # Filter for music libraries only
            music_libraries = []
            for directory in data['MediaContainer'].get('Directory', []):
                if directory.get('type') == 'artist':  # Music libraries have type 'artist'
                    music_libraries.append({
                        'id': directory['key'],
                        'title': directory['title'],
                        'type': directory['type']
                    })

            return music_libraries
        except Exception as e:
            logger.error(f"Failed to get libraries: {str(e)}")
            return None

    def set_library(self, library_id):
        """Set the selected music library"""
        self.library_section_id = library_id
        config.set('plex_library_section_id', library_id)
        config.save()
        logger.info(f"Set Plex library section ID to: {library_id}")
        return True

    def upload_playlist(self, m3u_file_path):
        """Upload a playlist to Plex"""
        logger.debug(f"=== Starting playlist upload ===")
        logger.debug(f"M3U file path: {m3u_file_path}")
        logger.debug(f"Server URL: {self.server_url}")
        logger.debug(f"Library Section ID: {self.library_section_id}")
        logger.debug(f"Auth token present: {bool(self.auth_token)}")

        if not self.auth_token:
            logger.error("No auth token available")
            return {'success': False, 'error': 'Not authenticated'}

        if not self.library_section_id:
            logger.error("No library section selected")
            return {'success': False, 'error': 'No library selected'}

        try:
            params = {
                'sectionID': self.library_section_id,
                'path': m3u_file_path,
                'X-Plex-Token': self.auth_token
            }

            upload_url = f"{self.server_url}/playlists/upload"
            logger.debug(f"Upload URL: {upload_url}")
            logger.debug(f"Request params: sectionID={self.library_section_id}, path={m3u_file_path}")

            logger.info(f"Sending POST request to Plex...")
            response = requests.post(upload_url, params=params, timeout=30)

            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response body: {response.text[:500]}")  # First 500 chars

            if response.status_code == 200:
                logger.info(f"✓ Successfully uploaded playlist: {m3u_file_path}")
                return {'success': True}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"✗ Failed to upload playlist: {error_msg}")
                return {'success': False, 'error': error_msg}
        except requests.exceptions.Timeout:
            error_msg = "Request timed out after 30 seconds"
            logger.error(f"✗ {error_msg}")
            return {'success': False, 'error': error_msg}
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(f"✗ {error_msg}")
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"✗ {error_msg}")
            logger.exception("Full traceback:")
            return {'success': False, 'error': error_msg}

    def disconnect(self):
        """Clear Plex authentication"""
        self.auth_token = None
        self.library_section_id = None
        config.set('plex_auth_token', None)
        config.set('plex_library_section_id', None)
        config.set('plex_server_url', 'http://127.0.0.1:32400')
        config.save()
        logger.info("Disconnected from Plex")
        return True


# Global Plex API instance
plex_api = PlexAPI()
