import os

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QSizePolicy, QSpacerItem, QFileDialog, QGridLayout,
)
from qfluentwidgets import (
    ScrollArea, TitleLabel, SubtitleLabel, BodyLabel,
    PrimaryPushButton, PushButton, ToolButton,
    InfoBar, InfoBarPosition, IndeterminateProgressBar,
    CardWidget, FluentIcon, setTheme, isDarkTheme,
    SimpleCardWidget, IconWidget, CaptionLabel,
    MessageBox,
)

from app.workers.wsl_worker import (
    ListInstalledWorker, SetDefaultWorker,
    TerminateDistroWorker, UnregisterDistroWorker,
    LaunchDistroTerminalWorker, ExportDistroWorker,
)


class DistroCard(CardWidget):
    """A card representing a single installed WSL distribution."""

    def __init__(self, distro, parent_page, parent=None):
        super().__init__(parent)
        self.distro = distro
        self.parent_page = parent_page
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui()

    def mousePressEvent(self, event):
        """Open a terminal for this distribution when clicked."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_page.launch_terminal(self.distro.name)
        super().mousePressEvent(event)

    def _build_ui(self):
        self.setFixedHeight(110)
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(16)

        # Logo
        logo_label = QLabel()
        logo_label.setFixedSize(64, 64)
        logo_label.setScaledContents(True)
        if self.distro.logo_path:
            px = QPixmap(self.distro.logo_path)
            if not px.isNull():
                logo_label.setPixmap(px)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(logo_label)

        # Info section
        info = QVBoxLayout()
        info.setSpacing(4)

        name_row = QHBoxLayout()
        name_label = SubtitleLabel(self.distro.name)
        name_row.addWidget(name_label)

        if self.distro.is_default:
            default_badge = CaptionLabel("  ★ Default  ")
            default_badge.setObjectName("defaultBadge")
            default_badge.setStyleSheet(
                "background-color: #0078D4; color: white; border-radius: 8px; padding: 2px 6px;"
            )
            name_row.addWidget(default_badge)

        name_row.addStretch()
        info.addLayout(name_row)

        # Status line
        status_color = "#107C10" if self.distro.state.lower() == "running" else "#797775"
        status_label = CaptionLabel(f"● {self.distro.state}   WSL{self.distro.version}")
        status_label.setStyleSheet(f"color: {status_color};")
        info.addWidget(status_label)

        root.addLayout(info)
        root.addStretch()

        # 2×2 button grid
        # row 0: Set as Default | Export
        # row 1: Stop           | Remove
        btn_grid = QGridLayout()
        btn_grid.setSpacing(6)
        btn_grid.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        BTN_W = 120

        # row 0, col 0 — Set as Default (hidden when already default)
        if not self.distro.is_default:
            set_default_btn = PrimaryPushButton("Set as Default")
            set_default_btn.setFixedWidth(BTN_W)
            set_default_btn.clicked.connect(lambda: self.parent_page.set_default(self.distro.name))
            btn_grid.addWidget(set_default_btn, 0, 0)
        else:
            btn_grid.addItem(
                QSpacerItem(BTN_W, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum), 0, 0
            )

        # row 0, col 1 — Export
        export_btn = PushButton(FluentIcon.SHARE, "Export")
        export_btn.setFixedWidth(BTN_W)
        export_btn.setToolTip("Export this distribution to a .tar file")
        export_btn.clicked.connect(lambda: self.parent_page.export_distro(self.distro.name))
        btn_grid.addWidget(export_btn, 0, 1)

        # row 1, col 0 — Stop (only when running)
        if self.distro.state.lower() == "running":
            stop_btn = PushButton("Stop")
            stop_btn.setFixedWidth(BTN_W)
            stop_btn.clicked.connect(lambda: self.parent_page.terminate_distro(self.distro.name))
            btn_grid.addWidget(stop_btn, 1, 0)

        # row 1, col 1 — Remove
        remove_btn = PushButton("Remove")
        remove_btn.setFixedWidth(BTN_W)
        remove_btn.clicked.connect(lambda: self.parent_page.remove_distro(self.distro.name))
        btn_grid.addWidget(remove_btn, 1, 1)

        root.addLayout(btn_grid)


class DistrosPage(ScrollArea):
    """Page showing all installed WSL distributions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DistrosPage")
        self._workers = []

        # Scroll content
        self._content = QWidget()
        self._content.setObjectName("distrosContent")
        self._main_layout = QVBoxLayout(self._content)
        self._main_layout.setContentsMargins(30, 20, 30, 20)
        self._main_layout.setSpacing(12)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setWidget(self._content)
        self.setWidgetResizable(True)

        self._build_header()
        self._build_cards_area()
        self.refresh()

    def _build_header(self):
        header = QHBoxLayout()
        title = TitleLabel("Installed Distributions")
        header.addWidget(title)
        header.addStretch()

        refresh_btn = ToolButton(FluentIcon.SYNC)
        refresh_btn.setToolTip("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        self._main_layout.addLayout(header)

        self._progress = IndeterminateProgressBar(self)
        self._progress.setVisible(False)
        self._main_layout.addWidget(self._progress)

    def _build_cards_area(self):
        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(10)
        self._main_layout.addWidget(self._cards_widget)

    def _clear_cards(self):
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def refresh(self):
        self._progress.setVisible(True)
        worker = ListInstalledWorker(self)
        worker.result.connect(self._on_distros_loaded)
        worker.error.connect(self._on_error)
        worker.finished.connect(lambda: self._progress.setVisible(False))
        self._workers.append(worker)
        worker.start()

    def _on_distros_loaded(self, distros):
        self._clear_cards()
        if not distros:
            empty = BodyLabel("No WSL distributions found. Go to the Install tab to add one.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._cards_layout.addWidget(empty)
            return
        for d in distros:
            card = DistroCard(d, self)
            self._cards_layout.addWidget(card)

    def _on_error(self, msg):
        InfoBar.error(
            title="Error",
            content=msg,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self,
        )

    def set_default(self, name: str):
        worker = SetDefaultWorker(name, self)
        worker.done.connect(self._on_action_done)
        self._workers.append(worker)
        worker.start()

    def terminate_distro(self, name: str):
        worker = TerminateDistroWorker(name, self)
        worker.done.connect(self._on_action_done)
        self._workers.append(worker)
        worker.start()

    def export_distro(self, name: str):
        default_filename = f"{name}.tar"
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export '{name}'",
            os.path.join(os.path.expanduser("~"), default_filename),
            "TAR Archive (*.tar);;All Files (*)",
        )
        if not export_path:
            return  # user cancelled
        # Show a progress notification
        InfoBar.info(
            title="Exporting…",
            content=f"Exporting '{name}', please wait. This may take a while.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self,
        )
        worker = ExportDistroWorker(name, export_path, self)
        worker.done.connect(self._on_action_done)
        self._workers.append(worker)
        worker.start()

    def remove_distro(self, name: str):
        dlg = MessageBox(
            "Remove Distribution",
            f"Are you sure you want to unregister '{name}'?\nThis will permanently delete all data in this distribution.",
            self,
        )
        if dlg.exec():
            worker = UnregisterDistroWorker(name, self)
            worker.done.connect(self._on_action_done)
            self._workers.append(worker)
            worker.start()

    def launch_terminal(self, name: str):
        worker = LaunchDistroTerminalWorker(name, self)
        worker.done.connect(self._on_action_done)
        self._workers.append(worker)
        worker.start()

    def _on_action_done(self, success: bool, msg: str):
        if success:
            InfoBar.success(
                title="Success", content=msg,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000, parent=self,
            )
        else:
            InfoBar.error(
                title="Error", content=msg,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000, parent=self,
            )
        self.refresh()

