import os
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QSpinBox, QComboBox, QWidget
from ..otsconfig import config


class NonScrollableSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()


class NonScrollableComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


def load_config(self):
    # Dev Tools
    self.inp_settings_scrollarea_value.valueChanged.connect(self.settings_scroll_area.verticalScrollBar().setValue)
    if not config.get('debug_mode'):
        self.inp_settings_scrollarea_value.hide()

    # Hide Popup Settings
    self.group_search_items.hide()
    self.group_download_items.hide()

    # Icons
    self.toggle_theme_button.setIcon(self.get_icon('light'))
    self.inp_export_logs.setIcon(self.get_icon('export_file'))

    self.inp_language.insertItem(0, self.get_icon('en_US'), "English")
    self.inp_language.insertItem(1, self.get_icon('de_DE'), "Deutsch")
    self.inp_language.insertItem(2, self.get_icon('pt_PT'), "Português")
    self.inp_language.insertItem(999, self.get_icon('pirate_flag'), "Contribute")
    self.inp_language.currentIndexChanged.connect(self.contribute)

    self.inp_login_service.insertItem(0, self.get_icon('apple_music'), "")
    self.inp_login_service.insertItem(1, self.get_icon('bandcamp'), "")
    self.inp_login_service.insertItem(2, self.get_icon('deezer'), "")
    self.inp_login_service.insertItem(3, self.get_icon('qobuz'), "")
    self.inp_login_service.insertItem(4, self.get_icon('soundcloud'), "")
    self.inp_login_service.insertItem(5, self.get_icon('spotify'), "")
    self.inp_login_service.insertItem(6, self.get_icon('tidal'), "")
    self.inp_login_service.insertItem(7, self.get_icon('youtube_music'), "")
    self.inp_login_service.insertItem(8, self.get_icon('generic'), "")
    self.inp_login_service.setCurrentIndex(5)

    #self.btn_reset_config.setIcon(self.get_icon('trash'))
    self.btn_save_config.setIcon(self.get_icon('save'))
    self.btn_download_root_browse.setIcon(self.get_icon('folder'))
    self.btn_generic_download_root_browse.setIcon(self.get_icon('folder'))
    self.btn_download_tmp_browse.setIcon(self.get_icon('folder'))
    self.btn_search.setIcon(self.get_icon('search'))
    self.btn_search_filter_toggle.setIcon(self.get_icon('collapse_down'))
    self.btn_download_filter_toggle.setIcon(self.get_icon('collapse_up'))

    # Text
    self.inp_language.setCurrentIndex(config.get("language_index"))
    self.inp_explicit_label.setText(config.get("explicit_label"))
    self.inp_file_bitrate.setText(config.get("file_bitrate"))
    self.inp_file_hertz.setValue(config.get("file_hertz"))
    self.inp_download_root.setText(config.get("download_root"))
    self.inp_generic_download_root.setText(config.get("generic_download_root"))
    self.inp_download_delay.setValue(config.get("download_delay"))
    self.inp_max_search_results.setValue(config.get("max_search_results"))
    self.inp_chunk_size.setValue(config.get("chunk_size"))
    self.inp_media_format.setText(config.get("media_format"))
    self.inp_podcast_media_format.setText(config.get("podcast_media_format"))
    self.inp_illegal_character_replacement.setText(config.get("illegal_character_replacement"))
    self.inp_track_formatter.setText(config.get("track_path_formatter"))
    self.inp_podcast_path_formatter.setText(config.get("podcast_path_formatter"))
    self.inp_playlist_path_formatter.setText(config.get("playlist_path_formatter"))
    self.inp_m3u_name_formatter.setText(config.get("m3u_name_formatter"))
    self.inp_ext_seperator.setText(config.get("ext_seperator"))
    self.inp_ext_path.setText(config.get("ext_path"))
    self.inp_album_cover_format.setText(config.get("album_cover_format"))
    self.inp_search_thumb_height.setValue(config.get("search_thumb_height"))
    self.inp_metadata_seperator.setText(config.get("metadata_seperator"))
    self.inp_maximum_queue_workers.setValue(config.get("maximum_queue_workers"))
    self.inp_maximum_download_workers.setValue(config.get("maximum_download_workers"))
    self.inp_maximum_generic_resolution.setValue(config.get("maximum_generic_resolution"))
    self.inp_retry_worker_delay.setValue(config.get("retry_worker_delay"))

    # Checkboxes
    self.inp_overwrite_existing_metadata.setChecked(config.get("overwrite_existing_metadata"))
    self.inp_embed_upc.setChecked(config.get("embed_upc"))
    self.inp_embed_service_id.setChecked(config.get("embed_service_id"))
    self.inp_windows_explorer_thumbnails.setChecked(config.get("windows_10_explorer_thumbnails"))
    self.inp_close_to_tray.setChecked(config.get("close_to_tray"))
    self.inp_enable_retry_worker.setChecked(config.get("enable_retry_worker"))

    self.inp_enable_search_tracks.setChecked(config.get("enable_search_tracks"))
    self.inp_enable_search_albums.setChecked(config.get("enable_search_albums"))
    self.inp_enable_search_artists.setChecked(config.get("enable_search_artists"))
    self.inp_enable_search_playlists.setChecked(config.get("enable_search_playlists"))
    self.inp_enable_search_episodes.setChecked(config.get("enable_search_episodes"))
    self.inp_enable_search_shows.setChecked(config.get("enable_search_shows"))
    self.inp_enable_search_audiobooks.setChecked(config.get("enable_search_audiobooks"))

    self.inp_show_download_thumbnails.setChecked(config.get("show_download_thumbnails"))
    self.inp_show_search_thumbnails.setChecked(config.get("show_search_thumbnails"))
    self.inp_use_lrc_file.setChecked(config.get("use_lrc_file"))
    self.inp_rotate_acc_sn.setChecked(config.get("rotate_acc_sn"))
    self.inp_download_copy_btn.setChecked(config.get("download_copy_btn"))
    self.inp_download_open_btn.setChecked(config.get("download_open_btn"))
    self.inp_download_locate_btn.setChecked(config.get("download_locate_btn"))
    self.inp_download_delete_btn.setChecked(config.get("download_delete_btn"))
    self.inp_translate_file_path.setChecked(config.get("translate_file_path"))
    self.inp_raw_download.setChecked(config.get("force_raw"))
    self.inp_disable_bulk_popup.setChecked(config.get("disable_bulk_dl_notices"))
    self.inp_save_album_cover.setChecked(config.get("save_album_cover"))
    self.inp_enable_lyrics.setChecked(config.get("inp_enable_lyrics"))
    self.inp_only_synced_lyrics.setChecked(config.get("only_synced_lyrics"))
    self.inp_use_playlist_path.setChecked(config.get("use_playlist_path"))
    self.inp_create_playlists.setChecked(config.get("create_m3u_playlists"))
    self.inp_check_for_updates.setChecked(config.get("check_for_updates"))

    self.inp_embed_cover.setChecked(config.get("embed_cover"))
    self.inp_embed_branding.setChecked(config.get("embed_branding"))
    self.inp_embed_artist.setChecked(config.get("embed_artist"))
    self.inp_embed_album.setChecked(config.get('embed_album'))
    self.inp_embed_albumartist.setChecked(config.get('embed_albumartist'))
    self.inp_embed_name.setChecked(config.get('embed_name'))
    self.inp_embed_year.setChecked(config.get('embed_year'))
    self.inp_embed_discnumber.setChecked(config.get('embed_discnumber'))
    self.inp_embed_tracknumber.setChecked(config.get('embed_tracknumber'))
    self.inp_embed_genre.setChecked(config.get('embed_genre'))
    self.inp_embed_performers.setChecked(config.get('embed_performers'))
    self.inp_embed_producers.setChecked(config.get('embed_producers'))
    self.inp_embed_writers.setChecked(config.get('embed_writers'))
    self.inp_embed_label.setChecked(config.get('embed_label'))
    self.inp_embed_copyright.setChecked(config.get('embed_copyright'))
    self.inp_embed_description.setChecked(config.get('embed_description'))
    self.inp_embed_language.setChecked(config.get('embed_language'))
    self.inp_embed_isrc.setChecked(config.get('embed_isrc'))
    self.inp_embed_length.setChecked(config.get('embed_length'))
    self.inp_embed_key.setChecked(config.get('embed_key'))
    self.inp_embed_bpm.setChecked(config.get('embed_bpm'))
    self.inp_embed_url.setChecked(config.get('embed_url'))
    self.inp_embed_lyrics.setChecked(config.get('embed_lyrics'))
    self.inp_embed_explicit.setChecked(config.get('embed_explicit'))
    self.inp_embed_compilation.setChecked(config.get('embed_compilation'))
    self.inp_embed_timesignature.setChecked(config.get('embed_timesignature'))
    self.inp_embed_acousticness.setChecked(config.get('embed_acousticness'))
    self.inp_embed_danceability.setChecked(config.get('embed_danceability'))
    self.inp_embed_energy.setChecked(config.get('embed_energy'))
    self.inp_embed_instrumentalness.setChecked(config.get('embed_instrumentalness'))
    self.inp_embed_liveness.setChecked(config.get('embed_liveness'))
    self.inp_embed_loudness.setChecked(config.get('embed_loudness'))
    self.inp_embed_speechiness.setChecked(config.get('embed_speechiness'))
    self.inp_embed_valence.setChecked(config.get('embed_valence'))
    self.inp_mirror_spotify_playback.setChecked(config.get('mirror_spotify_playback'))
    self.inp_download_youtube_videos.setChecked(config.get('download_youtube_videos'))
    self.inp_delete_removed.setChecked(config.get("delete_removed"))

    # Disable scrolling to change values of QSpinBoxes and QComboBoxes
    do_not_scroll = [
        "inp_login_service",
        "inp_language",
        "inp_max_search_results",
        "inp_search_thumb_height",
        "inp_maximum_generic_resolution",
        "inp_retry_worker_delay",
        "inp_file_hertz",
        "inp_download_delay",
        "inp_chunk_size",
        "inp_maximum_queue_workers",
        "inp_maximum_download_workers"
        ]

    for name in do_not_scroll:
        widget = self.findChild(QWidget, name)
        if isinstance(widget, QSpinBox):
            # Create new NonScrollableSpinBox
            new_widget = NonScrollableSpinBox()
            new_widget.setRange(widget.minimum(), widget.maximum())
            new_widget.setValue(widget.value())
            new_widget.setGeometry(widget.geometry())
            new_widget.setMinimumSize(widget.minimumSize())
            new_widget.setMaximumSize(widget.maximumSize())
        elif isinstance(widget, QComboBox):
            # Create new NonScrollableComboBox
            new_widget = NonScrollableComboBox()
            new_widget.addItems([widget.itemText(i) for i in range(widget.count())])
            new_widget.setCurrentIndex(widget.currentIndex())
            new_widget.setGeometry(widget.geometry())
            new_widget.setMinimumSize(widget.minimumSize())
            new_widget.setMaximumSize(widget.maximumSize())
            # Copy icons
            for i in range(widget.count()):
                icon = widget.itemIcon(i)
                if not icon.isNull():
                    new_widget.setItemIcon(i, icon)

        # Replace the widget in the layout
        widget.parent().layout().replaceWidget(widget, new_widget)
        # Delete the original widget
        widget.deleteLater()

        # Store the newly created widget in the previous instance variable
        setattr(self, name, new_widget)


