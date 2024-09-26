import os
import json
import platform
import shutil
from shutil import which
import uuid

def config_dir():
    if platform.system() == "Windows":
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
    if platform.system() == "Windows":
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
            cfg_path = os.path.join(config_dir(), "onthespot", "config.json")
        self.__cfg_path = cfg_path
        self.platform = platform.system()
        self.ext_ = ".exe" if self.platform == "Windows" else ""
        self.session_uuid = str(uuid.uuid4())
        self.__template_data = {
            "version": "", # Application version
            "check_for_updates": True, # Check for updates
            "language": "en_US", # Language
            "language_index": 0, # Language Index
            "max_threads": 1, # Maximum number of thread we can spawn
            "parsing_acc_sn": 1, # Serial number of account that will be used for parsing links
            "rotate_acc_sn": False, # Rotate active account for parsing and downloading tracks
            "download_root": os.path.join(os.path.expanduser("~"), "Music", "OnTheSpot"), # Root dir for downloads
            "download_delay": 5, # Seconds to wait before next download
            "track_path_formatter": "{artist}" + os.path.sep + "[{rel_year}] {album}" + os.path.sep + "{track_number}. {name}", # Track path format string
            "podcast_path_formatter": "Episodes" + os.path.sep + "{podcast_name}" + os.path.sep + "{episode_name}", # Episode path format string
            "playlist_path_formatter": "Playlists" + os.path.sep + "{playlist_name} by {playlist_owner}" + os.path.sep + "{name}", # Playlist path format string
            "m3u_name_formatter": "M3U" + os.path.sep + "{name} by {owner}", # M3U name format string
            "watch_bg_for_spotify": 0, # Detect and download songs playing on spotify client,
            "dl_end_padding_bytes": 167,
            "max_retries": 3, # Number of times to retry before giving up on download
            "max_search_results": 10, # Number of search results to display of each type
            "media_format": "mp3", # Song track media format
            "podcast_media_format": "mp3", # Podcast track media format
            "force_raw": False, # Skip media conversion and metadata writing
            "force_premium": False, # Set premium flag to always return true
            "chunk_size": 50000, # Chunk size in bytes to download in
            "recoverable_fail_wait_delay": 10, # No of seconds to wait before failure that can be retried
            "disable_bulk_dl_notices": True, # Hide popups for bulk download buttons
            "inp_enable_lyrics": False, # Enable lyrics download
            "use_lrc_file": False, # Download .lrc file alongside track
            "only_synced_lyrics": False, # Only use synced lyrics
            "use_playlist_path": False, # Use playlist path
            "create_m3u_playlists": False, # Create m3u based playlist
            "translate_file_path": False, # Translate downloaded file path to application language
            "ffmpeg_args": [], # Extra arguments for ffmpeg
            "show_search_thumbnails": True, # Show thumbnails in search view
            "explicit_label": "🅴", # Explicit label in app and download path
            "search_thumb_height": 60, # Thumbnail height ( they are of equal width and height )
            "metadata_seperator": "; ", # Seperator used for metadata fields that have multiple values
            "embed_branding": False,
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
            "embed_lyrics": False,
            "embed_explicit": False,
            "embed_compilation": False,
            "download_copy_btn": False, # Add copy button to downloads
            "download_save_btn": False, # Add save button to downloads
            "download_queue_btn": False, # Add queue button to downloads
            "download_play_btn": False, # Add play button to downloads
            "download_open_btn": True, # Add open button to downloads
            "download_locate_btn": True, # Add locate button to downloads
            "download_delete_btn": False, # Add delete button to downloads
            "theme": "dark", # Light\Dark
            "accounts": [] # Saved account information
        }
        if os.path.isfile(self.__cfg_path):
            self.__config = json.load(open(cfg_path, "r"))
        else:
            try:
                os.makedirs(os.path.dirname(self.__cfg_path), exist_ok=True)
            except (FileNotFoundError, PermissionError):
                fallback_path = os.path.abspath(
                    os.path.join('.config', 'config.json')
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
            os.makedirs(self.get("download_root"), exist_ok=True)
        except (FileNotFoundError, PermissionError):
            print(
                'Current download root cannot be set up at "',
                self.get("download_root"),
                '"; Falling back to : ',
                self.__template_data.get('download_root')
                )
            self.set_(
                'download_root', self.__template_data.get('download_root')
                )
            os.makedirs(self.get("download_root"), exist_ok=True)
        # Set ffmpeg path
        self.app_root = os.path.dirname(os.path.realpath(__file__))
        if os.path.isfile(os.path.join(self.app_root, 'bin', 'ffmpeg', 'ffmpeg' + self.ext_)):
            # Try embedded binary at first
            print('FFMPEG found in package !')
            self.set_('_ffmpeg_bin_path',
                      os.path.abspath(os.path.join(self.app_root, 'bin', 'ffmpeg', 'ffmpeg' + self.ext_)))
        elif os.path.isfile(os.path.join(self.get('ffmpeg_bin_dir', '.'), 'ffmpeg' + self.ext_)):
            # Now try user defined binary path
            print('FFMPEG found at config:ffmpeg_bin_dir !')
            self.set_('_ffmpeg_bin_path',
                      os.path.abspath(os.path.join(self.get('ffmpeg_bin_dir', '.'), 'ffmpeg' + self.ext_)))
        else:
            # Try system binaries as fallback
            print('Attempting to use system ffmpeg binary !')
            self.set_('_ffmpeg_bin_path', os.path.abspath(which('ffmpeg')) if which('ffmpeg') else 'ffmpeg' + self.ext_)
        print("Using ffmpeg binary at: ", self.get('_ffmpeg_bin_path'))
        self.set_('_log_file', os.path.join(cache_dir(), "onthespot", "logs", self.session_uuid, "onthespot.log"))
        self.set_('_cache_dir', os.path.join(cache_dir(), "onthespot"))
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
                self.get("download_root"),
                '"; Falling back to : ',
                fallback_logdir
                )
            self.set_('_log_file', fallback_logdir)
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

    def set_(self, key, value):
        if type(value) in [list, dict]:
            self.__config[key] = value.copy()
        else:
            self.__config[key] = value
        return value

    def update(self):
        os.makedirs(os.path.dirname(self.__cfg_path), exist_ok=True)
        for key in list(set(self.__template_data).difference(set(self.__config))):
            if not key.startswith('_'):
                self.set_(key, self.__template_data[key])
        with open(self.__cfg_path, "w") as cf:
            cf.write(json.dumps(self.__config, indent=4))

    def rollback(self):
        shutil.rmtree(os.path.join(config_dir(), "onthespot", "sessions"))
        with open(self.__cfg_path, "w") as cf:
            cf.write(json.dumps(self.__template_data, indent=4))
        self.__config = self.__template_data

config = Config()
