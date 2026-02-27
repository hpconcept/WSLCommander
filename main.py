import sys
import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import setTheme, Theme

from app.main_window import MainWindow


def main():
    # Enable High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("WSL Commander")
    app.setApplicationDisplayName("WSL Commander")

    # Set application icon
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    setTheme(Theme.AUTO)

    window = MainWindow()

    # Also set the window icon directly
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

