import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSizePolicy, QSpacerItem, QFileDialog, QGridLayout,
    QPlainTextEdit,
)
from qfluentwidgets import (
    ScrollArea, TitleLabel, SubtitleLabel, BodyLabel,
    PrimaryPushButton, PushButton, ToolButton,
    InfoBar, InfoBarPosition, IndeterminateProgressBar,
    CardWidget, FluentIcon, CaptionLabel,
    MessageBox, MessageBoxBase, SegmentedWidget, StrongBodyLabel,
)

from app.models.container import EntityFilter
from app.workers.wsl_worker import (
    ListInstalledWorker, SetDefaultWorker,
    TerminateDistroWorker, UnregisterDistroWorker,
    LaunchDistroTerminalWorker, ExportDistroWorker,
)
from app.workers.container_worker import (
    ListContainersWorker, StartContainerWorker, StopContainerWorker,
    RemoveContainerWorker, InspectContainerWorker, GetContainerLogsWorker,
    GetContainerStatsWorker, ListSessionsWorker,
)
from app.utils.wslc_locator import is_container_support_available
from app.utils.elevation import is_admin


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


class LogsDialog(MessageBoxBase):
    """A Fluent dialog that shows read-only container logs in monospace."""

    def __init__(self, title: str, logs: str, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)

        self.text = QPlainTextEdit(self)
        self.text.setReadOnly(True)
        self.text.setPlainText(logs)
        self.text.setFont(QFont("Consolas", 9))
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text.setMinimumSize(680, 380)
        self.viewLayout.addWidget(self.text)

        self.yesButton.setText("Close")
        self.cancelButton.hide()
        self.widget.setMinimumWidth(720)


