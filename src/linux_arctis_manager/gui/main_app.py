import logging
import os
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from linux_arctis_manager.gui.base_app import QBaseDesktopApp
from linux_arctis_manager.gui.dbus_wrapper import DbusWrapper
from linux_arctis_manager.gui.backend import ArctisBackend
from linux_arctis_manager.gui.ui_utils import get_icon_pixmap


class QMainApp(QBaseDesktopApp):
    def __init__(self, app, log_level: int):
        super().__init__(parent=app)

        self.logger = logging.getLogger('KirigamiApp')
        self.logger.setLevel(log_level)
        self.app = app

        # Dbus wrapper
        self.dbus_wrapper = DbusWrapper()
        self.backend = ArctisBackend(self.dbus_wrapper)

        self.engine = QQmlApplicationEngine()
        
        # Add system Qt6 QML paths so pip-installed PySide6 can find Kirigami
        self.engine.addImportPath("/usr/lib/qt6/qml")
        self.engine.addImportPath("/usr/lib/x86_64-linux-gnu/qt6/qml")
        
        self.engine.rootContext().setContextProperty("backend", self.backend)
        
        self.app.setWindowIcon(QIcon(get_icon_pixmap()))

        # Connect to DBus
        self.dbus_wrapper.start()
        self.destroyed.connect(self.sig_stop)

    def start_sync(self):
        self.logger.info('Starting Kirigami app.')
        qml_file = os.path.join(os.path.dirname(__file__), 'qml', 'Main.qml')
        self.engine.load(QUrl.fromLocalFile(qml_file))

        if not self.engine.rootObjects():
            self.logger.error("Failed to load QML")
            return

        self.app.exec()
    
    async def start(self):
        self.start_sync()

    def sig_stop(self):
        if hasattr(self, '_stopping') and self._stopping:
            return
        self._stopping = True

        self.dbus_wrapper.stop()
        self.logger.debug('Received shutdown signal, shutting down.')
        self.app.quit()
