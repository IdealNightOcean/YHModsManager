import logging

from PyQt6.QtCore import QThread, pyqtSignal

from core.mod_parser import ModParser
from ui.i18n import tr

logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, parser: ModParser):
        super().__init__()
        self.parser = parser

    def run(self):
        try:
            self.progress.emit(tr("refresh_mods"))
            mods = self.parser.scan_all_mods()

            if not mods and self.parser.last_error:
                self.error.emit(self.parser.last_error)

            self.finished.emit(mods)
        except Exception as e:
            logger.error(f"ScanWorker failed: {e}", exc_info=True)
            self.error.emit(str(e))
            self.finished.emit([])