class ContainerCard(CardWidget):
    """An expandable card representing a single WSL container."""

    _PASSWORD_HINTS = ("password", "secret", "token", "key", "passwd", "pwd")

    def __init__(self, container, parent_page, parent=None):
        super().__init__(parent)
        self.container = container
        self.parent_page = parent_page
        self._expanded = False
        self._detail_widget = None
        self._details_loaded = False
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        # Distinguish containers from distros with a subtle accent border.
        self.setStyleSheet(
            "ContainerCard { border-left: 3px solid #0078D4; }"
        )
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(16, 12, 16, 12)
        self._root.setSpacing(10)

        self._root.addLayout(self._build_summary_row())

    def _build_summary_row(self):
        row = QHBoxLayout()
        row.setSpacing(16)

        # Logo
        logo_label = QLabel()
        logo_label.setFixedSize(56, 56)
        logo_label.setScaledContents(True)
        if self.container.logo_path:
            px = QPixmap(self.container.logo_path)
            if not px.isNull():
                logo_label.setPixmap(px)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(logo_label)

        # Info section
        info = QVBoxLayout()
        info.setSpacing(4)

        name_row = QHBoxLayout()
        name_label = SubtitleLabel(self.container.name)
        name_row.addWidget(name_label)
        name_row.addSpacing(8)
        name_row.addWidget(self._status_label())
        name_row.addStretch()
        info.addLayout(name_row)

        image_label = CaptionLabel(f"Image: {self.container.image or 'unknown'}")
        image_label.setStyleSheet("color: gray;")
        info.addWidget(image_label)

        ports_label = CaptionLabel(self.container.port_summary())
        ports_label.setStyleSheet("color: gray;")
        info.addWidget(ports_label)

        row.addLayout(info)
        row.addStretch()

        row.addLayout(self._build_button_grid())
        return row

    def _status_label(self):
        state = self.container.state.lower()
        color = {
            "running": "#107C10",
            "paused": "#C19C00",
        }.get(state, "#797775")
        text = self.container.status or self.container.state or "unknown"
        label = CaptionLabel(f"● {text}")
        label.setStyleSheet(f"color: {color};")
        return label

    def _build_button_grid(self):
        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        BTN_W = 120

        self._details_btn = PushButton("▼ Details")
        self._details_btn.setFixedWidth(BTN_W)
        self._details_btn.clicked.connect(self.toggle_details)
        grid.addWidget(self._details_btn, 0, 0)

        logs_btn = PushButton(FluentIcon.ALIGNMENT, "Logs")
        logs_btn.setFixedWidth(BTN_W)
        logs_btn.clicked.connect(
            lambda: self.parent_page.show_container_logs(self.container)
        )
        grid.addWidget(logs_btn, 0, 1)

        if self.container.is_running:
            toggle_btn = PushButton("Stop")
            toggle_btn.clicked.connect(
                lambda: self.parent_page.stop_container(self.container)
            )
        else:
            toggle_btn = PrimaryPushButton("Start")
            toggle_btn.clicked.connect(
                lambda: self.parent_page.start_container(self.container)
            )
        toggle_btn.setFixedWidth(BTN_W)
        grid.addWidget(toggle_btn, 1, 0)

        remove_btn = PushButton("Remove")
        remove_btn.setFixedWidth(BTN_W)
        remove_btn.clicked.connect(
            lambda: self.parent_page.remove_container(self.container)
        )
        grid.addWidget(remove_btn, 1, 1)

        return grid

    # ------------------------------------------------------------------
    # Expansion
    # ------------------------------------------------------------------
    def toggle_details(self):
        if self._expanded:
            self.collapse()
        else:
            # Ask the page to collapse any other expanded card first.
            self.parent_page.on_container_expanded(self)
            self.expand()

    def expand(self):
        if self._expanded:
            return
        self._expanded = True
        self._details_btn.setText("▲ Details")
        if self._detail_widget is None:
            self._detail_widget = self._build_detail_placeholder()
            self._root.addWidget(self._detail_widget)
        self._detail_widget.setVisible(True)
        if not self._details_loaded:
            self.parent_page.load_container_details(self.container, self)

    def collapse(self):
        if not self._expanded:
            return
        self._expanded = False
        self._details_btn.setText("▼ Details")
        if self._detail_widget is not None:
            self._detail_widget.setVisible(False)

    def _build_detail_placeholder(self):
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(72, 0, 8, 4)
        layout.setSpacing(4)
        self._detail_layout = layout
        loading = CaptionLabel("Loading details…")
        loading.setStyleSheet("color: gray;")
        layout.addWidget(loading)
        return widget

    def _mask_env(self, entry: str) -> str:
        if "=" not in entry:
            return entry
        key, _, _value = entry.partition("=")
        if any(hint in key.lower() for hint in self._PASSWORD_HINTS):
            return f"{key}=***"
        return entry

    def populate_details(self, detail: dict):
        """Render inspect output into the expanded panel."""
        self._details_loaded = True
        if self._detail_widget is None:
            return
        # Clear existing rows.
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._add_detail_line("ID", self.container.id or self.container.short_id)

        ports = self.container.ports
        if ports:
            self._add_detail_section("Ports", [p.display() for p in ports])

        config = detail.get("Config", {}) if isinstance(detail, dict) else {}
        host_config = detail.get("HostConfig", {}) if isinstance(detail, dict) else {}

        mounts = detail.get("Mounts") if isinstance(detail, dict) else None
        if isinstance(mounts, list) and mounts:
            vols = []
            for m in mounts:
                if isinstance(m, dict):
                    src = m.get("Source", m.get("source", ""))
                    dst = m.get("Destination", m.get("destination", ""))
                    vols.append(f"{src}:{dst}" if src else str(dst))
            if vols:
                self._add_detail_section("Volumes", vols)

        env = config.get("Env") if isinstance(config, dict) else None
        if isinstance(env, list) and env:
            self._add_detail_section("Environment", [self._mask_env(e) for e in env])

        network_mode = ""
        if isinstance(host_config, dict):
            network_mode = str(host_config.get("NetworkMode", "") or "")
        if network_mode:
            self._add_detail_line("Network", network_mode)

        restart = ""
        if isinstance(host_config, dict):
            rp = host_config.get("RestartPolicy")
            if isinstance(rp, dict):
                restart = str(rp.get("Name", "") or "")
        if restart:
            self._add_detail_line("Restart", restart)

        if self.container.created:
            self._add_detail_line("Created", self.container.created)

        if self._detail_layout.count() == 0:
            empty = CaptionLabel("No additional details available.")
            empty.setStyleSheet("color: gray;")
            self._detail_layout.addWidget(empty)

    def populate_stats(self, stats: dict):
        """Append a best-effort resource-usage line to the expanded panel."""
        if not stats or self._detail_widget is None or not self._expanded:
            return
        cpu = stats.get("CPUPerc", stats.get("CPU", stats.get("cpu")))
        mem = stats.get("MemUsage", stats.get("Memory", stats.get("memory")))
        parts = []
        if cpu:
            parts.append(f"CPU: {cpu}")
        if mem:
            parts.append(f"Memory: {mem}")
        if parts:
            self._add_detail_line("Resources", "   ".join(parts))

    def show_details_error(self, message: str):
        self._details_loaded = False
        if self._detail_widget is None:
            return
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        err = CaptionLabel(f"Could not load details: {message}")
        err.setStyleSheet("color: #C42B1C;")
        self._detail_layout.addWidget(err)

    def _add_detail_line(self, label: str, value: str):
        row = QHBoxLayout()
        row.setSpacing(6)
        key = StrongBodyLabel(f"{label}:")
        row.addWidget(key)
        val = CaptionLabel(value)
        val.setWordWrap(True)
        row.addWidget(val)
        row.addStretch()
        self._detail_layout.addLayout(row)

    def _add_detail_section(self, label: str, values: list):
        header = StrongBodyLabel(f"{label}:")
        self._detail_layout.addWidget(header)
        for v in values:
            item = CaptionLabel(f"  • {v}")
            item.setWordWrap(True)
            self._detail_layout.addWidget(item)


