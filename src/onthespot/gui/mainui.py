import os
import queue
import time
import threading
import uuid
from PyQt6 import uic, QtNetwork, QtGui
from PyQt6.QtCore import QThread, QDir, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QHeaderView, QLabel, QPushButton, QProgressBar, QTableWidgetItem, QFileDialog
from ..exceptions import EmptySearchResultException
from ..utils.spotify import search_by_term, get_thumbnail
from ..utils.utils import fetch_account_uuid, name_by_from_sdata, login_user, remove_user, get_url_data, re_init_session, latest_release, open_item
from ..worker import LoadSessions, ParsingQueueProcessor, MediaWatcher, PlayListMaker, DownloadWorker
from ..worker.zeroconf import new_session
from .dl_progressbtn import DownloadActionsButtons
from .minidialog import MiniDialog
from ..otsconfig import config_dir, config
from ..runtimedata import get_logger, download_queue, downloads_status, downloaded_data, failed_downloads, cancel_list, \
    session_pool, thread_pool
from .thumb_listitem import LabelWithThumb
from urllib3.exceptions import MaxRetryError, NewConnectionError

logger = get_logger('gui.main_ui')


def dl_progress_update(data):
    media_id = data[0]
    status = data[1]
    progress = data[2]
    try:
        if status is not None:
            if progress == [0, 100]:
                downloads_status[media_id]["btn"]['cancel'].hide()
                if config.get("download_copy_btn"):
                    downloads_status[media_id]['btn']['copy'].show()
                downloads_status[media_id]["btn"]['retry'].show()
            elif progress != [0, 100]:
                downloads_status[media_id]["btn"]['retry'].hide()
                if config.get("download_copy_btn"):
                    downloads_status[media_id]['btn']['copy'].show()
                downloads_status[media_id]["btn"]['cancel'].show()
            downloads_status[media_id]["status_label"].setText(status)
            logger.debug(f"Updating status text for download item '{media_id}' to '{status}'")
        if progress != None:
            percent = int((progress[0] / progress[1]) * 100)
            if percent >= 100:
                downloads_status[media_id]['btn']['cancel'].hide()
                downloads_status[media_id]['btn']['retry'].hide()
                if config.get("download_copy_btn"):
                    downloads_status[media_id]['btn']['copy'].show()
                if config.get("download_play_btn"):
                    downloads_status[media_id]['btn']['play'].show()
                if config.get("download_save_btn"):
                    downloads_status[media_id]['btn']['save'].show()
                if config.get("download_queue_btn"):
                    downloads_status[media_id]['btn']['queue'].show()
                if config.get("download_open_btn"):
                    downloads_status[media_id]['btn']['open'].show()
                if config.get("download_locate_btn"):
                    downloads_status[media_id]['btn']['locate'].show()
                if config.get("download_delete_btn"):
                    downloads_status[media_id]['btn']['delete'].show()
                downloaded_data[media_id] = {
                    'media_path': data[3],
                    'media_name': data[4]
                }
            downloads_status[media_id]["progress_bar"].setValue(percent)
            logger.debug(f"Updating progressbar for download item '{media_id}' to '{percent}'%")
    except KeyError:
        logger.error(f"Why TF we get here ?, Got progressbar update for media_id '{media_id}' "
                     f"which does not seem to exist !!! -> Valid Status items: "
                     f"{str([_media_id for _media_id in downloads_status])} "
                     )


def retry_all_failed_downloads():
    for dl_id in list(failed_downloads.keys()):
        if config.get("download_copy_btn"):
            downloads_status[media_id]['btn']['copy'].show()
        downloads_status[dl_id]["btn"]['cancel'].show()
        downloads_status[dl_id]["btn"]['retry'].hide()
        download_queue.put(failed_downloads[dl_id].copy())
        failed_downloads.pop(dl_id)


def cancel_all_downloads():
    for did in downloads_status.keys():
        logger.info(f'Trying to cancel : {did}')
        try:
            if downloads_status[did]['progress_bar'].value() < 95 and did not in cancel_list:
                cancel_list[did] = {}
        except (KeyError, RuntimeError):
            logger.info(f'Cannot cancel media id: {did}, this might have been cleared')


