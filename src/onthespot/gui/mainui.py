import os
import time
import threading
from urllib3.exceptions import MaxRetryError, NewConnectionError
from PyQt6 import uic, QtGui
from PyQt6.QtCore import QThread, QDir, Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QHeaderView, QLabel, QPushButton, QProgressBar, QTableWidgetItem, QFileDialog, QRadioButton
from ..utils import is_latest_release, open_item
from .dl_progressbtn import DownloadActionsButtons
from .settings import load_config, save_config
from ..otsconfig import config
from ..runtimedata import get_logger, parsing, pending, download_queue, account_pool, download_queue_lock
from .thumb_listitem import LabelWithThumb
from ..api.spotify import spotify_get_token, spotify_get_track_metadata, spotify_get_episode_metadata, spotify_new_session
from ..api.soundcloud import soundcloud_get_token, soundcloud_get_track_metadata
from ..accounts import get_account_token, FillAccountPool
from ..search import get_search_results
from ..downloader import DownloadWorker

logger = get_logger('gui.main_ui')


class QueueWorker(QThread):
    add_item_to_download_list = pyqtSignal(dict, dict)
    def __init__(self):
        super().__init__()


    def run(self):
        while True:
            if pending:
                item_id = next(iter(pending))  # Get the first key  
                item = pending.pop(item_id)
                token = get_account_token()
                item_metadata = globals()[f"{item['item_service']}_get_{item['item_type']}_metadata"](token, item['item_id'])
                self.add_item_to_download_list.emit(item, item_metadata)
                continue
            else:
                time.sleep(4)