class DistrosPage(ScrollArea):
    """Page showing all installed WSL distributions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DistrosPage")
        self._workers = []

        # Mixed-entity state
        self._distros = []
        self._containers = []
        self._filter = EntityFilter.ALL
        self._container_support = is_container_support_available()
        self._distros_loaded = False
        self._containers_loaded = not self._container_support
        self._expanded_container_id = None   # preserved across refreshes
        self._session_hint_shown = False     # avoid repeating the hint each refresh

        # Timer used to poll the distro list after a terminal launch so the
        # status badge updates once the distribution transitions to "Running".
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(2000)          # check every 2 s
        self._poll_timer.timeout.connect(self.refresh)
        self._poll_count = 0
        self._POLL_MAX = 15                         # stop after 30 s
        self._last_distro_count = 0                 # used to detect newly installed distros

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

        # Entity filter (only meaningful when container support is available).
        self._filter_bar = SegmentedWidget(self)
        self._filter_bar.addItem(EntityFilter.ALL.value, "All", None)
        self._filter_bar.addItem(EntityFilter.DISTROS_ONLY.value, "Distros Only", None)
        self._filter_bar.addItem(EntityFilter.CONTAINERS_ONLY.value, "Containers Only", None)
        self._filter_bar.setCurrentItem(EntityFilter.ALL.value)
        self._filter_bar.currentItemChanged.connect(self._on_filter_changed)
        filter_row = QHBoxLayout()
        filter_row.addWidget(self._filter_bar)
        filter_row.addStretch()
        self._main_layout.addLayout(filter_row)
        # Hide the filter entirely when containers aren't supported.
        self._filter_bar.setVisible(self._container_support)

        if not self._container_support:
            self._support_note = CaptionLabel(
                "Container support requires WSL 2.9.3 or higher "
                "(run 'wsl --update --pre-release')."
            )
            self._support_note.setStyleSheet("color: gray;")
            self._main_layout.addWidget(self._support_note)

        self._progress = IndeterminateProgressBar(self)
        self._progress.setVisible(False)
        self._main_layout.addWidget(self._progress)

    def _on_filter_changed(self, key: str):
        try:
            self._filter = EntityFilter(key)
        except ValueError:
            self._filter = EntityFilter.ALL
        self._render()

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
        self._distros_loaded = False
        self._containers_loaded = not self._container_support

        worker = ListInstalledWorker(self)
        worker.result.connect(self._on_distros_loaded)
        worker.error.connect(self._on_distros_error)
        worker.finished.connect(self._on_source_finished)
        self._workers.append(worker)
        worker.start()

        if self._container_support:
            cworker = ListContainersWorker(self)
            cworker.result.connect(self._on_containers_loaded)
            cworker.error.connect(self._on_containers_error)
            cworker.finished.connect(self._on_source_finished)
            self._workers.append(cworker)
            cworker.start()

    def _on_source_finished(self):
        if self._distros_loaded and self._containers_loaded:
            self._progress.setVisible(False)

    def start_install_polling(self):
        """Start long-running polling to detect a newly installed distro.

        The catalogue installer runs in an external terminal so we don't know
        when it completes.  Poll every 5 s for up to 10 minutes (120 attempts).
        """
        self._poll_count = 0
        self._POLL_MAX = 120   # 10 min @ 5 s interval
        self._poll_timer.setInterval(5000)
        self._poll_timer.start()

    def _on_distros_loaded(self, distros):
        self._distros = distros
        self._distros_loaded = True
        self._render()

        # Stop polling once we see a running distro, a new distro appeared, or after max attempts
        if self._poll_timer.isActive():
            self._poll_count += 1
            any_running = any(d.state.lower() == "running" for d in distros)
            new_distro_appeared = len(distros) > self._last_distro_count
            if any_running or new_distro_appeared or self._poll_count >= self._POLL_MAX:
                self._poll_timer.stop()
                self._poll_count = 0
                # Restore default polling settings for terminal-launch polling
                self._poll_timer.setInterval(2000)
                self._POLL_MAX = 15

        self._last_distro_count = len(distros)

    def _on_containers_loaded(self, containers):
        self._containers = containers
        self._containers_loaded = True
        self._render()
        # If we found nothing, another (differently-elevated) session may hold
        # the user's containers — check and surface a one-time hint.
        if not containers and not self._session_hint_shown:
            self._check_other_sessions()

    def _check_other_sessions(self):
        worker = ListSessionsWorker(self)
        worker.result.connect(self._on_sessions_loaded)
        self._workers.append(worker)
        worker.start()

    def _on_sessions_loaded(self, sessions):
        # Only hint while our own container list is genuinely empty.
        if self._containers or self._session_hint_shown or len(sessions) < 2:
            return
        app_is_admin = is_admin()
        # Is there a session whose elevation differs from ours and could hold
        # the containers we can't see?
        other = next(
            (s for s in sessions if s.get("is_elevated") != app_is_admin),
            None,
        )
        if other is None:
            return
        self._session_hint_shown = True
        if app_is_admin:
            content = (
                "Containers may be running in a non-elevated session. "
                "Run WSL Commander as your normal user to manage them."
            )
        else:
            content = (
                "Containers may be running in an elevated session. "
                "Run WSL Commander as administrator to manage them."
            )
        InfoBar.warning(
            title="Containers in another session",
            content=content,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=10000,
            parent=self,
        )

    def _on_distros_error(self, msg):
        self._distros_loaded = True
        self._on_error(msg)
        self._render()

    def _on_containers_error(self, msg):
        self._containers_loaded = True
        self._on_error(msg)
        self._render()

    def _render(self):
        """Rebuild the card list from the current distros/containers + filter."""
        self._clear_cards()

        show_distros = self._filter in (EntityFilter.ALL, EntityFilter.DISTROS_ONLY)
        show_containers = (
            self._container_support
            and self._filter in (EntityFilter.ALL, EntityFilter.CONTAINERS_ONLY)
        )

        rendered = False
        if show_distros:
            for d in self._distros:
                self._cards_layout.addWidget(DistroCard(d, self))
                rendered = True

        if show_containers:
            for c in self._containers:
                card = ContainerCard(c, self)
                self._cards_layout.addWidget(card)
                rendered = True
                # Restore expanded state across refreshes.
                if c.id and c.id == self._expanded_container_id:
                    card.expand()

        if not rendered:
            self._cards_layout.addWidget(self._empty_label())

    def _empty_label(self):
        if self._filter == EntityFilter.CONTAINERS_ONLY:
            text = "No containers found. Create one with 'wslc run'."
        elif self._filter == EntityFilter.DISTROS_ONLY:
            text = "No WSL distributions found. Go to the Install tab to add one."
        else:
            text = "No distributions or containers found. Go to the Install tab to add one."
        empty = BodyLabel(text)
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return empty

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
        worker.done.connect(self._on_launch_done)
        self._workers.append(worker)
        worker.start()

    # ------------------------------------------------------------------
    # Container actions
    # ------------------------------------------------------------------
    def start_container(self, container):
        worker = StartContainerWorker(container.id, container.name, self)
        worker.done.connect(self._on_action_done)
        self._workers.append(worker)
        worker.start()

    def stop_container(self, container):
        worker = StopContainerWorker(container.id, container.name, self)
        worker.done.connect(self._on_action_done)
        self._workers.append(worker)
        worker.start()

    def remove_container(self, container):
        dlg = MessageBox(
            "Remove Container",
            f"Are you sure you want to remove '{container.name}'?\n"
            "This permanently deletes the container.",
            self,
        )
        if dlg.exec():
            if container.id == self._expanded_container_id:
                self._expanded_container_id = None
            worker = RemoveContainerWorker(
                container.id, container.name, force=container.is_running, parent=self
            )
            worker.done.connect(self._on_action_done)
            self._workers.append(worker)
            worker.start()

    def on_container_expanded(self, card):
        """Ensure only one container card is expanded at a time."""
        self._expanded_container_id = card.container.id
        for i in range(self._cards_layout.count()):
            widget = self._cards_layout.itemAt(i).widget()
            if isinstance(widget, ContainerCard) and widget is not card:
                widget.collapse()

    def load_container_details(self, container, card):
        worker = InspectContainerWorker(container.id, self)
        worker.result.connect(
            lambda cid, detail, c=card: c.populate_details(detail)
        )
        worker.error.connect(
            lambda cid, msg, c=card: c.show_details_error(msg)
        )
        self._workers.append(worker)
        worker.start()

        # Best-effort live resource snapshot for running containers.
        if container.is_running:
            sworker = GetContainerStatsWorker(container.id, self)
            sworker.result.connect(
                lambda cid, stats, c=card: c.populate_stats(stats)
            )
            self._workers.append(sworker)
            sworker.start()

    def show_container_logs(self, container):
        worker = GetContainerLogsWorker(container.id, parent=self)
        worker.result.connect(
            lambda cid, logs, name=container.name: self._show_logs_dialog(name, logs)
        )
        worker.error.connect(lambda cid, msg: self._on_error(msg))
        self._workers.append(worker)
        worker.start()

    def _show_logs_dialog(self, name: str, logs: str):
        dialog = LogsDialog(f"Logs — {name}", logs, self)
        dialog.exec()

    def _on_launch_done(self, success: bool, msg: str):
        if success:
            InfoBar.success(
                title="Success", content=msg,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000, parent=self,
            )
            # Start polling so the status badge updates once the distro is running
            self._poll_count = 0
            self._poll_timer.start()
        else:
            InfoBar.error(
                title="Error", content=msg,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000, parent=self,
            )

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

