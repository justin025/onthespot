import os
import time
from PyQt6.QtCore import QObject, pyqtSignal
from ..otsconfig import config_dir, config
from ..runtimedata import session_pool, get_logger
from ..utils.utils import login_user

logger = get_logger("worker.session")


class LoadSessions(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str, bool)
    __users = None

    def run(self):
        logger.info('Session loader has started !')
        accounts = config.get('accounts')
        t = len(accounts)
        c = 0
        for account in accounts:
            c = c + 1
            logger.info(f'Trying to create session for {account[0][:4]}')
            self.progress.emit(self.tr('Attempting to create session for\n{0}...').format(account[0]), True)
            time.sleep(0.2)
            login = login_user(account[0], "",
                               os.path.join(config_dir(), 'onthespot', 'sessions'), account[3])
            logged_in = False
            if login is not None:
                if login[0]:
                    # Login was successful, add to session pool
                    self.progress.emit(self.tr('Session created for\n{0}!').format(account[0]), True)
                    time.sleep(0.2)
                    session_pool[account[3]] = login[1]
                    self.__users.append([account[0], 'Premium' if login[3] else 'Free', 'OK', account[3]])
                    logged_in = True
            if not logged_in:
                self.progress.emit(self.tr('Failed to create session for\n{0}.').format(account[0]), True)
                self.__users.append([account[0], self.tr("LoginERROR"), self.tr("ERROR"), account[3]])
        self.finished.emit()

    def setup(self, users):
        self.__users = users
