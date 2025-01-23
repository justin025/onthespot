import json
import os
import uuid
from shutil import which

def config_dir():
    if os.name == "nt":
        if 'APPDATA' in os.environ:
            return os.environ["APPDATA"]
        elif 'LOCALAPPDATA' in os.environ:
            return os.environ["LOCALAPPDATA"]
        else:
            return os.path.join(os.path.expanduser("~"), ".config")
    else:
        if 'XDG_CONFIG_HOME' in os.environ:
            return os.environ["XDG_CONFIG_HOME"]
        else:
            return os.path.join(os.path.expanduser("~"), ".config")


def cache_dir():
    if os.name == "nt":
        if 'TEMP' in os.environ:
            return os.environ["TEMP"]
        else:
            return os.path.join(os.path.expanduser("~"), ".cache")
    else:
        if 'XDG_CACHE_HOME' in os.environ:
            return os.environ["XDG_CACHE_HOME"]
        else:
            return os.path.join(os.path.expanduser("~"), ".cache")


class Config:
    def __init__(self, cfg_path=None):
        if cfg_path is None or not os.path.isfile(cfg_path):
            cfg_path = os.path.join(config_dir(), "onthespot", "otsconfig.json")
        self.__cfg_path = cfg_path
        self.ext_ = ".exe" if os.name == "nt" else ""
        self.session_uuid = str(uuid.uuid4())
        self.__template_data = {
            # System Variables
            "version": "", # Application version
            "debug_mode": False, # Application version
            "language_index": 0, # Language Index
            "m3u_format": "m3u8", # M3U file format
            "ffmpeg_args": [], # Extra arguments for ffmpeg

            # Accounts
            "active_account_number": 0, # Serial number of account that will be used to parse and download media
            "accounts": [
                {
                    "uuid": "public_bandcamp",
                    "service": "bandcamp",
                    "active": True,
                },
                {
                    "uuid": "public_deezer",
                    "service": "deezer",
                    "active": True,
                    "login": {
                        "arl": "public_deezer",
                    }
                },
                {
                    "uuid": "public_soundcloud",
                    "service": "soundcloud",
                    "active": True,
                    "login": {
                        "client_id": "null",
                        "app_version": "null",
                        "app_locale": "null"
                    }
                },
                {
                    "uuid": "public_youtube_music",
                    "service": "youtube_music",
                    "active": True,
                },
            ], # Saved account information

            # Web UI Settings
            "use_webui_login": False, # Enable Web UI Login Page
            "webui_username": "", # Web UI Username
            "webui_password": "", # Web UI Password

            # General Settings
            "language": "en_US", # Language
            "theme": "background-color: #282828; color: white;", # Custom stylesheet
            "explicit_label": "🅴", # Explicit label in app and download path
            "download_copy_btn": False, # Add copy button to downloads
            "download_open_btn": True, # Add open button to downloads
            "download_locate_btn": True, # Add locate button to downloads
            "download_delete_btn": False, # Add delete button to downloads
            "show_search_thumbnails": True, # Show thumbnails in search view
            "show_download_thumbnails": False, # Show thumbnails in download view
            "thumbnail_size": 60, # Thumbnail height and width in px
            "max_search_results": 10, # Number of search results to display of each type
            "disable_download_popups": False, # Hide download popups
            "windows_10_explorer_thumbnails": False, # Use old id3 format to support windows 10 explorer (not the standard format)
            "mirror_spotify_playback": False, # Mirror spotify playback
            "close_to_tray": False, # Close application to tray
            "check_for_updates": True, # Check for updates
            "illegal_character_replacement": "-", # Character used to replace illegal characters or values in path
            "raw_media_download": False, # Skip media conversion and metadata writing
            "rotate_active_account_number": False, # Rotate active account for parsing and downloading tracks
            "download_delay": 3, # Seconds to wait before next download attempt
            "download_chunk_size": 50000, # Chunk size in bytes to download in
            "maximum_queue_workers": 1, # Maximum number of queue workers
            "maximum_download_workers": 1, # Maximum number of download workers
            "enable_retry_worker": False, # Enable retry worker, automatically retries failed downloads after a set time
            "retry_worker_delay": 10, # Amount of time to wait before retrying failed downloads, in minutes

            # Search Settings
            "enable_search_tracks": True, # Enable listed category in search
            "enable_search_albums": True, # Enable listed category in search
            "enable_search_playlists": True, # Enable listed category in search
            "enable_search_artists": True, # Enable listed category in search
            "enable_search_episodes": True, # Enable listed category in search
            "enable_search_podcasts": True, # Enable listed category in search
            "enable_search_audiobooks": True, # Enable listed category in search

            # Audio Download Settings
            "audio_download_path": os.path.join(os.path.expanduser("~"), "Music", "OnTheSpot"), # Root dir for audio downloads
            "track_file_format": "mp3", # Song track media format
            "track_path_formatter": "Tracks" + os.path.sep + "{album_artist}" + os.path.sep + "[{year}] {album}" + os.path.sep + "{track_number}. {name}", # Track path format string
            "podcast_file_format": "mp3", # Podcast track media format
            "podcast_path_formatter": "Episodes" + os.path.sep + "{album}" + os.path.sep + "{name}", # Episode path format string
            "use_playlist_path": False, # Use playlist path
            "playlist_path_formatter": "Playlists" + os.path.sep + "{playlist_name} by {playlist_owner}" + os.path.sep + "{playlist_number}. {name} - {artist}", # Playlist path format string
            "create_m3u_file": False, # Create m3u based playlist
            "m3u_path_formatter": "M3U" + os.path.sep + "{playlist_name} by {playlist_owner}", # M3U name format string
            "extinf_separator": "; ", # M3U EXTINF metadata separator
            "extinf_label": "{playlist_number}. {artist} - {name}", # M3U EXTINF path
            "save_album_cover": False, # Save album covers to a file
            "album_cover_format": "png", # Album cover format
            "file_bitrate": "320k", # Converted file bitrate
            "file_hertz": 44100, # Converted file hertz
            "use_custom_file_bitrate": False, # Use bitrate specified by file bitrate
            "download_lyrics": False, # Enable lyrics download
            "only_download_synced_lyrics": False, # Only download synced lyrics
            "only_download_plain_lyrics": False, # Only download plain lyrics
            "save_lrc_file": False, # Download .lrc file alongside track
            "translate_file_path": False, # Translate downloaded file path to application language

            # Audio Metadata Settings
            "metadata_separator": "; ", # Separator used for metadata fields that have multiple values
            "overwrite_existing_metadata": False, # Overwrite metadata in files that 'Already Exist'
            "embed_branding": False,
            "embed_cover": True,
            "embed_artist": True,
            "embed_album": True,
            "embed_albumartist": True,
            "embed_name": True,
            "embed_year": True,
            "embed_discnumber": True,
            "embed_tracknumber": True,
            "embed_genre": True,
            "embed_performers": True,
            "embed_producers": True,
            "embed_writers": True,
            "embed_label": True,
            "embed_copyright": True,
            "embed_description": True,
            "embed_language": True,
            "embed_isrc": True,
            "embed_length": True,
            "embed_url": True,
            "embed_key": True,
            "embed_bpm": True,
            "embed_compilation": True,
            "embed_lyrics": False,
            "embed_explicit": False,
            "embed_upc": False,
            "embed_service_id": False,
            "embed_timesignature": False,
            "embed_acousticness": False,
            "embed_danceability": False,
            "embed_energy": False,
            "embed_instrumentalness": False,
            "embed_liveness": False,
            "embed_loudness": False,
            "embed_speechiness": False,
            "embed_valence": False,

            # Video Download Settings
            "video_download_path": os.path.join(os.path.expanduser("~"), "Videos", "OnTheSpot"), # Root dir for audio downloads
            "movie_file_format": "mp4",
            "movie_path_formatter": "Movies" + os.path.sep + "{name} ({release_year})", # Show path format string
            "show_file_format": "mp4",
            "show_path_formatter": "Shows" + os.path.sep + "{show_name}" + os.path.sep + "Season {season_number}" + os.path.sep + "{episode_number}. {name}", # Show path format string
            "preferred_video_resolution": 1080, # Maximum video resolution for Generic Downloader
            "download_subtitles": False, # Download Subtitles
            "preferred_audio_language": "en-US",
            "preferred_subtitle_language": "en-US",
            "download_all_available_audio": False,
            "download_all_available_subtitles": False,
        }
        if os.path.isfile(self.__cfg_path):
            self.__config = json.load(open(cfg_path, "r"))
        else:
            try:
                os.makedirs(os.path.dirname(self.__cfg_path), exist_ok=True)
            except (FileNotFoundError, PermissionError):
                fallback_path = os.path.abspath(
                    os.path.join('.config', 'otsconfig.json')
                    )
                print(
                    'Critical error.. Configuration file could not be '
                    'created at "{self.__cfg_path}"; Trying : {fallback_path}'
                    )
                self.__cfg_path = fallback_path
                os.makedirs(os.path.dirname(self.__cfg_path), exist_ok=True)
            with open(self.__cfg_path, "w") as cf:
                cf.write(json.dumps(self.__template_data, indent=4))
            self.__config = self.__template_data
        try:
            os.makedirs(self.get("audio_download_path"), exist_ok=True)
            os.makedirs(self.get("video_download_path"), exist_ok=True)
        except (FileNotFoundError, PermissionError):
            print(
                'Current download root cannot be set up at "',
                self.get("audio_download_path"),
                '"; Falling back to : ',
                self.__template_data.get('audio_download_path')
                )
            self.set(
                'audio_download_path', self.__template_data.get('audio_download_path')
                )
            os.makedirs(self.get("audio_download_path"), exist_ok=True)
        # Set ffmpeg path
        self.app_root = os.path.dirname(os.path.realpath(__file__))
        if os.name != 'nt' and os.path.exists('/usr/bin/ffmpeg'):
            # Try system binaries first
            print('Attempting to use system ffmpeg binary !')
            self.set('_ffmpeg_bin_path', '/usr/bin/ffmpeg')
        elif which('ffmpeg'):
            print('Attempting to use ffmpeg binary in path !')
            self.set('_ffmpeg_bin_path', os.path.abspath(which('ffmpeg')))
        elif os.path.isfile(os.path.join(self.app_root, 'bin', 'ffmpeg', 'ffmpeg' + self.ext_)):
            # Try embedded binary next
            print('FFMPEG found in package !')
            self.set('_ffmpeg_bin_path',
                      os.path.abspath(os.path.join(self.app_root, 'bin', 'ffmpeg', 'ffmpeg' + self.ext_)))
        elif os.path.isfile(os.path.join(self.get('ffmpeg_bin_dir', '.'), 'ffmpeg' + self.ext_)):
            # Try user defined binary path neither are found
            print('FFMPEG found at config:ffmpeg_bin_dir !')
            self.set('_ffmpeg_bin_path',
                      os.path.abspath(os.path.join(self.get('ffmpeg_bin_dir', '.'), 'ffmpeg' + self.ext_)))
        else:
            print('Failed to find ffmpeg binary, please consider installing ffmpeg or defining its path.')
        print("Using ffmpeg binary at: ", self.get('_ffmpeg_bin_path'))
        self.set('_log_file', os.path.join(cache_dir(), "onthespot", "logs", self.session_uuid, "onthespot.log"))
        self.set('_cache_dir', os.path.join(cache_dir(), "onthespot"))
        try:
            os.makedirs(
                os.path.dirname(self.get("_log_file")), exist_ok=True
                )
        except (FileNotFoundError, PermissionError):
            fallback_logdir = os.path.abspath(os.path.join(
                ".logs", self.session_uuid, "onthespot.log"
                )
            )
            print(
                'Current logging dir cannot be set up at "',
                self.get("audio_download_path"),
                '"; Falling back to : ',
                fallback_logdir
                )
            self.set('_log_file', fallback_logdir)
            os.makedirs(
                os.path.dirname(self.get("_log_file")), exist_ok=True
                )


    def get(self, key, default=None):
        if key in self.__config:
            return self.__config[key]
        elif key in self.__template_data:
            return self.__template_data[key]
        else:
            return default


    def set(self, key, value):
        if type(value) in [list, dict]:
            self.__config[key] = value.copy()
        else:
            self.__config[key] = value
        return value


    def update(self):
        os.makedirs(os.path.dirname(self.__cfg_path), exist_ok=True)
        for key in list(set(self.__template_data).difference(set(self.__config))):
            if not key.startswith('_'):
                self.set(key, self.__template_data[key])
        with open(self.__cfg_path, "w") as cf:
            cf.write(json.dumps(self.__config, indent=4))


    def rollback(self):
        with open(self.__cfg_path, "w") as cf:
            cf.write(json.dumps(self.__template_data, indent=4))
        self.__config = self.__template_data

    def apply_overrides(self, overrides):
        for key, value in overrides.items():
            if key in self.__config or key in self.__template_data:
                current_value = self.get(key)
                if isinstance(current_value, bool):
                    value = value.lower() in ("true", "1", "yes")
                elif isinstance(current_value, int):
                    value = int(value)
                elif isinstance(current_value, float):
                    value = float(value)

                print(f"Overriding configuration : {key} = {value}")
                self.set(key, value)
            elif key=="download":
                print(f"Direct downloading {value}.")
            else:
                print(f"Warning: parameter {key} doesn't exist in configuration and will be discarded.")

        self.update()

config = Config()
