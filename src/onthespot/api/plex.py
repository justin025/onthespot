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

    def scan_library(self):
        """Trigger a library scan to update playlists"""
        if not self.auth_token or not self.library_section_id:
            return False

        try:
            params = {'X-Plex-Token': self.auth_token}
            scan_url = f"{self.server_url}/library/sections/{self.library_section_id}/refresh"
            logger.debug(f"Triggering library scan: {scan_url}")
            response = requests.get(scan_url, params=params, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to trigger library scan: {e}")
            return False

    def get_playlists(self):
        """Get all playlists from Plex server"""
        if not self.auth_token:
            return None

        try:
            params = {'X-Plex-Token': self.auth_token}
            playlists_url = f"{self.server_url}/playlists"
            logger.debug(f"Fetching playlists: {playlists_url}")
            response = requests.get(playlists_url, params=params, timeout=10)

            if response.status_code == 200:
                # Parse XML response
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                playlists = []
                for playlist in root.findall('.//Playlist'):
                    playlists.append({
                        'title': playlist.get('title'),
                        'key': playlist.get('key'),
                        'playlistType': playlist.get('playlistType'),
                        'smart': playlist.get('smart') == '1'
                    })
                return playlists
            return None
        except Exception as e:
            logger.warning(f"Failed to get playlists: {e}")
            return None

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

        # Get playlist name for verification
        import os
        playlist_name = os.path.splitext(os.path.basename(m3u_file_path))[0]

        # Get existing playlists before upload
        playlists_before = self.get_playlists()
        before_names = [p['title'] for p in playlists_before] if playlists_before else []

        try:
            params = {
                'sectionID': self.library_section_id,
                'path': m3u_file_path,
                'X-Plex-Token': self.auth_token
            }

            upload_url = f"{self.server_url}/playlists/upload"

            # Build complete URL with parameters for debugging
            from urllib.parse import urlencode
            token_masked = self.auth_token[:10] + '...' if self.auth_token else 'None'
            params_debug = {
                'sectionID': self.library_section_id,
                'path': m3u_file_path,
                'X-Plex-Token': token_masked
            }
            full_url_debug = f"{upload_url}?{urlencode(params_debug)}"

            logger.debug(f"=== Request Details ===")
            logger.debug(f"Upload URL: {upload_url}")
            logger.debug(f"Full URL (token masked): {full_url_debug}")
            logger.debug(f"sectionID: {self.library_section_id}")
            logger.debug(f"path: {m3u_file_path}")
            logger.debug(f"X-Plex-Token: {token_masked}")

            # Check M3U file exists and peek at contents
            if os.path.exists(m3u_file_path):
                file_size = os.path.getsize(m3u_file_path)
                logger.debug(f"M3U file size: {file_size} bytes")
                try:
                    with open(m3u_file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[:10]  # First 10 lines
                        logger.debug(f"M3U file first {len(lines)} lines:")
                        for i, line in enumerate(lines, 1):
                            logger.debug(f"  Line {i}: {line.rstrip()}")
                except Exception as e:
                    logger.warning(f"Could not read M3U file: {e}")
            else:
                logger.error(f"M3U file does not exist at: {m3u_file_path}")

            logger.info(f"Sending POST request to Plex...")
            response = requests.post(upload_url, params=params, timeout=30)

            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response body: {response.text[:500] if response.text else '(empty)'}")

            if response.status_code == 200:
                # Empty 200 response is normal for Plex
                logger.info(f"✓ Plex accepted playlist upload: {m3u_file_path}")

                # Trigger library scan to refresh playlists
                logger.info("Triggering library scan to refresh playlists...")
                self.scan_library()

                # Wait a moment for the scan to process
                time.sleep(2)

                # Check if playlist was created
                playlists_after = self.get_playlists()
                after_names = [p['title'] for p in playlists_after] if playlists_after else []

                if playlist_name in after_names:
                    if playlist_name not in before_names:
                        logger.info(f"✓ Playlist '{playlist_name}' created successfully!")
                        return {'success': True, 'message': f"Playlist '{playlist_name}' created successfully"}
                    else:
                        logger.info(f"✓ Playlist '{playlist_name}' updated successfully!")
                        return {'success': True, 'message': f"Playlist '{playlist_name}' updated"}
                else:
                    logger.warning(f"⚠ Playlist upload accepted but '{playlist_name}' not found in Plex. The playlist may be empty if tracks are not in the library.")
                    return {'success': True, 'warning': f"Upload accepted but playlist not visible. Ensure tracks at paths in M3U file are scanned into Plex library section {self.library_section_id}."}

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
