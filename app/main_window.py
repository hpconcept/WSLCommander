from qfluentwidgets import FluentWindow, FluentIcon

from app.pages.distros_page import DistrosPage
from app.pages.usb_page import UsbPage
from app.pages.install_page import InstallPage


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self._init_window()
        self._init_navigation()

    def _init_window(self):
        self.setWindowTitle("WSL Commander")
        self.setMinimumSize(900, 650)
        self.resize(1100, 720)


    def _init_navigation(self):
        self.distros_page = DistrosPage(self)
        self.usb_page = UsbPage(self)
        self.install_page = InstallPage(self)

        self.addSubInterface(
            interface=self.distros_page,
            icon=FluentIcon.HOME,
            text="Distributions",
        )
        self.addSubInterface(
            interface=self.usb_page,
            icon=FluentIcon.CONNECT,
            text="USB Sharing",
        )
        self.addSubInterface(
            interface=self.install_page,
            icon=FluentIcon.DOWNLOAD,
            text="Install",
        )

        self.navigationInterface.setCurrentItem(self.distros_page.objectName())


