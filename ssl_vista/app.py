import sys
import signal
from PyQt5.QtWidgets import QApplication

from ssl_vista import MainWindow

def run_app(layout: str, data_path):
    app = QApplication(sys.argv)

    # --- Handle Ctrl+C ---
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Restore default handler

    # Create main window and pass args
    window = MainWindow(layout=layout, data_path=data_path)
    window.show()

    sys.exit(app.exec())