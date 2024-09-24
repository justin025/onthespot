import platform
import os
import subprocess
import pyperclip
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QWidget
from ..otsconfig import config
from ..runtimedata import downloaded_data, cancel_list, failed_downloads, downloads_status, download_queue, session_pool, get_logger
from ..utils.utils import open_item
from ..utils.spotify import check_if_media_in_library, save_media_to_library, remove_media_from_library, queue_media, play_media

logger = get_logger("worker.utility")


class DownloadActionsButtons(QWidget):
    def __init__(self, dl_id, media_type, pbar, copy_btn, cancel_btn, remove_btn, play_btn, save_btn, queue_btn, open_btn, locate_btn, delete_btn, parent=None):
        super(DownloadActionsButtons, self).__init__(parent)
        self.__id = dl_id
        self.media_type = media_type
        self.copy_btn = copy_btn
        self.cancel_btn = cancel_btn
        self.remove_btn = remove_btn
        self.play_btn = play_btn
        self.save_btn = save_btn
        self.queue_btn = queue_btn
        self.open_btn = open_btn
        self.locate_btn = locate_btn
        self.delete_btn = delete_btn
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        copy_btn.clicked.connect(self.copy_link)
        cancel_btn.clicked.connect(self.cancel_item)
        remove_btn.clicked.connect(self.retry_item)
        play_btn.clicked.connect(self.play_item)
        save_btn.clicked.connect(self.save_item)
        queue_btn.clicked.connect(self.queue_item)
        open_btn.clicked.connect(self.open_file)
        locate_btn.clicked.connect(self.locate_file)
        delete_btn.clicked.connect(self.delete_file)
        layout.addWidget(pbar)
        layout.addWidget(copy_btn)
        layout.addWidget(cancel_btn)
        layout.addWidget(remove_btn)
        layout.addWidget(play_btn)
        layout.addWidget(save_btn)
        layout.addWidget(queue_btn)
        layout.addWidget(open_btn)
        layout.addWidget(locate_btn)
        layout.addWidget(delete_btn)
        self.setLayout(layout)
        if config.get("download_save_btn"):
            #selected_uuid = config.get('accounts')[config.get('parsing_acc_sn') - 1][3]
            selected_uuid = config.get('accounts')[0][3]
            self.session = session_pool[selected_uuid]
            in_library = check_if_media_in_library(self.session, self.__id, self.media_type)
            if in_library:
                save_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'filled-heart.png'))
                save_btn.setIcon(save_icon)
                self.in_library = True
            elif not in_library:
                save_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'empty-heart.png'))
                save_btn.setIcon(save_icon)
                self.in_library = False
            else:
                logger.info(f"Unable to determine if song is in library, value: {in_library}")

    def copy_link(self):
        pyperclip.copy(f"https://open.spotify.com/{self.media_type}/{self.__id}")

    def cancel_item(self):
        cancel_list[self.__id] = {}
        self.cancel_btn.hide()

    def retry_item(self):
        if self.__id in failed_downloads:
            downloads_status[self.__id]["status_label"].setText(self.tr("Waiting"))
            self.remove_btn.hide()
            download_queue.put(failed_downloads[self.__id])
            self.cancel_btn.show()

    def play_item(self):
        play_media(self.session, self.__id, self.media_type)

    def save_item(self):
        if self.in_library:
            remove_media_from_library(self.session, self.__id, self.media_type)
            save_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'empty-heart.png'))
            self.save_btn.setIcon(save_icon)
            self.in_library = False
            logger.info(f"Song removed from spotify library")
        elif not self.in_library:
            save_media_to_library(self.session, self.__id, self.media_type)
            save_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'filled-heart.png'))
            self.save_btn.setIcon(save_icon)
            self.in_library = True
            logger.info(f"Song saved to spotify library")
        else:
            logger.info(f"Unable to determine if song is in library cannot save, value: {in_library}")

    def queue_item(self):
        queue_media(self.session, self.__id, self.media_type)

    def open_file(self):
        file = os.path.abspath(downloaded_data[self.__id]['media_path'])
        open_item(file)

    def locate_file(self):
        if self.__id in downloaded_data:
            if downloaded_data[self.__id].get('media_path', None):
                file_dir = os.path.dirname(downloaded_data[self.__id]['media_path'])
                open_item(file_dir)

    def delete_file(self):
        file = os.path.abspath(downloaded_data[self.__id]['media_path'])
        os.remove(file)
        downloads_status[self.__id]["status_label"].setText(self.tr("Deleted"))
        self.play_btn.hide()
        self.save_btn.hide()
        self.queue_btn.hide()
        self.open_btn.hide()
        self.locate_btn.hide()
        self.delete_btn.hide()
