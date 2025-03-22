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
    config.migration()
    logger.info(f'OnTheSpot Version: {config.get("version")}')

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
