#!/usr/bin/env python3
import os
import sys
from PyQt6.QtCore import QTranslator
from PyQt6.QtWidgets import QApplication
from .gui.mainui import MainWindow
from .gui.minidialog import MiniDialog
from .runtimedata import get_logger
from .otsconfig import config

def main():
    logger = get_logger('__init__')
    logger.info('Starting application in \n3\n2\n1')
    app = QApplication(sys.argv)

    # Set Application Version
    version = "v0.7.0"
    logger.info(f'OnTheSpot Version: {version}')

    # Migration (<v0.7)
    if int(version.replace('v', '').replace('.', '')) > int(config.get("version").replace('v', '').replace('.', '')):
        if " " not in config.get("metadata_seperator"):
            config.set_("metadata_seperator", config.get("metadata_seperator")+" ")
        config.set_("download_play_btn", False)

    config.set_("version", version)

    # Language
    if config.get("language_index") == 0:
        config.set_("language", "en_US")
    elif config.get("language_index") == 1:
        config.set_("language", "de_DE")
    elif config.get("language_index") == 2:
        config.set_("language", "pt_PT")
    else:
        logger.info(f'Unknown language index: {config.get("language_index")}')
        config.set_("language", "en_US")

    config.update()

    translator = QTranslator()
    path = os.path.join(os.path.join(config.app_root, 'resources', 'translations'),
                 f"{config.get('language')}.qm")
    translator.load(path)
    app.installTranslator(translator)

    # Check for start url
    try:
        if sys.argv[1] == "-u" or sys.argv[1] == "--url":
            start_url = sys.argv[2]
        else:
            start_url = ""
    except IndexError:
        start_url = ""

    _dialog = MiniDialog()
    window = MainWindow(_dialog, start_url)
    app.setDesktopFileName('org.eu.casualsnek.onthespot')
    app.exec()
    logger.info('Good bye ..')


if __name__ == '__main__':
    main()