class MainWindow(QMainWindow):

    # Remove Later
    def contribute(self):
        if self.inp_language.currentIndex() == self.inp_language.count() - 1:
            url = "https://github.com/justin025/onthespot/blob/main/README.md#6-contributingsupporting"
            open_item(url)

    def __init__(self, _dialog, start_url=''):
        super(MainWindow, self).__init__()
        self.path = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(config.app_root, 'resources', 'icons', 'onthespot.png')
        QApplication.setStyle("fusion")
        uic.loadUi(os.path.join(self.path, "qtui", "main.ui"), self)
        self.setWindowIcon(QtGui.QIcon(icon_path))

        en_US_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'en_US.png'))
        self.inp_language.insertItem(0, en_US_icon, "English")
        #de_DE_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'de_DE.png'))
        #self.inp_language.insertItem(1, de_DE_icon, "Deutsch")
        #pt_PT_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'pt_PT.png'))
        #self.inp_language.insertItem(2, pt_PT_icon, "Português")

        # Contribute Translations
        pirate_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'pirate_flag.png'))
        self.inp_language.insertItem(999, pirate_icon, "Contribute")
        self.inp_language.currentIndexChanged.connect(self.contribute)

        save_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'save.png'))
        self.btn_save_config.setIcon(save_icon)
        folder_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'folder.png'))
        self.btn_download_root_browse.setIcon(folder_icon)
        self.btn_download_tmp_browse.setIcon(folder_icon)
        search_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'search.png'))
        self.btn_search.setIcon(search_icon)
        collapse_down_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'collapse_down.png'))
        self.btn_search_filter_toggle.setIcon(collapse_down_icon)

        # Breaks zeroconf login because of dirty restart
        self.start_url = start_url
        self.inp_version.setText(config.get("version"))
        self.inp_session_uuid.setText(config.session_uuid)
        logger.info(f"Initialising main window, logging session : {config.session_uuid}")
        self.group_search_items.hide()
        # Bind button click
        self.bind_button_inputs()

        # Create required variables to store configuration state about other threads/objects
        self.__playlist_maker = None
        self.__media_watcher_thread = None
        self.__media_watcher = None
        self.__qt_nam = QtNetwork.QNetworkAccessManager()
        # Variable to store data for class use
        self.__users = []
        self.__parsing_queue = queue.Queue()
        self.__last_search_data = None

        # Fill the value from configs
        logger.info("Loading configurations..")
        self.__fill_configs()

        # Hide the advanced tab on initial startup
        self.__advanced_visible = False
        self.tabview.setTabVisible(3, self.__advanced_visible)
        if not self.__advanced_visible:
            self.group_temp_dl_root.hide()

        self.__splash_dialog = _dialog

        # Start/create session builder and queue processor
        logger.info("Preparing session loader")
        self.__session_builder_thread = QThread()
        self.__session_builder_worker = LoadSessions()
        self.__session_builder_worker.setup(self.__users)
        self.__session_builder_worker.moveToThread(self.__session_builder_thread)
        self.__session_builder_thread.started.connect(self.__session_builder_worker.run)
        self.__session_builder_worker.finished.connect(self.__session_builder_thread.quit)
        self.__session_builder_worker.finished.connect(self.__session_builder_worker.deleteLater)
        self.__session_builder_worker.finished.connect(self.__session_load_done)
        self.__session_builder_thread.finished.connect(self.__session_builder_thread.deleteLater)
        self.__session_builder_worker.progress.connect(self.__show_popup_dialog)
        self.__session_builder_thread.start()
        logger.info("Preparing parsing queue processor")
        self.__media_parser_thread = QThread()
        self.__media_parser_worker = ParsingQueueProcessor()
        self.__media_parser_worker.setup(self.__parsing_queue)
        self.__media_parser_worker.moveToThread(self.__media_parser_thread)
        self.__media_parser_thread.started.connect(self.__media_parser_worker.run)
        self.__media_parser_worker.finished.connect(self.__media_parser_thread.quit)
        self.__media_parser_worker.finished.connect(self.__media_parser_worker.deleteLater)
        self.__media_parser_thread.finished.connect(self.__media_parser_thread.deleteLater)
        self.__media_parser_worker.progress.connect(self.__show_popup_dialog)
        self.__media_parser_worker.enqueue.connect(self.__add_item_to_downloads)
        self.__media_parser_thread.start()

        # Create path to dark_theme
        self.dark_theme_path = os.path.join(config.app_root,'resources', 'themes', 'main_window_dark_theme.qss')
        self.light_theme_path = os.path.join(config.app_root,'resources', 'themes', 'main_window_light_theme.qss')
        # Create button and add to the interface
        self.toggle_theme_button.clicked.connect(self.toggle_theme)
        # Set theme from config
        self.theme = config.get("theme")
        if self.theme == "Dark":
          theme_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'light.png'))
          self.toggle_theme_button.setIcon(theme_icon)
          self.toggle_theme_button.setText(self.tr(" Light Theme"))
          with open(self.dark_theme_path, 'r') as f:
              dark_theme = f.read()
              self.setStyleSheet(dark_theme)
        elif self.theme == "Light":
          theme_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'dark.png'))
          self.toggle_theme_button.setIcon(theme_icon)
          self.toggle_theme_button.setText(self.tr(" Dark Theme"))
          with open(self.light_theme_path, 'r') as f:
              light_theme = f.read()
              self.setStyleSheet(light_theme)
        logger.info(f"Set theme {self.theme}!")

        # Set the table header properties
        self.set_table_props()
        logger.info("Main window init completed !")

    def load_dark_theme(self):
        theme_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'light.png'))
        self.toggle_theme_button.setIcon(theme_icon)
        self.toggle_theme_button.setText(self.tr(" Light Theme"))
        with open(self.dark_theme_path, 'r') as f:
            dark_theme = f.read()
            self.setStyleSheet(dark_theme)
        self.theme = "Dark"

    def load_light_theme(self):
        theme_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'dark.png'))
        self.toggle_theme_button.setIcon(theme_icon)
        self.toggle_theme_button.setText(self.tr(" Dark Theme"))
        with open(self.light_theme_path, 'r') as f:
            light_theme = f.read()
            self.setStyleSheet(light_theme)
        self.theme = "Light"

    def toggle_theme(self):
        if self.theme == "Light":
            self.load_dark_theme()
        elif self.theme == "Dark":
            self.load_light_theme()

    def bind_button_inputs(self):
        # Connect button click signals
        collapse_down_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'collapse_down.png'))
        collapse_up_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'collapse_up.png'))

        self.btn_search.clicked.connect(self.__get_search_results)

        self.btn_login_add.clicked.connect(self.__add_account)
        self.btn_save_config.clicked.connect(self.__update_config)
        self.btn_reset_config.clicked.connect(self.reset_app_config)

        self.btn_search_download_all.clicked.connect(lambda x, cat="all": self.__mass_action_dl(cat))
        self.btn_save_adv_config.clicked.connect(self.__update_config)
        self.btn_toggle_advanced.clicked.connect(self.__toggle_advanced)
        self.inp_enable_lyrics.clicked.connect(self.__enable_lyrics)
        self.btn_progress_retry_all.clicked.connect(retry_all_failed_downloads)
        self.btn_progress_cancel_all.clicked.connect(cancel_all_downloads)
        self.btn_download_root_browse.clicked.connect(self.__select_dir)
        self.btn_download_tmp_browse.clicked.connect(self.__select_tmp_dir)
        self.inp_search_term.returnPressed.connect(self.__get_search_results)
        self.btn_search_download_tracks.clicked.connect(lambda x, cat="tracks": self.__mass_action_dl(cat))
        self.btn_search_download_albums.clicked.connect(lambda x, cat="albums": self.__mass_action_dl(cat))
        self.btn_search_download_artists.clicked.connect(lambda x, cat="artists": self.__mass_action_dl(cat))
        self.btn_progress_clear_complete.clicked.connect(self.rem_complete_from_table)
        self.btn_search_download_playlists.clicked.connect(lambda x, cat="playlists": self.__mass_action_dl(cat))
        self.btn_search_filter_toggle.clicked.connect(lambda toggle: self.group_search_items.show() if self.group_search_items.isHidden() else self.group_search_items.hide())
        self.btn_search_filter_toggle.clicked.connect(lambda switch: self.btn_search_filter_toggle.setIcon(collapse_down_icon) if self.group_search_items.isHidden() else self.btn_search_filter_toggle.setIcon(collapse_up_icon))
        # Connect checkbox state change signals
        self.inp_create_playlists.stateChanged.connect(self.__m3u_maker_set)
        self.inp_enable_spot_watch.stateChanged.connect(self.__media_watcher_set)

    def set_table_props(self):
        logger.info("Setting table item properties")
        # Sessions table
        tbl_sessions_header = self.tbl_sessions.horizontalHeader()
        tbl_sessions_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tbl_sessions_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        tbl_sessions_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tbl_sessions_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        # Search results table
        tbl_search_results_headers = self.tbl_search_results.horizontalHeader()
        tbl_search_results_headers.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        tbl_search_results_headers.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        tbl_search_results_headers.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        tbl_search_results_headers.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        # Download progress table
        tbl_dl_progress_header = self.tbl_dl_progress.horizontalHeader()
        tbl_dl_progress_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tbl_dl_progress_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tbl_dl_progress_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tbl_dl_progress_header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        return True

    def __m3u_maker_set(self):
        logger.info("Playlist generator watcher set clicked")
        maker_enabled = self.inp_create_playlists.isChecked()
        if maker_enabled and self.__playlist_maker is None:
            logger.info("Starting media watcher thread, no active watcher")
            self.__playlist_maker = PlayListMaker()
            self.__playlist_maker_thread = QThread(parent=self)
            self.__playlist_maker.moveToThread(self.__playlist_maker_thread)
            self.__playlist_maker_thread.started.connect(self.__playlist_maker.run)
            self.__playlist_maker.finished.connect(self.__playlist_maker_thread.quit)
            self.__playlist_maker.finished.connect(self.__playlist_maker.deleteLater)
            self.__playlist_maker.finished.connect(self.__playlist_maker_stopped)
            self.__playlist_maker_thread.finished.connect(self.__playlist_maker_thread.deleteLater)
            self.__playlist_maker_thread.start()
            logger.info("Playlist thread started")
        if maker_enabled is False and self.__playlist_maker is not None:
            logger.info("Active playlist maker, stopping it")
            self.__playlist_maker.stop()
            time.sleep(2)
            self.__playlist_maker = None
            self.__playlist_maker_thread = None

    def __media_watcher_set(self):
        logger.info("Media watcher set clicked")
        media_watcher_enabled = self.inp_enable_spot_watch.isChecked()
        if media_watcher_enabled and self.__media_watcher is None:
            logger.info("Starting media watcher thread, no active watcher")
            self.__media_watcher = MediaWatcher()
            self.__media_watcher_thread = QThread(parent=self)
            self.__media_watcher.moveToThread(self.__media_watcher_thread)
            self.__media_watcher_thread.started.connect(self.__media_watcher.run)
            self.__media_watcher.finished.connect(self.__media_watcher_thread.quit)
            self.__media_watcher.finished.connect(self.__media_watcher.deleteLater)
            self.__media_watcher.finished.connect(self.sig_media_track_end)
            self.__media_watcher.changed_media.connect(self.__download_by_url)
            self.__media_watcher_thread.finished.connect(self.__media_watcher_thread.deleteLater)
            self.__media_watcher_thread.start()
            logger.info("Media watcher thread started")
        if media_watcher_enabled is False and self.__media_watcher is not None:
            logger.info("Active watcher, stopping it")
            self.__media_watcher.stop()
            time.sleep(2)
            self.__media_watcher = None
            self.__media_watcher_thread = None

    def sig_media_track_end(self):
        logger.info("Watcher stopped")
        if self.inp_create_playlists.isChecked():
            self.inp_create_playlists.setChecked(False)

    def reset_app_config(self):
        config.rollback()
        self.__show_popup_dialog("The application setting was cleared successfully !\n Please restart the application.")

    def __playlist_maker_stopped(self):
        logger.info("Watcher stopped")
        if self.inp_enable_spot_watch.isChecked():
            self.inp_enable_spot_watch.setChecked(False)

    def __select_dir(self):
        dir_path = QFileDialog.getExistingDirectory(None, 'Select a folder:', os.path.expanduser("~"))
        if dir_path.strip() != '':
            self.inp_download_root.setText(QDir.toNativeSeparators(dir_path))

    def __select_tmp_dir(self):
        dir_path = QFileDialog.getExistingDirectory(None, 'Select a folder:', os.path.expanduser("~"))
        if dir_path.strip() != '':
            self.inp_tmp_dl_root.setText(QDir.toNativeSeparators(dir_path))

    def __toggle_advanced(self):
        self.__advanced_visible = False if self.__advanced_visible else True
        self.tabview.setTabVisible(3, self.__advanced_visible)
        if not self.__advanced_visible:
            self.group_temp_dl_root.hide()
        else:
            self.group_temp_dl_root.show()

    def __enable_lyrics(self):
        if self.inp_enable_lyrics.isChecked() == True and user[1].lower() == "free":
            self.__splash_dialog.run(self.tr("Warning: Downloading lyrics is a premium feature."))

    def __add_item_to_downloads(self, item):
        # Create progress status
        if item['item_id'] in downloads_status:
            # If the item is in download status dictionary, it's not cleared from view
            logger.info(f'The media: "{item["item_title"]}" ({item["item_id"]}) was already in view')
            if item['item_id'] in cancel_list:
                logger.info(f'The media: "{item["item_title"]}" ({item["item_id"]}) was being cancelled, preventing cancellation !')
                cancel_list.pop(item['item_id'])
            elif item['item_id'] in failed_downloads:
                dl_id = item['item_id']
                logger.info(f'The media: "{item["item_title"]}" ({item["item_id"]}) had failed to download, re-downloading ! !')
                downloads_status[dl_id]["status_label"].setText(self.tr("Waiting"))
                downloads_status[dl_id]["btn"]['cancel'].show()
                downloads_status[dl_id]["btn"]['retry'].hide()
                download_queue.put(failed_downloads[dl_id].copy())
                failed_downloads.pop(dl_id)
            else:
                logger.info(f'The media: "{item["item_title"]}" ({item["item_id"]}) is already in queue and is being downloaded, ignoring.. !')
            return None
        pbar = QProgressBar()
        pbar.setValue(0)
        pbar.setMinimumHeight(30)
        copy_btn = QPushButton()
        #copy_btn.setText('Retry')
        copy_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'link.png'))
        copy_btn.setIcon(copy_icon)
        copy_btn.setToolTip(self.tr('Copy'))
        copy_btn.setMinimumHeight(30)
        copy_btn.hide()
        cancel_btn = QPushButton()
        # cancel_btn.setText('Cancel')
        cancel_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'stop.png'))
        cancel_btn.setIcon(cancel_icon)
        cancel_btn.setToolTip(self.tr('Cancel'))
        cancel_btn.setMinimumHeight(30)
        retry_btn = QPushButton()
        #retry_btn.setText('Retry')
        retry_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'retry.png'))
        retry_btn.setIcon(retry_icon)
        retry_btn.setToolTip(self.tr('Retry'))
        retry_btn.setMinimumHeight(30)
        retry_btn.hide()
        play_btn = QPushButton()
        #play_btn.setText('Play')
        play_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'play.png'))
        play_btn.setIcon(play_icon)
        play_btn.setToolTip(self.tr('Play'))
        play_btn.setMinimumHeight(30)
        play_btn.hide()
        save_btn = QPushButton()
        #save_btn.setText('Save')
        #save_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'filled-heart.png'))
        #save_btn.setIcon(save_icon)
        save_btn.setToolTip(self.tr('Save'))
        save_btn.setMinimumHeight(30)
        save_btn.hide()
        queue_btn = QPushButton()
        #queue_btn.setText('Queue')
        queue_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'queue.png'))
        queue_btn.setIcon(queue_icon)
        queue_btn.setToolTip(self.tr('Queue'))
        queue_btn.setMinimumHeight(30)
        queue_btn.hide()
        open_btn = QPushButton()
        #open_btn.setText('Open')
        open_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'file.png'))
        open_btn.setIcon(open_icon)
        open_btn.setToolTip(self.tr('Open'))
        open_btn.setMinimumHeight(30)
        open_btn.hide()
        locate_btn = QPushButton()
        #locate_btn.setText('Locate')
        locate_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'folder.png'))
        locate_btn.setIcon(locate_icon)
        locate_btn.setToolTip(self.tr('Locate'))
        locate_btn.setMinimumHeight(30)
        locate_btn.hide()
        delete_btn = QPushButton()
        #delete_btn.setText('Delete')
        delete_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'delete.png'))
        delete_btn.setIcon(delete_icon)
        delete_btn.setToolTip(self.tr('Delete'))
        delete_btn.setMinimumHeight(30)
        delete_btn.hide()
        status = QLabel(self.tbl_dl_progress)
        status.setText(self.tr("Waiting"))
        actions = DownloadActionsButtons(item['item_id'], item['dl_params']['media_type'], pbar, copy_btn, cancel_btn, retry_btn, play_btn, save_btn, queue_btn, open_btn, locate_btn, delete_btn)
        download_queue.put(
            {
                'media_type': item['dl_params']['media_type'],
                'media_id': item['item_id'],
                'extra_paths': item['dl_params']['extra_paths'],
                'extra_path_as_root': item['dl_params']['extra_path_as_root'],
                'm3u_filename': '',
                'playlist_name': item['dl_params'].get('playlist_name', ''),
                'playlist_owner': item['dl_params'].get('playlist_owner', ''),
                'playlist_desc': item['dl_params'].get('playlist_desc', '')

            }
        )
        downloads_status[item['item_id']] = {
            "status_label": status,
            "progress_bar": pbar,
            "btn": {
                "copy": copy_btn,
                "cancel": cancel_btn,
                "retry": retry_btn,
                "play": play_btn,
                "save": save_btn,
                "queue": queue_btn,
                "open": open_btn,
                "locate": locate_btn,
                "delete": delete_btn
            }
        }
        logger.info(
            f"Adding item to download queue -> media_type:{item['dl_params']['media_type']}, "
            f"media_id: {item['item_id']}, extra_path:{item['dl_params']['extra_paths']}, "
            f"extra_path_as_root: {item['dl_params']['extra_path_as_root']}, Prefix value: ''")
        rows = self.tbl_dl_progress.rowCount()
        self.tbl_dl_progress.insertRow(rows)
        self.tbl_dl_progress.setItem(rows, 0, QTableWidgetItem(item['item_id']))
        self.tbl_dl_progress.setItem(rows, 1, QTableWidgetItem(item['item_title']))
        self.tbl_dl_progress.setItem(rows, 2, QTableWidgetItem(item['item_by_text']))
        self.tbl_dl_progress.setItem(rows, 3, QTableWidgetItem(item['item_type_text']))
        self.tbl_dl_progress.setCellWidget(rows, 4, status)
        self.tbl_dl_progress.setCellWidget(rows, 5, actions)

    def __show_popup_dialog(self, txt, btn_hide=False):
        self.__splash_dialog.lb_main.setText(str(txt))
        if btn_hide:
            self.__splash_dialog.btn_close.hide()
        else:
            self.__splash_dialog.btn_close.show()
        self.__splash_dialog.show()

    def __session_load_done(self):
        self.__splash_dialog.hide()
        self.__splash_dialog.btn_close.show()
        self.__generate_users_table(self.__users)
        self.show()
        if self.start_url.strip() != '':
            logger.info(f'Session was started with query of {self.start_url}')
            self.inp_search_term.setText(self.start_url.strip())
            self.__get_search_results()
        self.start_url = ''
        # Build threads
        self.__rebuild_threads()
        # Update Checker
        if config.get("check_for_updates"):
            if latest_release() == False:
                self.__splash_dialog.run(self.tr("<p>An update is available at the link below,<p><a style='color: #6495ed;' href='https://github.com/justin025/onthespot/releases/latest'>https://github.com/justin025/onthespot/releases/latest</a>"))

    def __user_table_remove_click(self, account_uuid):
        button = self.sender()
        index = self.tbl_sessions.indexAt(button.pos())
        # TODO: Wait for thread using the account, then remove thread as well as the account
        logger.debug(f"Clicked account remove button ! uuid: {account_uuid}")
        for account in config.get('accounts'):
            if account[3] == account_uuid:
                removed = remove_user(account[0],
                                      os.path.join(config_dir(), "onthespot", "sessions"),
                                      config, account_uuid, thread_pool, session_pool)
                if removed:
                    self.tbl_sessions.removeRow(index.row())
                    self.__users = [user for user in self.__users if user[3] != account_uuid]
                    self.__splash_dialog.run(self.tr("Account {0} was removed successfully.").format(account[0]))
                else:
                    self.__splash_dialog.run(self.tr("Something went wrong while removing account {0}.").format(account[0]))

    def __generate_users_table(self, userdata):

        # Clear the table
        while self.tbl_sessions.rowCount() > 0:
            self.tbl_sessions.removeRow(0)
        sn = 0
        for user in userdata:
            sn = sn + 1
            btn = QPushButton(self.tbl_sessions)
            btn.setText(self.tr(" Remove "))
            btn.clicked.connect(lambda x, account_uuid=user[3]: self.__user_table_remove_click(account_uuid))
            btn.setMinimumHeight(30)
            rows = self.tbl_sessions.rowCount()
            br = "N/A"
            if user[1].lower() == "free":
                br = "160K"
            elif user[1].lower() == "premium":
                br = "320K"
            self.tbl_sessions.insertRow(rows)
            self.tbl_sessions.setItem(rows, 0, QTableWidgetItem(user[0]))
            self.tbl_sessions.setItem(rows, 1, QTableWidgetItem(user[1]))
            self.tbl_sessions.setItem(rows, 2, QTableWidgetItem(br))
            self.tbl_sessions.setItem(rows, 3, QTableWidgetItem(user[2]))
            self.tbl_sessions.setCellWidget(rows, 4, btn)
        logger.info("Accounts table was populated !")

    def __rebuild_threads(self):
        # Check how many threads can we build till we reach max thread
        logger.debug(f'Thread builder -> TPool count : {len(thread_pool)}, SPool count : {len(session_pool)}, MaxT : {config.get("max_threads")}')
        for session_uuid in session_pool.keys():
            if ( len(thread_pool) < config.get('max_threads') ) and session_uuid not in thread_pool.keys():
                # We have space for new thread and the session is not used by any thread
                thread_pool[session_uuid] = [DownloadWorker(), QThread()]
                logger.info(f"Spawning DL thread using session : {session_uuid} ")
                thread_pool[session_uuid][0].setup(
                    thread_name=f"SESSION_DL_TH-{session_uuid}",
                    session_uuid=session_uuid,
                    queue_tracks=download_queue)
                thread_pool[session_uuid][0].moveToThread(thread_pool[session_uuid][1])
                thread_pool[session_uuid][1].started.connect(thread_pool[session_uuid][0].run)
                thread_pool[session_uuid][0].finished.connect(thread_pool[session_uuid][1].quit)
                thread_pool[session_uuid][0].finished.connect(thread_pool[session_uuid][0].deleteLater)
                thread_pool[session_uuid][1].finished.connect(thread_pool[session_uuid][1].deleteLater)
                thread_pool[session_uuid][0].progress.connect(dl_progress_update)
                thread_pool[session_uuid][0].finished.connect(thread_pool[session_uuid][1].quit)
                thread_pool[session_uuid][1].start()
            else:
                logger.debug(f'Session {session_uuid} not used, resource busy !')
        if len(session_pool) == 0:
            # Display notice that no session is available and threads are not built
            self.__splash_dialog.run(self.tr("No session available, login with at least one account."))

    def __fill_configs(self):
        self.inp_language.setCurrentIndex(config.get("language_index"))
        self.inp_max_threads.setValue(config.get("max_threads"))
        self.inp_parsing_acc_sn.setValue(config.get("parsing_acc_sn"))
        self.inp_download_root.setText(config.get("download_root"))
        self.inp_download_delay.setValue(config.get("download_delay"))
        self.inp_max_search_results.setValue(config.get("max_search_results"))
        self.inp_max_retries.setValue(config.get("max_retries"))
        self.inp_chunk_size.setValue(config.get("chunk_size"))
        self.inp_media_format.setText(config.get("media_format"))
        self.inp_podcast_media_format.setText(config.get("podcast_media_format"))
        self.inp_track_formatter.setText(config.get("track_path_formatter"))
        self.inp_podcast_path_formatter.setText(config.get("podcast_path_formatter"))
        self.inp_playlist_path_formatter.setText(config.get("playlist_path_formatter"))
        self.inp_m3u_name_formatter.setText(config.get("m3u_name_formatter"))
        self.inp_max_recdl_delay.setValue(config.get("recoverable_fail_wait_delay"))
        self.inp_dl_endskip.setValue(config.get("dl_end_padding_bytes"))
        self.inp_search_thumb_height.setValue(config.get("search_thumb_height"))
        self.inp_metadata_seperator.setText(config.get("metadata_seperator"))
        if config.get("show_search_thumbnails"):
            self.inp_show_search_thumbnails.setChecked(True)
        else:
            self.inp_show_search_thumbnails.setChecked(False)
        if config.get("use_lrc_file"):
            self.inp_use_lrc_file.setChecked(True)
        else:
            self.inp_use_lrc_file.setChecked(False)
        if config.get("rotate_acc_sn"):
            self.inp_rotate_acc_sn.setChecked(True)
        else:
            self.inp_rotate_acc_sn.setChecked(False)
        if config.get("download_copy_btn"):
            self.inp_download_copy_btn.setChecked(True)
        else:
            self.inp_download_copy_btn.setChecked(False)
        if config.get("download_play_btn"):
            self.inp_download_play_btn.setChecked(True)
        else:
            self.inp_download_play_btn.setChecked(False)
        if config.get("download_save_btn"):
            self.inp_download_save_btn.setChecked(True)
        else:
            self.inp_download_save_btn.setChecked(False)
        if config.get("download_queue_btn"):
            self.inp_download_queue_btn.setChecked(True)
        else:
            self.inp_download_queue_btn.setChecked(False)
        if config.get("download_open_btn"):
            self.inp_download_open_btn.setChecked(True)
        else:
            self.inp_download_open_btn.setChecked(False)
        if config.get("download_locate_btn"):
            self.inp_download_locate_btn.setChecked(True)
        else:
            self.inp_download_locate_btn.setChecked(False)
        if config.get("download_delete_btn"):
            self.inp_download_delete_btn.setChecked(True)
        else:
            self.inp_download_delete_btn.setChecked(False)
        if config.get("translate_file_path"):
            self.inp_translate_file_path.setChecked(True)
        else:
            self.inp_translate_file_path.setChecked(False)
        if config.get("force_raw"):
            self.inp_raw_download.setChecked(True)
        else:
            self.inp_raw_download.setChecked(False)
        if config.get("watch_bg_for_spotify"):
            self.inp_enable_spot_watch.setChecked(True)
        else:
            self.inp_enable_spot_watch.setChecked(False)
        if config.get("force_premium"):
            self.inp_force_premium.setChecked(True)
        else:
            self.inp_force_premium.setChecked(False)
        if config.get("disable_bulk_dl_notices"):
            self.inp_disable_bulk_popup.setChecked(True)
        else:
            self.inp_disable_bulk_popup.setChecked(False)
        if config.get("inp_enable_lyrics"):
            self.inp_enable_lyrics.setChecked(True)
        else:
            self.inp_enable_lyrics.setChecked(False)
        if config.get("only_synced_lyrics"):
            self.inp_only_synced_lyrics.setChecked(True)
        else:
            self.inp_only_synced_lyrics.setChecked(False)
        if config.get('use_playlist_path'):
            self.inp_use_playlist_path.setChecked(True)
        else:
            self.inp_use_playlist_path.setChecked(False)
        if config.get('create_m3u_playlists'):
            self.inp_create_playlists.setChecked(True)
        else:
            self.inp_create_playlists.setChecked(False)
        if config.get('check_for_updates'):
            self.inp_check_for_updates.setChecked(True)
        else:
            self.inp_check_for_updates.setChecked(False)
        if config.get('embed_branding'):
            self.inp_embed_branding.setChecked(True)
        else:
            self.inp_embed_branding.setChecked(False)
        if config.get('embed_artist'):
            self.inp_embed_artist.setChecked(True)
        else:
            self.inp_embed_artist.setChecked(False)
        if config.get('embed_album'):
            self.inp_embed_album.setChecked(True)
        else:
            self.inp_embed_album.setChecked(False)
        if config.get('embed_albumartist'):
            self.inp_embed_albumartist.setChecked(True)
        else:
            self.inp_embed_albumartist.setChecked(False)
        if config.get('embed_name'):
            self.inp_embed_name.setChecked(True)
        else:
            self.inp_embed_name.setChecked(False)
        if config.get('embed_year'):
            self.inp_embed_year.setChecked(True)
        else:
            self.inp_embed_year.setChecked(False)
        if config.get('embed_discnumber'):
            self.inp_embed_discnumber.setChecked(True)
        else:
            self.inp_embed_discnumber.setChecked(False)
        if config.get('embed_tracknumber'):
            self.inp_embed_tracknumber.setChecked(True)
        else:
            self.inp_embed_tracknumber.setChecked(False)
        if config.get('embed_genre'):
            self.inp_embed_genre.setChecked(True)
        else:
            self.inp_embed_genre.setChecked(False)
        if config.get('embed_performers'):
            self.inp_embed_performers.setChecked(True)
        else:
            self.inp_embed_performers.setChecked(False)
        if config.get('embed_producers'):
            self.inp_embed_producers.setChecked(True)
        else:
            self.inp_embed_producers.setChecked(False)
        if config.get('embed_writers'):
            self.inp_embed_writers.setChecked(True)
        else:
            self.inp_embed_writers.setChecked(False)
        if config.get('embed_label'):
            self.inp_embed_label.setChecked(True)
        else:
            self.inp_embed_label.setChecked(False)
        if config.get('embed_copyright'):
            self.inp_embed_copyright.setChecked(True)
        else:
            self.inp_embed_copyright.setChecked(False)
        if config.get('embed_description'):
            self.inp_embed_description.setChecked(True)
        else:
            self.inp_embed_description.setChecked(False)
        if config.get('embed_language'):
            self.inp_embed_language.setChecked(True)
        else:
            self.inp_embed_language.setChecked(False)
        if config.get('embed_isrc'):
            self.inp_embed_isrc.setChecked(True)
        else:
            self.inp_embed_isrc.setChecked(False)
        if config.get('embed_length'):
            self.inp_embed_length.setChecked(True)
        else:
            self.inp_embed_length.setChecked(False)
        if config.get('embed_lyrics'):
            self.inp_embed_lyrics.setChecked(True)
        else:
            self.inp_embed_lyrics.setChecked(False)
        if config.get('embed_url'):
            self.inp_embed_url.setChecked(True)
        else:
            self.inp_embed_url.setChecked(False)

        logger.info('Config filled to UI')

    def __update_config(self):
        if config.get('language_index') != self.inp_language.currentIndex():
            self.__splash_dialog.run(self.tr("Language changed. \n Application needs to be restarted for changes to take effect."))
        config.set_('language_index', self.inp_language.currentIndex())
        if config.get('max_threads') != self.inp_max_threads.value():
            self.__splash_dialog.run(self.tr("Thread config was changed. \n Application needs to be restarted for changes to take effect."))
        config.set_('max_threads', self.inp_max_threads.value())
        if self.inp_parsing_acc_sn.value() > len(session_pool):
            config.set_('parsing_acc_sn', 1)
            self.inp_parsing_acc_sn.setValue(1)
        else:
            config.set_('parsing_acc_sn', self.inp_parsing_acc_sn.value())
        config.set_('download_root', self.inp_download_root.text())
        config.set_('track_path_formatter', self.inp_track_formatter.text())
        config.set_('podcast_path_formatter', self.inp_podcast_path_formatter.text())
        config.set_('playlist_path_formatter', self.inp_playlist_path_formatter.text())
        config.set_('m3u_name_formatter', self.inp_m3u_name_formatter.text())
        config.set_('download_delay', self.inp_download_delay.value())
        config.set_('chunk_size', self.inp_chunk_size.value())
        config.set_('recoverable_fail_wait_delay', self.inp_max_recdl_delay.value())
        config.set_('dl_end_padding_bytes', self.inp_dl_endskip.value())
        config.set_('search_thumb_height', self.inp_search_thumb_height.value())
        config.set_('max_retries', self.inp_max_retries.value())
        config.set_('disable_bulk_dl_notices', self.inp_disable_bulk_popup.isChecked())
        config.set_('theme', self.theme)
        config.set_('metadata_seperator', self.inp_metadata_seperator.text())
        if 0 < self.inp_max_search_results.value() <= 50:
            config.set_('max_search_results', self.inp_max_search_results.value())
        else:
            config.set_('max_search_results', 5)
        config.set_('media_format', self.inp_media_format.text())
        config.set_('podcast_media_format', self.inp_podcast_media_format.text())
        if self.inp_show_search_thumbnails.isChecked():
            config.set_('show_search_thumbnails', True)
        else:
            config.set_('show_search_thumbnails', False)
        if self.inp_use_lrc_file.isChecked():
            config.set_('use_lrc_file', True)
        else:
            config.set_('use_lrc_file', False)
        if self.inp_rotate_acc_sn.isChecked():
            config.set_('rotate_acc_sn', True)
        else:
            config.set_('rotate_acc_sn', False)
        if self.inp_translate_file_path.isChecked():
            config.set_('translate_file_path', True)
        else:
            config.set_('translate_file_path', False)
        if self.inp_raw_download.isChecked():
            config.set_('force_raw', True)
        else:
            config.set_('force_raw', False)
        if self.inp_download_copy_btn.isChecked():
            config.set_('download_copy_btn', True)
        else:
            config.set_('download_copy_btn', False)
        if self.inp_download_play_btn.isChecked():
            config.set_('download_play_btn', True)
        else:
            config.set_('download_play_btn', False)
        if self.inp_download_save_btn.isChecked():
            config.set_('download_save_btn', True)
        else:
            config.set_('download_save_btn', False)
        if self.inp_download_queue_btn.isChecked():
            config.set_('download_queue_btn', True)
        else:
            config.set_('download_queue_btn', False)
        if self.inp_download_open_btn.isChecked():
            config.set_('download_open_btn', True)
        else:
            config.set_('download_open_btn', False)
        if self.inp_download_locate_btn.isChecked():
            config.set_('download_locate_btn', True)
        else:
            config.set_('download_locate_btn', False)
        if self.inp_download_delete_btn.isChecked():
            config.set_('download_delete_btn', True)
        else:
            config.set_('download_delete_btn', False)
        if self.inp_force_premium.isChecked():
            config.set_('force_premium', True)
        else:
            config.set_('force_premium', False)
        if self.inp_enable_spot_watch.isChecked():
            config.set_('watch_bg_for_spotify', True)
        else:
            config.set_('watch_bg_for_spotify', False)
        if self.inp_enable_lyrics.isChecked():
            config.set_('inp_enable_lyrics', True)
        else:
            config.set_('inp_enable_lyrics', False)
        if self.inp_only_synced_lyrics.isChecked():
            config.set_('only_synced_lyrics', True)
        else:
            config.set_('only_synced_lyrics', False)
        if self.inp_use_playlist_path.isChecked():
            config.set_('use_playlist_path', True)
        else:
            config.set_('use_playlist_path', False)
        if self.inp_create_playlists.isChecked():
            config.set_('create_m3u_playlists', True)
        else:
            config.set_('create_m3u_playlists', False)
        if self.inp_check_for_updates.isChecked():
            config.set_('check_for_updates', True)
        else:
            config.set_('check_for_updates', False)
        if self.inp_embed_branding.isChecked():
            config.set_('embed_branding', True)
        else:
            config.set_('embed_branding', False)
        if self.inp_embed_artist.isChecked():
            config.set_('embed_artist', True)
        else:
            config.set_('embed_artist', False)
        if self.inp_embed_album.isChecked():
            config.set_('embed_album', True)
        else:
            config.set_('embed_album', False)
        if self.inp_embed_albumartist.isChecked():
            config.set_('embed_albumartist', True)
        else:
            config.set_('embed_albumartist', False)
        if self.inp_embed_name.isChecked():
            config.set_('embed_name', True)
        else:
            config.set_('embed_name', False)
        if self.inp_embed_year.isChecked():
            config.set_('embed_year', True)
        else:
            config.set_('embed_year', False)
        if self.inp_embed_discnumber.isChecked():
            config.set_('embed_discnumber', True)
        else:
            config.set_('embed_discnumber', False)
        if self.inp_embed_tracknumber.isChecked():
            config.set_('embed_tracknumber', True)
        else:
            config.set_('embed_tracknumber', False)
        if self.inp_embed_genre.isChecked():
            config.set_('embed_genre', True)
        else:
            config.set_('embed_genre', False)
        if self.inp_embed_performers.isChecked():
            config.set_('embed_performers', True)
        else:
            config.set_('embed_performers', False)
        if self.inp_embed_producers.isChecked():
            config.set_('embed_producers', True)
        else:
            config.set_('embed_producers', False)
        if self.inp_embed_writers.isChecked():
            config.set_('embed_writers', True)
        else:
            config.set_('embed_writers', False)
        if self.inp_embed_label.isChecked():
            config.set_('embed_label', True)
        else:
            config.set_('embed_label', False)
        if self.inp_embed_copyright.isChecked():
            config.set_('embed_copyright', True)
        else:
            config.set_('embed_copyright', False)
        if self.inp_embed_description.isChecked():
            config.set_('embed_description', True)
        else:
            config.set_('embed_description', False)
        if self.inp_embed_language.isChecked():
            config.set_('embed_language', True)
        else:
            config.set_('embed_language', False)
        if self.inp_embed_isrc.isChecked():
            config.set_('embed_isrc', True)
        else:
            config.set_('embed_isrc', False)
        if self.inp_embed_length.isChecked():
            config.set_('embed_length', True)
        else:
            config.set_('embed_length', False)
        if self.inp_embed_lyrics.isChecked():
            config.set_('embed_lyrics', True)
        else:
            config.set_('embed_lyrics', False)
        if self.inp_embed_url.isChecked():
            config.set_('embed_url', True)
        else:
            config.set_('embed_url', False)
        config.update()
        logger.info('Config updated !')

    def __add_account(self):
        logger.info('Add account clicked ')
        self.btn_login_add.setText(self.tr("Waiting..."))
        self.btn_login_add.setDisabled(True)
        login = threading.Thread(target=new_session)
        login.daemon = True
        login.start()
        self.__splash_dialog.run(self.tr("Login Service Started...\nSelect 'OnTheSpot' under devices in the Spotify Desktop App."))

    def __get_search_results(self):
        search_term = self.inp_search_term.text().strip()
        results = None
        if len(session_pool) <= 0:
            self.__splash_dialog.run(self.tr("You need to login to at least one account to use this feature."))
            return None
        if search_term.startswith('https://'):
            logger.info(f"Search clicked with value with url {search_term}")
            self.__download_by_url(search_term)
            self.inp_search_term.setText('')
            return True
        else:
            if os.path.isfile(search_term):
                with open(search_term, 'r', encoding='utf-8') as sf:
                    links = sf.readlines()
                    for link in links:
                        logger.info(f'Reading link "{link}" from file at "{search_term}"')
                        self.__download_by_url(link, hide_dialog=True)
                self.inp_search_term.setText('')
                return True
        logger.info(f"Search clicked with value term {search_term}")
        try:
            filters = []
            if self.inp_enable_search_playlists.isChecked():
                filters.append('playlist')
            if self.inp_enable_search_albums.isChecked():
                filters.append('album')
            if self.inp_enable_search_tracks.isChecked():
                filters.append('track')
            if self.inp_enable_search_artists.isChecked():
                filters.append('artist')
            download = False
            selected_uuid = fetch_account_uuid(download)
            session = session_pool[ selected_uuid ]
            try:
                results = search_by_term(session, search_term,
                                     config.get('max_search_results'), content_types=filters)
            except (OSError, queue.Empty, MaxRetryError, NewConnectionError, ConnectionError):
                # Internet disconnected ?
                logger.error('Search failed Connection error ! Trying to re init parsing account session ! ')
                re_init_session(session_pool, selected_uuid, wait_connectivity=False)
                return None
            self.__populate_search_results(results)
            self.__last_search_data = results
            self.inp_search_term.setText('')
        except EmptySearchResultException:
            self.__last_search_data = []
            while self.tbl_search_results.rowCount() > 0:
                self.tbl_search_results.removeRow(0)
            self.__splash_dialog.run(self.tr("No results found."))
            return None

    def __download_by_url(self, url=None, hide_dialog=False):
        logger.info(f"URL download clicked with value {url}")
        media_type, media_id = get_url_data(url)
        if media_type is None:
            logger.error(f"The type of url could not be determined ! URL: {url}")
            if not hide_dialog:
                self.__splash_dialog.run(self.tr("Unable to parse inputted URL."))
            return False
        if len(session_pool) <= 0:
            logger.error('User needs to be logged in to download from url')
            if not hide_dialog:
                self.__splash_dialog.run(self.tr("You need to login to at least one account to use this feature."))
            return False
        queue_item = {
            "media_type": media_type,
            "media_id": media_id,
            "data": {
                "hide_dialogs": hide_dialog,
            }
        }

        self.__send_to_pqp(queue_item)
        logger.info(f'URL "{url}" added to parsing queue')
        if not hide_dialog:
            self.__splash_dialog.run(self.tr("The {0} is being parsed and will be added to download queue shortly.").format(media_type.title()))
        return True

    def __insert_search_result_row(self, btn_text, item_name, item_by, item_type, queue_data):
        btn = QPushButton(self.tbl_search_results)
        #btn.setText(btn_text.strip())
        download_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'download.png'))
        btn.setIcon(download_icon)

        btn.clicked.connect(lambda x, q_data=queue_data: self.__send_to_pqp(q_data))
        btn.setMinimumHeight(30)


        rows = self.tbl_search_results.rowCount()
        tbl_search_results_headers = self.tbl_search_results.horizontalHeader()
        self.tbl_search_results.insertRow(rows)
        self.tbl_search_results.setRowHeight(rows, 60)
        self.tbl_search_results.setCellWidget(rows, 0, LabelWithThumb(queue_data['data']['thumb_url'],
                                                                      item_name.strip(),
                                                                      self.__qt_nam,
                                                                      thumb_enabled=config.get('show_search_thumbnails'),
                                                                      parent=self))
        c1item = QTableWidgetItem(item_by.strip())
        c1item.setToolTip(item_by.strip())
        self.tbl_search_results.setItem(rows, 1, c1item)
        c2item = QTableWidgetItem(item_type.strip())
        c2item.setToolTip(item_type.strip())
        self.tbl_search_results.setItem(rows, 2, c2item)
        btn.setToolTip(f"Download {item_type.strip()} '{item_name.strip()}' by '{item_by.strip()}'. ")
        self.tbl_search_results.setCellWidget(rows, 3, btn)
        tbl_search_results_headers.resizeSection(0, 450)
        return True

    def __populate_search_results(self, data):
        # Clear the table
        self.__last_search_data = data
        logger.debug('Populating search results table ')
        while self.tbl_search_results.rowCount() > 0:
            self.tbl_search_results.removeRow(0)
        for d_key in data.keys():  # d_key in ['Albums', 'Artists', 'Tracks', 'Playlists']
            for item in data[d_key]:  # Item is Data for Albums, Artists, etc.
                # Set item name
                item_name, item_by = name_by_from_sdata(d_key, item)
                if item_name is None and item_by is None:
                    continue
                if d_key.lower() == "tracks":
                    thumb_dict = item['album']['images']
                # Playlists fail because height and width in the response are set to null
                elif d_key.lower() == "playlists":
                    url = item['images'][int('0')]['url']
                    thumb_dict = [{'height': 64, 'url': url,'width': 64}]
                else:
                    thumb_dict = item['images']
                queue_data = {'media_type': d_key[0:-1], 'media_id': item['id'],
                              'data': {
                                  'media_title': item_name.replace("[ E ]", ""),
                                  'thumb_url': get_thumbnail(thumb_dict,
                                                             preferred_size=config.get('search_thumb_height')^2
                                                             )
                              }}
                tmp_dl_val = self.inp_tmp_dl_root.text().strip()
                if self.__advanced_visible and tmp_dl_val != "" and os.path.isdir(tmp_dl_val):
                    queue_data['data']['dl_path'] = tmp_dl_val
                btn_text = f"Download {d_key[0:-1]}".replace('artist', 'discography').title()
                self.__insert_search_result_row(btn_text=btn_text, item_name=item_name, item_by=item_by,
                                                item_type=d_key[0:-1].title(), queue_data=queue_data)

    def __mass_action_dl(self, result_type):
        data = self.__last_search_data
        downloaded_types = []
        logger.info(f"Mass download for {result_type} was clicked.. Here hangs up the application")
        if data is None:
            self.__splash_dialog.run(self.tr("No search results to download."))
        else:
            hide_dialog = config.get('disable_bulk_dl_notices')
            for d_key in data.keys():  # d_key in ['Albums', 'Artists', 'Tracks', 'Playlists']
                if d_key == result_type or result_type == "all":
                    for item in data[d_key]:  # Item is Data for Albums, Artists, etc.
                        item_name, item_by = name_by_from_sdata(d_key, item)
                        if item_name is None and item_by is None:
                            continue
                        queue_data = {'media_type': d_key[0:-1], 'media_id': item['id'],
                                      'data': {
                                          'media_title': item_name.replace('[ E ]', ''),
                                          "hide_dialogs": hide_dialog
                                      }}
                        self.__send_to_pqp(queue_data)
                    downloaded_types.append(d_key)
            if len(downloaded_types) != 0:
                self.__splash_dialog.run(self.tr("Added all results to download queue."))

    def rem_complete_from_table(self):
        check_row = 0
        while check_row < self.tbl_dl_progress.rowCount():
            did = self.tbl_dl_progress.item(check_row, 0).text()
            logger.info(f'Removing Row : {check_row} and mediaid: {did}')
            if did in downloads_status:
                progress = downloads_status[did]["progress_bar"].value()
                status = downloads_status[did]["status_label"].text().lower()
                if progress == 100 or status == self.tr("cancelled"):
                    self.tbl_dl_progress.removeRow(check_row)
                    downloads_status.pop(did)
                else:
                    check_row = check_row + 1
            else:
                check_row = check_row + 1

    def __send_to_pqp(self, queue_item):
        tmp_dl_val = self.inp_tmp_dl_root.text().strip()
        if self.__advanced_visible and tmp_dl_val != "":
            logger.info('Advanced tab visible and temporary download path set !')
            try:
                if not os.path.exists(os.path.abspath(tmp_dl_val)):
                    os.makedirs(os.path.abspath(tmp_dl_val), exist_ok=True)
                queue_item['data']['dl_path'] = tmp_dl_val
                queue_item['data']['dl_path_is_root'] = True
            except:
                logger.error('Temp dl path cannot be created !')
        logger.info('Prepared media for parsing, adding to PQP queue !')
        self.__parsing_queue.put(queue_item)
