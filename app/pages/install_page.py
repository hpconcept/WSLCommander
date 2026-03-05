import os

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
)
from qfluentwidgets import (
    ScrollArea, TitleLabel, SubtitleLabel, BodyLabel, CaptionLabel,
    PrimaryPushButton, ToolButton, SearchLineEdit, LineEdit,
    InfoBar, InfoBarPosition, IndeterminateProgressBar,
    CardWidget, FluentIcon, SimpleCardWidget, SegmentedWidget,
)

from app.utils.logo_resolver import resolve_logo_path
from app.workers.wsl_worker import (
    ListAvailableWorker, LaunchInstallTerminalWorker, ImportDistroWorker,
)


class AvailableDistroListItem(CardWidget):
    """List item for an available (not yet installed) distro with logo."""

    def __init__(self, name: str, friendly_name: str, parent_page, parent=None):
        super().__init__(parent)
        self.distro_name = name
        self.friendly_name = friendly_name
        self.parent_page = parent_page
        self._selected = False
        self._build()

    def _build(self):
        self.setFixedHeight(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # Logo
        logo = QLabel()
        logo.setFixedSize(56, 56)
        logo.setScaledContents(True)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        px = QPixmap(resolve_logo_path(self.distro_name))
        if not px.isNull():
            logo.setPixmap(px)
        layout.addWidget(logo)

        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        name_label = SubtitleLabel(self.distro_name)
        info_layout.addWidget(name_label)

        friendly_label = CaptionLabel(self.friendly_name)
        friendly_label.setStyleSheet("color: gray;")
        info_layout.addWidget(friendly_label)

        layout.addLayout(info_layout)
        layout.addStretch()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.parent_page.select_card(self)

    def set_selected(self, selected: bool):
        self._selected = selected
        if selected:
            self.setStyleSheet("CardWidget { border: 2px solid #0078D4; border-radius: 8px; }")
        else:
            self.setStyleSheet("")


class InstallPage(ScrollArea):
    """Page for browsing/installing new WSL distributions, or importing from a .tar file."""

    # Emitted after a distribution is fully installed/imported (e.g. import from .tar)
    distro_installed = pyqtSignal()
    # Emitted when a catalogue installer terminal has been launched (install is async)
    install_launched = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InstallPage")
        self._workers = []
        self._all_distros = []
        self._cards: list[AvailableDistroListItem] = []
        self._selected_card: AvailableDistroListItem | None = None

        self._content = QWidget()
        self._content.setObjectName("installContent")
        self._main_layout = QVBoxLayout(self._content)
        self._main_layout.setContentsMargins(30, 20, 30, 30)
        self._main_layout.setSpacing(16)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setWidget(self._content)
        self.setWidgetResizable(True)

        self._build_ui()
        self._load_available()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Page title
        header_row = QHBoxLayout()
        title = TitleLabel("Install / Import Distributions")
        header_row.addWidget(title)
        header_row.addStretch()
        self._main_layout.addLayout(header_row)

        # ── Segmented tab bar ─────────────────────────────────────────
        self._tab_bar = SegmentedWidget(self._content)
        self._tab_bar.addItem(
            routeKey="catalogue",
            text="  Install from Catalogue  ",
            onClick=lambda: self._switch_tab("catalogue"),
            icon=FluentIcon.DOWNLOAD,
        )
        self._tab_bar.addItem(
            routeKey="import",
            text="  Import from .tar  ",
            onClick=lambda: self._switch_tab("import"),
            icon=FluentIcon.FOLDER_ADD,
        )
        self._tab_bar.setCurrentItem("catalogue")

        tab_bar_row = QHBoxLayout()
        tab_bar_row.addWidget(self._tab_bar)
        tab_bar_row.addStretch()
        self._main_layout.addLayout(tab_bar_row)

        # ── Stacked panels — shown/hidden so height adapts naturally ──
        self._catalogue_panel = self._build_catalogue_panel()
        self._import_panel = self._build_import_panel()
        self._main_layout.addWidget(self._catalogue_panel)
        self._main_layout.addWidget(self._import_panel)
        self._import_panel.hide()

    def _switch_tab(self, key: str):
        self._tab_bar.setCurrentItem(key)
        if key == "catalogue":
            self._import_panel.hide()
            self._catalogue_panel.show()
        else:
            self._catalogue_panel.hide()
            self._import_panel.show()

    # ── Panel: Install from catalogue ─────────────────────────────────

    def _build_catalogue_panel(self) -> QWidget:
        panel = SimpleCardWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Refresh button (right-aligned)
        refresh_row = QHBoxLayout()
        refresh_row.addStretch()
        refresh_btn = ToolButton(FluentIcon.SYNC)
        refresh_btn.setToolTip("Reload available distributions")
        refresh_btn.clicked.connect(self._load_available)
        refresh_row.addWidget(refresh_btn)
        layout.addLayout(refresh_row)

        # Full-width hint text
        hint = BodyLabel(
            "Select a distribution and click Install. "
            "Requires an internet connection and WSL 2 to be enabled."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Search bar
        self._search = SearchLineEdit()
        self._search.setPlaceholderText("Search distributions…")
        self._search.textChanged.connect(self._filter)
        self._search.setMaximumWidth(400)
        layout.addWidget(self._search)

        self._progress = IndeterminateProgressBar(panel)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Distro list
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._list_widget)

        # Install action row
        install_row = QHBoxLayout()
        self._selected_label = BodyLabel("No distribution selected.")
        install_row.addWidget(self._selected_label)
        install_row.addStretch()
        self._install_btn = PrimaryPushButton(FluentIcon.DOWNLOAD, "Install")
        self._install_btn.setEnabled(False)
        self._install_btn.setFixedWidth(140)
        self._install_btn.clicked.connect(self._install_selected)
        install_row.addWidget(self._install_btn)
        layout.addLayout(install_row)

        return panel

    # ── Panel: Import from .tar ────────────────────────────────────────

    def _build_import_panel(self) -> QWidget:
        panel = SimpleCardWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        hint = BodyLabel(
            "Import a previously exported WSL distribution from a .tar archive. "
            "Provide a unique name, choose where to install it, and select the archive."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Form: three fields side-by-side
        form_layout = QHBoxLayout()
        form_layout.setSpacing(16)

        # Left — Distribution name
        left = QVBoxLayout()
        left.setSpacing(4)
        left.addWidget(CaptionLabel("Distribution name"))
        self._import_name_edit = LineEdit()
        self._import_name_edit.setPlaceholderText("e.g. MyUbuntu")
        self._import_name_edit.setMinimumWidth(200)
        self._import_name_edit.textChanged.connect(self._update_import_btn)
        left.addWidget(self._import_name_edit)
        form_layout.addLayout(left)

        # Middle — Install location
        middle = QVBoxLayout()
        middle.setSpacing(4)
        middle.addWidget(CaptionLabel("Install location (folder)"))
        dir_row = QHBoxLayout()
        dir_row.setSpacing(6)
        self._import_dir_edit = LineEdit()
        self._import_dir_edit.setPlaceholderText(
            os.path.join(os.path.expanduser("~"), "WSL")
        )
        self._import_dir_edit.setMinimumWidth(220)
        self._import_dir_edit.textChanged.connect(self._update_import_btn)
        dir_row.addWidget(self._import_dir_edit)
        browse_dir_btn = ToolButton(FluentIcon.FOLDER)
        browse_dir_btn.setToolTip("Browse for install folder")
        browse_dir_btn.clicked.connect(self._browse_install_dir)
        dir_row.addWidget(browse_dir_btn)
        middle.addLayout(dir_row)
        form_layout.addLayout(middle)

        # Right — TAR archive
        right = QVBoxLayout()
        right.setSpacing(4)
        right.addWidget(CaptionLabel("TAR archive"))
        tar_row = QHBoxLayout()
        tar_row.setSpacing(6)
        self._import_tar_edit = LineEdit()
        self._import_tar_edit.setPlaceholderText("Select a .tar file…")
        self._import_tar_edit.setMinimumWidth(220)
        self._import_tar_edit.setReadOnly(True)
        tar_row.addWidget(self._import_tar_edit)
        browse_tar_btn = ToolButton(FluentIcon.FOLDER)
        browse_tar_btn.setToolTip("Browse for .tar archive")
        browse_tar_btn.clicked.connect(self._browse_tar)
        tar_row.addWidget(browse_tar_btn)
        right.addLayout(tar_row)
        form_layout.addLayout(right)

        layout.addLayout(form_layout)

        # Import action row
        import_row = QHBoxLayout()
        self._import_status_label = BodyLabel("")
        import_row.addWidget(self._import_status_label)
        import_row.addStretch()
        self._import_btn = PrimaryPushButton(FluentIcon.FOLDER_ADD, "Import")
        self._import_btn.setEnabled(False)
        self._import_btn.setFixedWidth(140)
        self._import_btn.clicked.connect(self._run_import)
        import_row.addWidget(self._import_btn)
        layout.addLayout(import_row)

        return panel

    # ------------------------------------------------------------------
    # Install-from-catalogue logic
    # ------------------------------------------------------------------

    def _load_available(self):
        self._progress.setVisible(True)
        self._clear_list()
        worker = ListAvailableWorker(self)
        worker.result.connect(self._on_available_loaded)
        worker.error.connect(self._on_error)
        worker.finished.connect(lambda: self._progress.setVisible(False))
        self._workers.append(worker)
        worker.start()

    def _on_available_loaded(self, distros: list):
        self._all_distros = distros
        self._populate_list(distros)

    def _populate_list(self, distros: list):
        self._clear_list()
        self._cards = []
        for d in distros:
            item = AvailableDistroListItem(d["name"], d["friendly_name"], self)
            self._cards.append(item)
            self._list_layout.addWidget(item)

    def _clear_list(self):
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._selected_card = None
        self._install_btn.setEnabled(False)
        self._selected_label.setText("No distribution selected.")

    def _filter(self, text: str):
        lower = text.lower()
        filtered = (
            [d for d in self._all_distros
             if lower in d["name"].lower() or lower in d["friendly_name"].lower()]
            if text else self._all_distros
        )
        self._populate_list(filtered)

    def select_card(self, card: AvailableDistroListItem):
        if self._selected_card:
            self._selected_card.set_selected(False)
        self._selected_card = card
        card.set_selected(True)
        self._selected_label.setText(f"Selected: {card.friendly_name}")
        self._install_btn.setEnabled(True)

    def _install_selected(self):
        if not self._selected_card:
            return
        name = self._selected_card.distro_name
        self._install_btn.setEnabled(False)
        worker = LaunchInstallTerminalWorker(name, self)
        worker.done.connect(self._on_install_done)
        self._workers.append(worker)
        worker.start()

    def _on_install_done(self, success: bool, msg: str):
        self._install_btn.setEnabled(True)
        if success:
            InfoBar.success(
                title="Installer Launched", content=msg,
                orient=Qt.Orientation.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=5000, parent=self,
            )
            self.install_launched.emit()
        else:
            InfoBar.error(
                title="Failed to Launch Installer", content=msg,
                orient=Qt.Orientation.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=8000, parent=self,
            )

    # ------------------------------------------------------------------
    # Import-from-file logic
    # ------------------------------------------------------------------

    def _browse_install_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Install Location",
            os.path.expanduser("~"),
        )
        if folder:
            self._import_dir_edit.setText(folder)

    def _browse_tar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select TAR Archive",
            os.path.expanduser("~"),
            "TAR Archive (*.tar);;All Files (*)",
        )
        if path:
            self._import_tar_edit.setText(path)
            self._update_import_btn()

    def _update_import_btn(self):
        name_ok = bool(self._import_name_edit.text().strip())
        tar_ok = bool(self._import_tar_edit.text().strip())
        self._import_btn.setEnabled(name_ok and tar_ok)

    def _run_import(self):
        name = self._import_name_edit.text().strip()
        tar_path = self._import_tar_edit.text().strip()
        install_dir = self._import_dir_edit.text().strip()

        if not install_dir:
            install_dir = os.path.join(os.path.expanduser("~"), "WSL", name)

        self._import_btn.setEnabled(False)
        self._import_status_label.setText("Importing, please wait…")

        worker = ImportDistroWorker(name, install_dir, tar_path, self)
        worker.done.connect(self._on_import_done)
        self._workers.append(worker)
        worker.start()

    def _on_import_done(self, success: bool, msg: str):
        self._import_btn.setEnabled(True)
        self._import_status_label.setText("")
        if success:
            # Clear the form on success
            self._import_name_edit.clear()
            self._import_dir_edit.clear()
            self._import_tar_edit.clear()
            InfoBar.success(
                title="Import Successful", content=msg,
                orient=Qt.Orientation.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=5000, parent=self,
            )
            self.distro_installed.emit()
        else:
            InfoBar.error(
                title="Import Failed", content=msg,
                orient=Qt.Orientation.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=8000, parent=self,
            )

    # ------------------------------------------------------------------
    # Shared error handler
    # ------------------------------------------------------------------

    def _on_error(self, msg: str):
        InfoBar.warning(
            title="Could not fetch distributions", content=msg,
            orient=Qt.Orientation.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=6000, parent=self,
        )