def save_config(self):
    # Missing Theme
    config.set_('language_index', self.inp_language.currentIndex())
    config.set_('explicit_label', self.inp_explicit_label.text())
    config.set_('download_root', self.inp_download_root.text())
    config.set_('generic_download_root', self.inp_generic_download_root.text())
    config.set_('file_bitrate', self.inp_file_bitrate.text())
    config.set_('file_hertz', self.inp_file_hertz.value())
    config.set_('track_path_formatter', self.inp_track_formatter.text())
    config.set_('podcast_path_formatter', self.inp_podcast_path_formatter.text())
    config.set_('playlist_path_formatter', self.inp_playlist_path_formatter.text())
    config.set_('m3u_name_formatter', self.inp_m3u_name_formatter.text())
    config.set_('ext_seperator', self.inp_ext_seperator.text())
    config.set_('ext_path', self.inp_ext_path.text())
    config.set_('album_cover_format', self.inp_album_cover_format.text())
    config.set_('download_delay', self.inp_download_delay.value())
    config.set_('chunk_size', self.inp_chunk_size.value())
    config.set_('search_thumb_height', self.inp_search_thumb_height.value())
    config.set_('disable_bulk_dl_notices', self.inp_disable_bulk_popup.isChecked())
    config.set_('metadata_seperator', self.inp_metadata_seperator.text())
    config.set_('max_search_results', self.inp_max_search_results.value())
    config.set_('media_format', self.inp_media_format.text())
    config.set_('podcast_media_format', self.inp_podcast_media_format.text())
    config.set_('illegal_character_replacement', self.inp_illegal_character_replacement.text())
    config.set_('maximum_queue_workers', self.inp_maximum_queue_workers.value())
    config.set_('maximum_download_workers', self.inp_maximum_download_workers.value())
    config.set_('maximum_generic_resolution', self.inp_maximum_generic_resolution.value())
    config.set_('retry_worker_delay', self.inp_retry_worker_delay.value())

    # Checkboxes: config.set_('key', bool)
    config.set_('overwrite_existing_metadata', self.inp_overwrite_existing_metadata.isChecked())
    config.set_('embed_upc', self.inp_embed_upc.isChecked())
    config.set_('embed_service_id', self.inp_embed_service_id.isChecked())
    config.set_('windows_10_explorer_thumbnails', self.inp_windows_explorer_thumbnails.isChecked())
    config.set_('close_to_tray', self.inp_close_to_tray.isChecked())
    config.set_('enable_retry_worker', self.inp_enable_retry_worker.isChecked())

    config.set_('enable_search_tracks', self.inp_enable_search_tracks.isChecked())
    config.set_('enable_search_albums', self.inp_enable_search_albums.isChecked())
    config.set_('enable_search_playlists', self.inp_enable_search_playlists.isChecked())
    config.set_('enable_search_artists', self.inp_enable_search_artists.isChecked())
    config.set_('enable_search_episodes', self.inp_enable_search_episodes.isChecked())
    config.set_('enable_search_shows', self.inp_enable_search_shows.isChecked())
    config.set_('enable_search_audiobooks', self.inp_enable_search_audiobooks.isChecked())

    config.set_('show_download_thumbnails', self.inp_show_download_thumbnails.isChecked())
    config.set_('show_search_thumbnails', self.inp_show_search_thumbnails.isChecked())
    config.set_('use_lrc_file', self.inp_use_lrc_file.isChecked())
    config.set_('rotate_acc_sn', self.inp_rotate_acc_sn.isChecked())
    config.set_('translate_file_path', self.inp_translate_file_path.isChecked())
    config.set_('force_raw', self.inp_raw_download.isChecked())
    config.set_('download_copy_btn', self.inp_download_copy_btn.isChecked())
    config.set_('download_open_btn', self.inp_download_open_btn.isChecked())
    config.set_('download_locate_btn', self.inp_download_locate_btn.isChecked())
    config.set_('download_delete_btn', self.inp_download_delete_btn.isChecked())
    config.set_('save_album_cover', self.inp_save_album_cover.isChecked())
    config.set_('inp_enable_lyrics', self.inp_enable_lyrics.isChecked())
    config.set_('only_synced_lyrics', self.inp_only_synced_lyrics.isChecked())
    config.set_('use_playlist_path', self.inp_use_playlist_path.isChecked())
    config.set_('create_m3u_playlists', self.inp_create_playlists.isChecked())
    config.set_('check_for_updates', self.inp_check_for_updates.isChecked())
    config.set_('embed_cover', self.inp_embed_cover.isChecked())
    config.set_('embed_branding', self.inp_embed_branding.isChecked())
    config.set_('embed_artist', self.inp_embed_artist.isChecked())
    config.set_('embed_album', self.inp_embed_album.isChecked())
    config.set_('embed_albumartist', self.inp_embed_albumartist.isChecked())
    config.set_('embed_name', self.inp_embed_name.isChecked())
    config.set_('embed_year', self.inp_embed_year.isChecked())
    config.set_('embed_discnumber', self.inp_embed_discnumber.isChecked())
    config.set_('embed_tracknumber', self.inp_embed_tracknumber.isChecked())
    config.set_('embed_genre', self.inp_embed_genre.isChecked())
    config.set_('embed_performers', self.inp_embed_performers.isChecked())
    config.set_('embed_producers', self.inp_embed_producers.isChecked())
    config.set_('embed_writers', self.inp_embed_writers.isChecked())
    config.set_('embed_label', self.inp_embed_label.isChecked())
    config.set_('embed_copyright', self.inp_embed_copyright.isChecked())
    config.set_('embed_description', self.inp_embed_description.isChecked())
    config.set_('embed_language', self.inp_embed_language.isChecked())
    config.set_('embed_isrc', self.inp_embed_isrc.isChecked())
    config.set_('embed_length', self.inp_embed_length.isChecked())
    config.set_('embed_key', self.inp_embed_key.isChecked())
    config.set_('embed_bpm', self.inp_embed_bpm.isChecked())
    config.set_('embed_url', self.inp_embed_url.isChecked())
    config.set_('embed_lyrics', self.inp_embed_lyrics.isChecked())
    config.set_('embed_explicit', self.inp_embed_explicit.isChecked())
    config.set_('embed_compilation', self.inp_embed_compilation.isChecked())
    config.set_('embed_timesignature', self.inp_embed_timesignature.isChecked())
    config.set_('embed_acousticness', self.inp_embed_acousticness.isChecked())
    config.set_('embed_danceability', self.inp_embed_danceability.isChecked())
    config.set_('embed_energy', self.inp_embed_energy.isChecked())
    config.set_('embed_instrumentalness', self.inp_embed_instrumentalness.isChecked())
    config.set_('embed_liveness', self.inp_embed_liveness.isChecked())
    config.set_('embed_loudness', self.inp_embed_loudness.isChecked())
    config.set_('embed_speechiness', self.inp_embed_speechiness.isChecked())
    config.set_('embed_valence', self.inp_embed_valence.isChecked())
    config.set_('mirror_spotify_playback', self.inp_mirror_spotify_playback.isChecked())
    config.set_('download_youtube_videos', self.inp_download_youtube_videos.isChecked())
    config.set_('delete_removed', self.inp_delete_removed.isChecked())
    config.update()
