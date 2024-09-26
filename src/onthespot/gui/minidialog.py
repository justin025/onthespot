import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import Qt
from ..runtimedata import get_logger
from ..otsconfig import config

logger = get_logger('gui.minidialog')


class MiniDialog(QDialog):
    def __init__(self, parent=None):
        super(MiniDialog, self).__init__(parent)
        self.path = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(os.path.join(self.path, 'qtui', 'notice.ui'), self)
        self.btn_close.clicked.connect(self.hide)
        logger.debug('Dialog item is ready..')

        # Set theme
        self.theme = config.get("theme")
        self.theme_path = os.path.join(config.app_root,'resources', 'themes', f'{self.theme}.qss')
        if self.theme == "dark":
          with open(self.theme_path, 'r') as f:
              dark_theme = f.read()
              self.setStyleSheet(dark_theme)
        elif self.theme == "light":
          with open(self.theme_path, 'r') as f:
              light_theme = f.read()
              self.setStyleSheet(light_theme)

        def load_dark_theme(self):
            with open(self.dark_theme_path, 'r') as f:
                dark_theme = f.read()
                self.setStyleSheet(dark_theme)
            self.theme = "dark"

        def load_light_theme(self):
            with open(self.light_theme_path, 'r') as f:
                light_theme = f.read()
                self.setStyleSheet(light_theme)
            self.theme = "dark"

        def toggle_theme(self):
            if self.theme == "light":
                self.load_dark_theme()
            elif self.theme == "dark":
                self.load_light_theme()

    def run(self, content, btn_hidden=False):
        if btn_hidden:
            self.btn_close.hide()
        else:
            self.btn_close.show()
        self.show()
        logger.debug(f"Displaying dialog with text '{content}'")
        self.lb_main.setText(str(content))
