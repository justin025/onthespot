import os
# Required for librespot-python
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
import sys
import threading
from PyQt6.QtCore import QTranslator
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QStyle
from .gui.mainui import MainWindow
from .gui.minidialog import MiniDialog
from .otsconfig import config
from .parse_item import parsingworker
from .runtimedata import get_logger, set_init_tray

logger = get_logger('gui')


class TrayApp:
    def __init__(self, main_window):
        self.main_window = main_window
        self.tray_icon = QSystemTrayIcon(self.main_window)
        self.tray_icon.setIcon(QIcon(os.path.join(config.app_root, 'resources', 'icons', 'onthespot.png')))
        self.tray_icon.setVisible(True)
        tray_menu = QMenu()
        tray_menu.addAction("Show", self.show_window)
        tray_menu.addAction("Quit", self.quit_application)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_clicked)


    def tray_icon_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()


    def show_window(self):
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()


    def quit_application(self):
        QApplication.quit()


def main():
    logger.info('Starting application in \n3\n2\n1')
    version = "v1.0.7"
    logger.info(f'OnTheSpot Version: {version}')

    if config.get('version') != version:
        config.set("version", version)

        # Migration (>v1.0.3)
        if isinstance(config.get("file_hertz"), str):
            config.set("file_hertz", int(config.get("file_hertz")))

        # Migration (>v1.0.4)
        if config.get('theme') == 'dark':
            config.set('theme', f'background-color: #282828; color: white;')
        elif config.get('theme') == 'light':
            config.set('theme', f'background-color: white; color: black;')

        # Migration (>v1.0.5)
        cfg_copy = config.get('accounts').copy()
        for account in cfg_copy:
            if account['uuid'] == 'public_youtube':
                account['uuid'] = 'public_youtube_music'
                account['service'] = 'youtube_music'
        config.set('accounts', cfg_copy)

        # Migration (>v1.0.7)
        config.set('active_account_number', config.get('parsing_acc_sn'))
        config.set('thumbnail_size', config.get('search_thumb_height'))
        config.set('disable_download_popups', config.get('disable_bulk_dl_notices'))
        config.set('raw_media_download', config.get('force_raw'))
        config.set('download_chunk_size', config.get('chunk_size'))
        config.set('rotate_active_account_number', config.get('rotate_acc_sn'))
        config.set('audio_download_path', config.get('download_root'))
        config.set('track_file_format', config.get('media_format'))
        config.set('podcast_file_format', config.get('podcast_media_format'))
        config.set('video_download_path', config.get('generic_download_root'))
        config.set('create_m3u_file', config.get('create_m3u_playlists'))
        config.set('m3u_path_formatter', config.get('m3u_name_formatter'))
        config.set('enable_search_podcasts', config.get('enable_search_shows'))
        config.set('extinf_separator', config.get('ext_seperator'))
        config.set('extinf_label', config.get('ext_path'))
        config.set('download_lyrics', config.get('inp_enable_lyrics'))
        config.set('save_lrc_file', config.get('use_lrc_file'))
        config.set('only_download_synced_lyrics', config.get('only_synced_lyrics'))
        config.set('preferred_video_resolution', config.get('maximum_generic_resolution'))
        config.set('use_custom_file_bitrate', True)

    # Language
    if config.get("language_index") == 0:
        config.set("language", "en_US")
    elif config.get("language_index") == 1:
        config.set("language", "de_DE")
    elif config.get("language_index") == 2:
        config.set("language", "pt_PT")
    else:
        logger.info(f'Unknown language index: {config.get("language_index")}')
        config.set("language", "en_US")

    config.update()

    app = QApplication(sys.argv)

    translator = QTranslator()
    path = os.path.join(os.path.join(config.app_root, 'resources', 'translations'),
                 f"{config.get('language')}.qm")
    translator.load(path)
    app.installTranslator(translator)

    # Start Item Parser
    thread = threading.Thread(target=parsingworker)
    thread.daemon = True
    thread.start()

    # Check for start URL
    try:
        if sys.argv[1] == "-u" or sys.argv[1] == "--url":
            start_url = sys.argv[2]
        else:
            start_url = ""
    except IndexError:
        start_url = ""

    _dialog = MiniDialog()
    window = MainWindow(_dialog, start_url)

    if config.get('close_to_tray'):
        set_init_tray(True)
        tray_app = TrayApp(window)

    app.setDesktopFileName('org.onthespot.OnTheSpot')
    app.exec()

    logger.info('Good bye ..')
    os._exit(0)


if __name__ == '__main__':
    main()
