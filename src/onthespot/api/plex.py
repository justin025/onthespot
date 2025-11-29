import requests
import time
from ..otsconfig import config
from ..runtimedata import get_logger

logger = get_logger("api.plex")


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
                'auth_url': f"https://app.plex.tv/auth#?clientID={self.CLIENT_IDENTIFIER}&code={data['code']}&context[device][product]=OnTheSpot"
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

            response = requests.post(
                f"{self.server_url}/playlists/upload",
                params=params
            )

            if response.status_code == 200:
                logger.info(f"Successfully uploaded playlist: {m3u_file_path}")
                return {'success': True}
            else:
                logger.error(f"Failed to upload playlist: {response.status_code} - {response.text}")
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to upload playlist: {str(e)}")
            return {'success': False, 'error': str(e)}

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