class MainWindow(QMainWindow):

    def fill_account_table(self):

        # Clear the table
        while self.tbl_sessions.rowCount() > 0:
            self.tbl_sessions.removeRow(0)
        sn = 0
        for account in account_pool:
            sn = sn + 1
            rows = self.tbl_sessions.rowCount()

            radiobutton = QRadioButton()
            radiobutton.clicked.connect(lambda: config.set_('parsing_acc_sn', self.tbl_sessions.currentRow()) and config.update())
            if sn == config.get("parsing_acc_sn") + 1:
                radiobutton.setChecked(True)

            btn = QPushButton(self.tbl_sessions)
            trash_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'trash.png'))
            btn.setIcon(trash_icon)
            #btn.setText(self.tr(" Remove "))
            
            btn.clicked.connect(lambda x, index=rows: self.user_table_remove_click(index))
            btn.setMinimumHeight(30)

            service = QTableWidgetItem(str(account["service"]).title())
            service.setIcon(QIcon(os.path.join(config.app_root, 'resources', 'icons', f'{account["service"]}.png')))

            self.tbl_sessions.insertRow(rows)
            self.tbl_sessions.setCellWidget(rows, 0, radiobutton)
            self.tbl_sessions.setItem(rows, 1, QTableWidgetItem(account["username"]))
            self.tbl_sessions.setItem(rows, 2, QTableWidgetItem(service))
            self.tbl_sessions.setItem(rows, 3, QTableWidgetItem(str(account["account_type"]).title()))
            self.tbl_sessions.setItem(rows, 4, QTableWidgetItem(account["bitrate"]))
            self.tbl_sessions.setItem(rows, 5, QTableWidgetItem(str(account["status"]).title()))
            self.tbl_sessions.setCellWidget(rows, 6, btn)
        logger.info("Accounts table was populated !")

    def add_item_to_download_list(self, item, item_metadata):
        with download_queue_lock:
            # Skip rendering QButtons if they are not in use
            copy_btn = None
            play_btn = None
            save_btn = None
            queue_btn = None
            open_btn = None
            locate_btn = None
            delete_btn = None

            # Items
            pbar = QProgressBar()
            pbar.setValue(0)
            pbar.setMinimumHeight(30)
            if config.get("download_copy_btn"):
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
            if config.get("download_play_btn"):
                play_btn = QPushButton()
                #play_btn.setText('Play')
                play_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'play.png'))
                play_btn.setIcon(play_icon)
                play_btn.setToolTip(self.tr('Play'))
                play_btn.setMinimumHeight(30)
                play_btn.hide()
            if config.get("download_save_btn"):
                save_btn = QPushButton()
                #save_btn.setText('Save')
                #save_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'filled_heart.png'))
                #save_btn.setIcon(save_icon)
                save_btn.setToolTip(self.tr('Save'))
                save_btn.setMinimumHeight(30)
                save_btn.hide()
            if config.get("download_queue_btn"):
                queue_btn = QPushButton()
                #queue_btn.setText('Queue')
                queue_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'queue.png'))
                queue_btn.setIcon(queue_icon)
                queue_btn.setToolTip(self.tr('Queue'))
                queue_btn.setMinimumHeight(30)
                queue_btn.hide()
            if config.get("download_open_btn"):
                open_btn = QPushButton()
                #open_btn.setText('Open')
                open_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'file.png'))
                open_btn.setIcon(open_icon)
                open_btn.setToolTip(self.tr('Open'))
                open_btn.setMinimumHeight(30)
                open_btn.hide()
            if config.get("download_locate_btn"):
                locate_btn = QPushButton()
                #locate_btn.setText('Locate')
                locate_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'folder.png'))
                locate_btn.setIcon(locate_icon)
                locate_btn.setToolTip(self.tr('Locate'))
                locate_btn.setMinimumHeight(30)
                locate_btn.hide()
            if config.get("download_delete_btn"):
                delete_btn = QPushButton()
                #delete_btn.setText('Delete')
                delete_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'delete.png'))
                delete_btn.setIcon(delete_icon)
                delete_btn.setToolTip(self.tr('Delete'))
                delete_btn.setMinimumHeight(30)
                delete_btn.hide()
            
            item_service = item["item_service"]
            service_label = QTableWidgetItem(str(item_service).title())
            service_label.setIcon(QIcon(os.path.join(config.app_root, 'resources', 'icons', f'{item_service}.png')))

            status_label = QLabel(self.tbl_dl_progress)
            status_label.setText(self.tr("Waiting"))
            actions = DownloadActionsButtons(item['item_id'], pbar, copy_btn, cancel_btn, retry_btn, open_btn, locate_btn, delete_btn)

            rows = self.tbl_dl_progress.rowCount()
            self.tbl_dl_progress.insertRow(rows)
            if config.get('show_download_thumbnails'):
                self.tbl_dl_progress.setRowHeight(rows, config.get("search_thumb_height"))
                item_label = LabelWithThumb(item_metadata['title'], item_metadata['image_url'])
            else:
                item_label = QLabel(self.tbl_dl_progress)
                item_label.setText(item_metadata['title'])
            # Add To List
            self.tbl_dl_progress.setItem(rows, 0, QTableWidgetItem(str(item['item_id'])))
            self.tbl_dl_progress.setCellWidget(rows, 1, item_label)
            self.tbl_dl_progress.setItem(rows, 2, QTableWidgetItem(item_metadata['artists']))
            self.tbl_dl_progress.setItem(rows, 3, QTableWidgetItem(service_label))
            self.tbl_dl_progress.setCellWidget(rows, 4, status_label)
            self.tbl_dl_progress.setCellWidget(rows, 5, actions)

            if item['is_playlist_item'] is True:
                playlist_name = item['playlist_name']
                playlist_by = item['playlist_by']
            else:
                playlist_name = ''
                playlist_by = ''

            download_queue[item['item_id']] = {
                "item_service": item["item_service"],
                "item_type": item["item_type"],
                'item_id': item['item_id'],
                'item_status': 'Waiting',
                "file_path": None,
                'is_playlist_item': item['is_playlist_item'],
                'playlist_name': playlist_name,
                'playlist_by': playlist_by,
                "gui": {
                    "status_label": status_label,
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
                }


    def update_item_in_download_list(self, item, status, progress):
        with download_queue_lock:
            item['gui']['status_label'].setText(status)
            item['gui']['progress_bar'].setValue(progress)
            if progress == 0:
                item['gui']["btn"]['cancel'].hide()
                if config.get("download_copy_btn"):
                    item['gui']['btn']['copy'].show()
                item['gui']["btn"]['retry'].show()
                return
            elif progress == 100:
                item['gui']['btn']['cancel'].hide()
                item['gui']['btn']['retry'].hide()
                if config.get("download_copy_btn"):
                    item['gui']['btn']['copy'].show()
                if config.get("download_play_btn"):
                    item['gui']['btn']['play'].show()
                if config.get("download_save_btn"):
                    item['gui']['btn']['save'].show()
                if config.get("download_queue_btn"):
                    item['gui']['btn']['queue'].show()
                if config.get("download_open_btn"):
                    item['gui']['btn']['open'].show()
                if config.get("download_locate_btn"):
                    item['gui']['btn']['locate'].show()
                if config.get("download_delete_btn"):
                    item['gui']['btn']['delete'].show()
                return
            elif progress != 0:
                item['gui']["btn"]['retry'].hide()
                if config.get("download_copy_btn"):
                    item['gui']['btn']['copy'].show()
                item['gui']["btn"]['cancel'].show()
                return

    def remove_completed_from_download_list(self):
        with download_queue_lock:
            check_row = 0
            while check_row < self.tbl_dl_progress.rowCount():
                item_id = self.tbl_dl_progress.item(check_row, 0).text()
                logger.info(f'Removing Row : {check_row} and mediaid: {item_id}')
                if item_id in download_queue:
                    if download_queue[item_id]['item_status'] in (
                                "Cancelled",
                                "Downloaded",
                                "Already Exists"
                            ):
                        logger.info(f'Removing Row : {check_row} and mediaid: {item_id}')
                        self.tbl_dl_progress.removeRow(check_row)
                        download_queue.pop(item_id)
                    else:
                        check_row = check_row + 1
                else:
                    check_row = check_row + 1

    def cancel_all_downloads(self):
        with download_queue_lock:
            row_count = self.tbl_dl_progress.rowCount()
            while row_count > 0:
                for item_id in download_queue.keys():
                    logger.info(f'Trying to cancel : {item_id}')
                    if download_queue[item_id]['item_status'] == "Waiting":
                        download_queue[item_id]['item_status'] = "Cancelled"
                        download_queue[item_id]['gui']['status_label'].setText(self.tr("Cancelled"))
                        download_queue[item_id]['gui']['status_label'].setText(self.tr("Cancelled"))
                        download_queue[item_id]['gui']['progress_bar'].setValue(0)
                        download_queue[item_id]['gui']["btn"]['cancel'].hide()
                        download_queue[item_id]['gui']["btn"]['retry'].show()
                    row_count -= 1

    def retry_all_failed_downloads(self):
        with download_queue_lock:
            row_count = self.tbl_dl_progress.rowCount()
            while row_count > 0:
                for item_id in download_queue.keys():
                    logger.info(f'Trying to cancel : {item_id}')
                    if download_queue[item_id]['item_status'] == "Failed":
                        download_queue[item_id]['item_status'] = "Waiting"
                        download_queue[item_id]['gui']['status_label'].setText(self.tr("Waiting"))
                        download_queue[item_id]['gui']["btn"]['cancel'].show()
                        download_queue[item_id]['gui']["btn"]['retry'].hide()
                    row_count -= 1


    # Remove Later
    def contribute(self):
        if self.inp_language.currentIndex() == self.inp_language.count() - 1:
            from ..queue import add_item_to_download_list
            url = "https://github.com/justin025/OnTheSpot/tree/main#contributing"
            open_item(url)

    def __init__(self, _dialog, start_url=''):
        super(MainWindow, self).__init__()
        self.path = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(config.app_root, 'resources', 'icons', 'onthespot.png')
        QApplication.setStyle("fusion")
        uic.loadUi(os.path.join(self.path, "qtui", "main.ui"), self)
        self.setWindowIcon(QtGui.QIcon(icon_path))

        self.start_url = start_url
        self.inp_version.setText(config.get("version"))
        self.inp_session_uuid.setText(config.session_uuid)
        logger.info(f"Initialising main window, logging session : {config.session_uuid}")
        self.group_search_items.hide()
        # Bind button click
        self.bind_button_inputs()


        self.__users = []
        self.last_search = None

        # Fill the value from configs
        logger.info("Loading configurations..")
        load_config(self)

        self.__splash_dialog = _dialog

        # Start/create session builder and queue processor
        fillaccountpool = FillAccountPool(gui=True)  
        fillaccountpool.finished.connect(self.session_load_done)
        fillaccountpool.progress.connect(self.__show_popup_dialog)
        fillaccountpool.start()


        queueworker = QueueWorker()
        queueworker.add_item_to_download_list.connect(self.add_item_to_download_list)  # Connect signal to update_table method  
        queueworker.start()

        downloadworker = DownloadWorker(gui=True)
        downloadworker.progress.connect(self.update_item_in_download_list)  # Connect the signal to the update method
        downloadworker.start()  # Start the download worker thread


        # Set application theme
        self.toggle_theme_button.clicked.connect(self.toggle_theme)
        self.theme = config.get("theme")
        self.theme_path = os.path.join(config.app_root,'resources', 'themes', f'{self.theme}.qss')
        if self.theme == "dark":
            self.toggle_theme_button.setText(self.tr(" Light Theme"))
            theme_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'light.png'))
        elif self.theme == "light":
            self.toggle_theme_button.setText(self.tr(" Dark Theme"))
            theme_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'dark.png'))
        self.toggle_theme_button.setIcon(theme_icon)

        with open(self.theme_path, 'r') as f:
              theme = f.read()
              self.setStyleSheet(theme)
        logger.info(f"Set theme {self.theme}!")

        # Set the table header properties
        self.set_table_props()
        logger.info("Main window init completed !")


    def load_dark_theme(self):
        self.theme = "dark"
        self.theme_path = os.path.join(config.app_root,'resources', 'themes', f'{self.theme}.qss')
        theme_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', f'light.png'))
        self.toggle_theme_button.setIcon(theme_icon)
        self.toggle_theme_button.setText(self.tr(" Light Theme"))
        with open(self.theme_path, 'r') as f:
            dark_theme = f.read()
            self.setStyleSheet(dark_theme)

    def load_light_theme(self):
        self.theme = "light"
        self.theme_path = os.path.join(config.app_root,'resources', 'themes', f'{self.theme}.qss')
        theme_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', f'dark.png'))
        self.toggle_theme_button.setIcon(theme_icon)
        self.toggle_theme_button.setText(self.tr(" Dark Theme"))
        with open(self.theme_path, 'r') as f:
            light_theme = f.read()
            self.setStyleSheet(light_theme)

    def toggle_theme(self):
        if self.theme == "light":
            self.load_dark_theme()
        elif self.theme == "dark":
            self.load_light_theme()

    def bind_button_inputs(self):
        # Connect button click signals
        collapse_down_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'collapse_down.png'))
        collapse_up_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'collapse_up.png'))

        self.btn_search.clicked.connect(self.fill_search_table)

        self.inp_login_service.currentIndexChanged.connect(self.set_login_fields)

        self.btn_save_config.clicked.connect(self.update_config)
        self.btn_reset_config.clicked.connect(self.reset_app_config)

        self.btn_progress_retry_all.clicked.connect(self.retry_all_failed_downloads)
        self.btn_progress_cancel_all.clicked.connect(self.cancel_all_downloads)
        self.btn_download_root_browse.clicked.connect(self.__select_dir)
        self.btn_download_tmp_browse.clicked.connect(self.__select_tmp_dir)
        self.inp_search_term.returnPressed.connect(self.fill_search_table)
        self.btn_progress_clear_complete.clicked.connect(self.remove_completed_from_download_list)
        self.btn_search_filter_toggle.clicked.connect(lambda toggle: self.group_search_items.show() if self.group_search_items.isHidden() else self.group_search_items.hide())
        self.btn_search_filter_toggle.clicked.connect(lambda switch: self.btn_search_filter_toggle.setIcon(collapse_down_icon) if self.group_search_items.isHidden() else self.btn_search_filter_toggle.setIcon(collapse_up_icon))


    def set_table_props(self):
        window_width = self.width()
        logger.info(f"Setting table item properties {window_width}")
        # Sessions table
        self.tbl_sessions.setSortingEnabled(True)
        self.tbl_sessions.horizontalHeader().setSectionsMovable(True)
        self.tbl_sessions.horizontalHeader().setSectionsClickable(True)
        self.tbl_sessions.horizontalHeader().resizeSection(0, 16)
        self.tbl_sessions.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_sessions.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl_sessions.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl_sessions.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tbl_sessions.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tbl_sessions.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        # Search results table
        self.tbl_search_results.setSortingEnabled(True)
        self.tbl_search_results.horizontalHeader().setSectionsMovable(True)
        self.tbl_search_results.horizontalHeader().setSectionsClickable(True)
        self.tbl_search_results.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_search_results.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_search_results.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl_search_results.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl_search_results.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        # Download progress table
        self.tbl_dl_progress.setSortingEnabled(True)
        self.tbl_dl_progress.horizontalHeader().setSectionsMovable(True)
        self.tbl_dl_progress.horizontalHeader().setSectionsClickable(True)
        if config.get("debug_mode"):
            self.tbl_dl_progress.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        else:
            self.tbl_dl_progress.setColumnWidth(0, 0)
        self.tbl_dl_progress.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_dl_progress.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl_dl_progress.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl_dl_progress.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.set_login_fields()
        return True


    def reset_app_config(self):
        config.rollback()
        self.__show_popup_dialog("The application setting was cleared successfully !\n Please restart the application.")

    def __select_dir(self):
        dir_path = QFileDialog.getExistingDirectory(None, 'Select a folder:', os.path.expanduser("~"))
        if dir_path.strip() != '':
            self.inp_download_root.setText(QDir.toNativeSeparators(dir_path))

    def __select_tmp_dir(self):
        dir_path = QFileDialog.getExistingDirectory(None, 'Select a folder:', os.path.expanduser("~"))
        if dir_path.strip() != '':
            self.inp_tmp_dl_root.setText(QDir.toNativeSeparators(dir_path))

    def __show_popup_dialog(self, txt, btn_hide=False):
        self.__splash_dialog.lb_main.setText(str(txt))
        if btn_hide:
            self.__splash_dialog.btn_close.hide()
        else:
            self.__splash_dialog.btn_close.show()
        self.__splash_dialog.show()

    def session_load_done(self):
        self.__splash_dialog.hide()
        self.__splash_dialog.btn_close.show()
        self.fill_account_table()
        self.show()
        if self.start_url.strip() != '':
            logger.info(f'Session was started with query of {self.start_url}')
            self.inp_search_term.setText(self.start_url.strip())
            self.fill_search_table()
        self.start_url = ''
        # Update Checker
        if config.get("check_for_updates"):
            if is_latest_release() == False:
                self.__splash_dialog.run(self.tr("<p>An update is available at the link below,<p><a style='color: #6495ed;' href='https://github.com/justin025/onthespot/releases/latest'>https://github.com/justin025/onthespot/releases/latest</a>"))

    def user_table_remove_click(self, index):
        if config.get('parsing_acc_sn') == self.tbl_sessions.currentRow():
            config.set_('parsing_acc_sn', self.tbl_sessions.currentRow() - 1)
            self.tbl_sessions.cellWidget(self.tbl_sessions.currentRow() - 1, 0).setChecked(True)
        if config.get('parsing_acc_sn') == "0":
            self.tbl_sessions.cellWidget(0, 0).setChecked(True)
        accounts = config.get('accounts').copy()
        del accounts[index]
        config.set_('accounts', accounts)
        config.update()
        del account_pool[index]
        self.tbl_sessions.removeRow(index)
        self.__splash_dialog.run(self.tr("Account was removed successfully."))

    def update_config(self):
        save_config(self)

    def set_login_fields(self):
        # Spotify
        if self.inp_login_service.currentIndex() == 0:
            self.lb_login_username.hide()
            self.inp_login_username.hide()
            self.lb_login_password.hide()
            self.inp_login_password.hide()
            self.btn_login_add.show()
            self.btn_login_add.setText(self.tr("Add Spotify Account"))
            self.btn_login_add.clicked.connect(self.add_spotify_account)

        # Soundcloud
        elif self.inp_login_service.currentIndex() == 1:
            self.lb_login_username.show()
            self.lb_login_username.setText(self.tr("Client ID"))
            self.inp_login_username.show()
            self.lb_login_password.show()
            self.lb_login_password.setText(self.tr("Token"))
            self.inp_login_password.show()
            self.btn_login_add.show()
            self.btn_login_add.setText(self.tr("Add Account"))

    def add_spotify_account(self):
        logger.info('Add spotify account clicked ')
        self.btn_login_add.setText(self.tr("Waiting..."))
        self.btn_login_add.setDisabled(True)
        self.inp_login_service.setDisabled(True)
        self.__splash_dialog.run(self.tr("Login Service Started...\nSelect 'OnTheSpot' under devices in the Spotify Desktop App."))
        login_worker = threading.Thread(target=self.add_spotify_account_worker)
        login_worker.daemon = True
        login_worker.start()

    def add_spotify_account_worker(self):
        session = spotify_new_session()
        if session == True:
            self.__splash_dialog.run(self.tr("Account added, please restart the app."))
            self.btn_login_add.setText(self.tr("Please Restart The App"))
            config.set_('parsing_acc_sn', config.get('parsing_acc_sn') + 1)
            config.update()
        elif session == False:
            self.__splash_dialog.run(self.tr("Account already exists."))
            self.btn_login_add.setText(self.tr("Add Account"))
            self.btn_login_add.setDisabled(False)

    def fill_search_table(self):
        while self.tbl_search_results.rowCount() > 0:
            self.tbl_search_results.removeRow(0)
        search_term = self.inp_search_term.text().strip()
        content_types = []
        if self.inp_enable_search_tracks.isChecked():
            content_types.append('track')
        if self.inp_enable_search_playlists.isChecked():
            content_types.append('playlist')
        if self.inp_enable_search_albums.isChecked():
            content_types.append('album')
        if self.inp_enable_search_artists.isChecked():
            content_types.append('artist')
        if self.inp_enable_search_shows.isChecked():
            content_types.append('show')
        if self.inp_enable_search_episodes.isChecked():
            content_types.append('episode')
        if self.inp_enable_search_audiobooks.isChecked():
            content_types.append('audiobook')

        results = get_search_results(search_term, content_types)
        if results is None:
            self.__splash_dialog.run(self.tr("You need to login to at least one account to use this feature."))
            self.inp_search_term.setText('')
            return
        elif results is True:
            self.__splash_dialog.run(self.tr("Item is being parsed and will be added to the download queue shortly."))
            self.inp_search_term.setText('')
            return
        elif results is False:
            self.__splash_dialog.run(self.tr("Invalid item, please check your query or account settings"))
            self.inp_search_term.setText('')
            return


        for result in results:
            btn = QPushButton(self.tbl_search_results)
            #btn.setText(btn_text.strip())
            btn.setIcon(QIcon(os.path.join(config.app_root, 'resources', 'icons', 'download.png')))

            item_url = result['item_url']

            def download_btn_clicked(item_name, item_url, item_service, item_type, item_id, ):
                parsing[item_id] = {
                    'item_url': item_url, 
                    'item_service': item_service,
                    'item_type': item_type, 
                    'item_id': item_id
                }
                self.__splash_dialog.run(self.tr("{0} is being parsed and will be added to the download queue shortly.").format(f"{item_type.title()}: {item_name}"))

            btn.clicked.connect(lambda x, 
                            item_name=result['item_name'], 
                            item_url=result['item_url'], 
                            item_type=result['item_type'], 
                            item_id=result['item_id'], 
                            item_service=result['item_service']: 
                            download_btn_clicked(item_name, item_url, item_service, item_type, item_id))

            btn.setMinimumHeight(30)
            service = QTableWidgetItem(result['item_service'].title())
            service.setIcon(QIcon(os.path.join(config.app_root, 'resources', 'icons', f'{result["item_service"]}.png')))

            rows = self.tbl_search_results.rowCount()
            self.tbl_search_results.insertRow(rows)

            if config.get('show_search_thumbnails'):
                self.tbl_search_results.setRowHeight(rows, config.get("search_thumb_height"))
                item_label = LabelWithThumb(result['item_name'], result['item_thumbnail_url'])
            else:
                item_label = QLabel(self.tbl_dl_progress)
                item_label.setText(result['item_name'])

            self.tbl_search_results.setCellWidget(rows, 0, item_label)
            self.tbl_search_results.setItem(rows, 1, QTableWidgetItem(str(result['item_by'])))
            self.tbl_search_results.setItem(rows, 2, QTableWidgetItem(result['item_type'].title()))
            self.tbl_search_results.setItem(rows, 3, service)
            self.tbl_search_results.setCellWidget(rows, 4, btn)
            self.tbl_search_results.horizontalHeader().resizeSection(0, 450)
        self.inp_search_term.setText('')
