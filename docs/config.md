# Configuration Guide

This document provides a detailed explanation of all configuration parameters available for the application. Each parameter includes its name, type, and description. Use this guide to adjust settings in the configuration JSON file effectively. 🚀

---

## General Settings

| **Parameter**                      | **Type**  | **Description**                                                      |
| ---------------------------------- | --------- | -------------------------------------------------------------------- |
| `version`                          | `string`  | The version of the application.                                      |
| `use_webui_login`                  | `boolean` | Enables or disables WebUI login functionality.                       |
| `webui_username`                   | `string`  | Username for accessing the WebUI.                                    |
| `webui_password`                   | `string`  | Password for accessing the WebUI.                                    |
| `debug_mode`                       | `boolean` | Activates debug mode for troubleshooting.                            |
| `close_to_tray`                    | `boolean` | If enabled, the app minimizes to the system tray instead of closing. |
| `check_for_updates`                | `boolean` | Automatically checks for updates on startup.                         |
| `language`                         | `string`  | Sets the application language (e.g., `en_US`).                       |
| `language_index`                   | `integer` | Index of the selected language in the UI.                            |
| `parsing_acc_sn`                   | `integer` | Number of parsing attempts for accounts.                             |
| `rotate_acc_sn`                    | `boolean` | Enables automatic rotation of accounts to avoid rate limits.         |
| `download_root`                    | `string`  | Root directory for saving downloaded files.                          |
| `generic_download_root`            | `string`  | Root directory for saving generic downloads.                         |
| `download_delay`                   | `integer` | Delay (in seconds) between downloads to prevent rate limits.         |
| `maximum_download_workers`         | `integer` | Maximum number of concurrent download workers.                       |
| `maximum_queue_workers`            | `integer` | Maximum number of queue workers for managing downloads.              |
| `enable_retry_worker`              | `boolean` | Enables a retry mechanism for failed downloads.                      |
| `retry_worker_delay`               | `integer` | Delay (in minutes) before retrying failed downloads.                 |
| `track_path_formatter`             | `string`  | Defines the file naming format for downloaded tracks.                |
| `podcast_path_formatter`           | `string`  | Defines the file naming format for downloaded podcasts.              |
| `playlist_path_formatter`          | `string`  | Defines the file naming format for downloaded playlists.             |
| `m3u_name_formatter`               | `string`  | Defines the naming format for M3U playlist files.                    |
| `m3u_format`                       | `string`  | Specifies the M3U file format (`m3u` or `m3u8`).                     |
| `ext_seperator`                    | `string`  | Separator for EXTINF metadata in M3U files.                          |
| `ext_path`                         | `string`  | Path format for EXTINF metadata.                                     |
| `max_search_results`               | `integer` | Maximum number of search results displayed per media type.           |
| `media_format`                     | `string`  | Default audio file format for downloads (e.g., `mp3`, `flac`).       |
| `podcast_media_format`             | `string`  | Default file format for downloaded podcasts.                         |
| `file_bitrate`                     | `string`  | Bitrate for downloaded audio files (e.g., `320k`).                   |
| `file_hertz`                       | `integer` | Sampling rate for downloaded audio files (e.g., `44100`).            |
| `illegal_character_replacement`    | `string`  | Replacement character for illegal file path characters.              |
| `force_raw`                        | `boolean` | Downloads raw, unprocessed files without embedding metadata.         |
| `chunk_size`                       | `integer` | File chunk size (in bytes) for downloading.                          |
| `disable_bulk_dl_notices`          | `boolean` | Disables notifications for bulk downloads.                           |
| `save_album_cover`                 | `boolean` | Saves album cover images alongside tracks.                           |
| `album_cover_format`               | `string`  | Format for album cover images (e.g., `png`, `jpg`).                  |
| `inp_enable_lyrics`                | `boolean` | Enables lyrics downloading for tracks.                               |
| `use_lrc_file`                     | `boolean` | Saves lyrics in `.lrc` format.                                       |
| `only_synced_lyrics`               | `boolean` | Downloads only synced lyrics.                                        |
| `use_playlist_path`                | `boolean` | Enables the use of custom paths for playlists.                       |
| `create_m3u_playlists`             | `boolean` | Creates M3U files for downloaded playlists.                          |
| `translate_file_path`              | `boolean` | Translates file paths into the selected application language.        |
| `ffmpeg_args`                      | `array`   | Additional arguments to pass to FFMPEG during processing.            |
| `enable_search_tracks`             | `boolean` | Enables searching for individual tracks.                             |
| `enable_search_albums`             | `boolean` | Enables searching for albums.                                        |
| `enable_search_playlists`          | `boolean` | Enables searching for playlists.                                     |
| `enable_search_artists`            | `boolean` | Enables searching for artists.                                       |
| `enable_search_episodes`           | `boolean` | Enables searching for episodes.                                      |
| `enable_search_shows`              | `boolean` | Enables searching for shows.                                         |
| `enable_search_audiobooks`         | `boolean` | Enables searching for audiobooks.                                    |
| `show_search_thumbnails`           | `boolean` | Displays thumbnails in search results.                               |
| `show_download_thumbnails`         | `boolean` | Displays thumbnails in the download queue.                           |
| `explicit_label`                   | `string`  | Label used to mark explicit content.                                 |
| `search_thumb_height`              | `integer` | Height of thumbnails in the search results.                          |
| `download_youtube_videos`          | `boolean` | Enables downloading videos from YouTube.                             |
| `maximum_generic_resolution`       | `integer` | Maximum resolution for generic video downloads.                      |
| `mirror_spotify_playback`          | `boolean` | Downloads the currently playing track on Spotify.                    |
| `windows_10_explorer_thumbnails`   | `boolean` | Enables embedding of thumbnails for Windows 10 Explorer.             |
| `overwrite_existing_metadata`      | `boolean` | Re-embeds metadata for existing files.                               |
| `embed_branding`                   | `boolean` | Embeds branding information in metadata.                             |
| `embed_cover`                      | `boolean` | Embeds cover art in metadata.                                        |
| `embed_artist`                     | `boolean` | Embeds artist name in metadata.                                      |
| `embed_album`                      | `boolean` | Embeds album name in metadata.                                       |
| `embed_albumartist`                | `boolean` | Embeds album artist name in metadata.                                |
| `embed_name`                       | `boolean` | Embeds track name in metadata.                                       |
| `embed_year`                       | `boolean` | Embeds release year in metadata.                                     |
| `embed_discnumber`                 | `boolean` | Embeds disc number in metadata.                                      |
| `embed_tracknumber`                | `boolean` | Embeds track number in metadata.                                     |
| `embed_genre`                      | `boolean` | Embeds genre in metadata.                                            |
| `embed_performers`                 | `boolean` | Embeds performers in metadata.                                       |
| `embed_producers`                  | `boolean` | Embeds producers in metadata.                                        |
| `embed_writers`                    | `boolean` | Embeds writers in metadata.                                          |
| `embed_label`                      | `boolean` | Embeds record label in metadata.                                     |
| `embed_copyright`                  | `boolean` | Embeds copyright information in metadata.                            |
| `embed_description`                | `boolean` | Embeds description in metadata.                                      |
| `embed_language`                   | `boolean` | Embeds language information in metadata.                             |
| `embed_isrc`                       | `boolean` | Embeds ISRC code in metadata.                                        |
| `embed_length`                     | `boolean` | Embeds track length in metadata.                                     |
| `embed_url`                        | `boolean` | Embeds URL in metadata.                                              |
| `embed_key`                        | `boolean` | Embeds musical key in metadata.                                      |
| `embed_bpm`                        | `boolean` | Embeds BPM (tempo) in metadata.                                      |
| `embed_compilation`                | `boolean` | Marks tracks as part of a compilation in metadata.                   |
| `embed_lyrics`                     | `boolean` | Embeds lyrics in metadata.                                           |
| `embed_explicit`                   | `boolean` | Embeds explicit content information in metadata.                     |
| `embed_upc`                        | `boolean` | Embeds UPC in metadata.                                              |
| `embed_service_id`                 | `boolean` | Embeds service-specific ID in metadata.                              |
| `embed_timesignature`              | `boolean` | Embeds time signature in metadata.                                   |
| `embed_acousticness`               | `boolean` | Embeds acousticness score in metadata.                               |
| `embed_danceability`               | `boolean` | Embeds danceability score in metadata.                               |
| `embed_energy`                     | `boolean` | Embeds energy score in metadata.                                     |
| `embed_instrumentalness`           | `boolean` | Embeds instrumentalness score in metadata.                           |
| `embed_liveness`                   | `boolean` | Embeds liveness score in metadata.                                   |
| `embed_loudness`                   | `boolean` | Embeds loudness score in metadata.                                   |
| `embed_performer`                  | `boolean` | Embeds performer information in metadata.                            |
| `embed_speechiness`                | `boolean` | Embeds speechiness score in metadata.                                |
| `embed_valence`                    | `boolean` | Embeds valence score in metadata.                                    |
| `download_copy_btn`                | `boolean` | Adds a copy button in the download interface.                        |
| `download_open_btn`                | `boolean` | Adds an open button in the download interface.                       |
| `download_locate_btn`              | `boolean` | Adds a locate button in the download interface.                      |
| `download_delete_btn`              | `boolean` | Adds a delete button in the download interface.                      |
| `theme`                            | `string`  | Defines the application's theme (e.g., background and text colors).  |
| `accounts`                         | `array`   | List of user accounts and their configurations.                      |
| `_ffmpeg_bin_path`                 | `string`  | Path to the FFMPEG binary.                                           |
| `_log_file`                        | `string`  | Path to the log file.                                                |
| `_cache_dir`                       | `string`  | Path to the cache directory.                                         |
| `metadata_separator`               | `string`  | Separator for multiple metadata values.                              |
| `audio_download_path`              | `string`  | Path for saving downloaded audio files.                              |
| `movie_file_format`                | `string`  | File format for downloaded movies.                                   |
| `movie_path_formatter`             | `string`  | File naming format for downloaded movies.                            |
| `preferred_subtitle_language`      | `string`  | Preferred language for subtitles.                                    |
| `thumbnail_size`                   | `integer` | Size of thumbnails.                                                  |
| `only_download_synced_lyrics`      | `boolean` | Downloads only synced lyrics.                                        |
| `extinf_separator`                 | `string`  | Separator for EXTINF metadata.                                       |
| `show_file_format`                 | `string`  | File format for downloaded shows.                                    |
| `podcast_file_format`              | `string`  | File format for downloaded podcasts.                                 |
| `extinf_label`                     | `string`  | Label format for EXTINF metadata.                                    |
| `save_lrc_file`                    | `boolean` | Saves lyrics in `.lrc` format.                                       |
| `download_all_available_audio`     | `boolean` | Downloads all available audio versions.                              |
| `rotate_active_account_number`     | `boolean` | Rotates between active accounts automatically.                       |
| `show_path_formatter`              | `string`  | File naming format for downloaded shows.                             |
| `preferred_video_resolution`       | `integer` | Preferred resolution for downloaded videos.                          |
| `download_all_available_subtitles` | `boolean` | Downloads all available subtitles for videos.                        |
| `download_subtitles`               | `boolean` | Enables downloading of subtitles.                                    |
| `disable_download_popups`          | `boolean` | Disables download notifications.                                     |
| `download_lyrics`                  | `boolean` | Enables downloading of lyrics.                                       |
| `video_download_path`              | `string`  | Path for saving downloaded video files.                              |
| `active_account_number`            | `integer` | Index of the currently active account.                               |
| `m3u_path_formatter`               | `string`  | File naming format for M3U playlists.                                |
| `delete_removed`                   | `boolean` | Deletes files that are no longer available in the source.            |
| `preferred_audio_language`         | `string`  | Preferred language for audio tracks.                                 |
| `download_chunk_size`              | `integer` | Chunk size for downloading files.                                    |
| `track_file_format`                | `string`  | File format for downloaded tracks.                                   |
| `enable_search_podcasts`           | `boolean` | Enables searching for podcasts.                                      |
| `create_m3u_file`                  | `boolean` | Creates M3U playlist files.                                          |
| `raw_media_download`               | `boolean` | Downloads raw media without processing or metadata embedding.        |