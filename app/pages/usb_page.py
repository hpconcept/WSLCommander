from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QHeaderView, QAbstractItemView,
)
from qfluentwidgets import (
    ScrollArea, TitleLabel, BodyLabel, CaptionLabel,
    PrimaryPushButton, PushButton, ToolButton,
    TableWidget, ComboBox, CheckBox,
    InfoBar, InfoBarPosition, IndeterminateProgressBar,
    FluentIcon, CardWidget, SubtitleLabel,
)

from app.workers.usb_worker import (
    ListUsbWorker, BindUsbWorker, AttachUsbWorker, DetachUsbWorker, UnbindUsbWorker,
)
from app.workers.wsl_worker import ListInstalledWorker


class UsbPage(ScrollArea):
    """Page for USB device sharing with WSL distributions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UsbPage")
        self._workers = []
        self._devices = []
        self._distros = []
        self._last_selected_busid: str | None = None  # remember selection across refreshes

        self._content = QWidget()
        self._content.setObjectName("usbContent")
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(30, 20, 30, 20)
        self._layout.setSpacing(14)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setWidget(self._content)
        self.setWidgetResizable(True)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Header
        header = QHBoxLayout()
        title = TitleLabel("USB Device Sharing")
        header.addWidget(title)
        header.addStretch()
        refresh_btn = ToolButton(FluentIcon.SYNC)
        refresh_btn.setToolTip("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        self._layout.addLayout(header)

        hint = BodyLabel(
            "Manage USB devices shared with WSL using usbipd-win. "
            "Binding may require administrator privileges."
        )
        hint.setWordWrap(True)
        self._layout.addWidget(hint)

        self._progress = IndeterminateProgressBar(self)
        self._progress.setVisible(False)
        self._layout.addWidget(self._progress)

        # Distro selector card
        sel_card = CardWidget()
        sel_card.setFixedHeight(70)
        sel_layout = QHBoxLayout(sel_card)
        sel_layout.setContentsMargins(16, 10, 16, 10)
        sel_layout.addWidget(CaptionLabel("Target WSL Distribution:"))
        self._distro_combo = ComboBox()
        self._distro_combo.setPlaceholderText("(default)")
        self._distro_combo.setMinimumWidth(220)
        sel_layout.addWidget(self._distro_combo)

        self._force_check = CheckBox("Force bind")
        self._force_check.setToolTip("Pass --force flag to usbipd bind")
        sel_layout.addWidget(self._force_check)
        sel_layout.addStretch()
        self._layout.addWidget(sel_card)

        # Table
        self._table = TableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Bus ID", "Device", "State", "Actions"])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setMinimumHeight(320)
        self._layout.addWidget(self._table)

        # Action toolbar
        action_bar = QHBoxLayout()
        self._bind_btn = PrimaryPushButton(FluentIcon.LINK, "Bind")
        self._bind_btn.setToolTip("Bind selected device (share it with WSL)")
        self._bind_btn.clicked.connect(self._bind_selected)
        action_bar.addWidget(self._bind_btn)

        self._attach_btn = PushButton(FluentIcon.SHARE, "Attach to WSL")
        self._attach_btn.setToolTip("Attach the bound device to the selected WSL distribution")
        self._attach_btn.clicked.connect(self._attach_selected)
        action_bar.addWidget(self._attach_btn)

        self._detach_btn = PushButton(FluentIcon.REMOVE, "Detach")
        self._detach_btn.setToolTip("Detach device from WSL")
        self._detach_btn.clicked.connect(self._detach_selected)
        action_bar.addWidget(self._detach_btn)

        self._unbind_btn = PushButton(FluentIcon.UNPIN, "Unbind")
        self._unbind_btn.setToolTip("Unbind selected device (stop sharing with WSL)")
        self._unbind_btn.clicked.connect(self._unbind_selected)
        action_bar.addWidget(self._unbind_btn)

        action_bar.addStretch()
        self._layout.addLayout(action_bar)

    def refresh(self):
        self._progress.setVisible(True)
        # Load USB devices
        usb_w = ListUsbWorker(self)
        usb_w.result.connect(self._on_usb_loaded)
        usb_w.error.connect(self._on_usb_error)
        self._workers.append(usb_w)
        usb_w.start()

        # Load WSL distros for combo
        wsl_w = ListInstalledWorker(self)
        wsl_w.result.connect(self._on_distros_loaded)
        wsl_w.finished.connect(lambda: self._progress.setVisible(False))
        self._workers.append(wsl_w)
        wsl_w.start()

    def _on_distros_loaded(self, distros):
        self._distros = distros
        self._distro_combo.clear()
        self._distro_combo.addItem("(default)")
        for d in distros:
            self._distro_combo.addItem(d.name)

    def _on_usb_loaded(self, devices):
        self._devices = devices
        self._table.setRowCount(0)
        for row, dev in enumerate(devices):
            self._table.insertRow(row)
            from PyQt6.QtWidgets import QTableWidgetItem
            self._table.setItem(row, 0, QTableWidgetItem(dev.busid))
            self._table.setItem(row, 1, QTableWidgetItem(dev.description))
            state_item = QTableWidgetItem(dev.state)
            # Colour-code state
            from PyQt6.QtGui import QColor
            state_lower = dev.state.lower()
            if "attached" in state_lower:
                state_item.setForeground(QColor("#107C10"))
            elif "shared" in state_lower or "bound" in state_lower:
                state_item.setForeground(QColor("#0078D4"))
            self._table.setItem(row, 2, state_item)
            # Empty actions column (handled via toolbar)
            self._table.setItem(row, 3, QTableWidgetItem(""))
        self._table.resizeRowsToContents()

        # Restore the previously selected device (if it still exists after refresh)
        if self._last_selected_busid:
            for row, dev in enumerate(self._devices):
                if dev.busid == self._last_selected_busid:
                    self._table.selectRow(row)
                    break

    def _on_usb_error(self, msg):
        InfoBar.warning(
            title="USB Warning",
            content=msg,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=6000,
            parent=self,
        )

    def _selected_device(self):
        rows = self._table.selectedItems()
        if not rows:
            InfoBar.warning(
                title="No selection",
                content="Please select a USB device from the table first.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
            return None
        row = self._table.currentRow()
        if row < len(self._devices):
            dev = self._devices[row]
            self._last_selected_busid = dev.busid  # remember for post-refresh restore
            return dev
        return None

    def _selected_distro(self) -> str:
        text = self._distro_combo.currentText()
        if text == "(default)" or not text:
            return ""
        return text

    def _bind_selected(self):
        dev = self._selected_device()
        if not dev:
            return
        force = self._force_check.isChecked()
        worker = BindUsbWorker(dev.busid, force=force, parent=self)
        worker.done.connect(self._on_action_done)
        self._workers.append(worker)
        worker.start()

    def _attach_selected(self):
        dev = self._selected_device()
        if not dev:
            return
        distro = self._selected_distro()
        worker = AttachUsbWorker(dev.busid, distro=distro, parent=self)
        worker.done.connect(self._on_action_done)
        self._workers.append(worker)
        worker.start()

    def _detach_selected(self):
        dev = self._selected_device()
        if not dev:
            return
        worker = DetachUsbWorker(dev.busid, parent=self)
        # After detach the device re-enumerates at USB level; delay the refresh
        # so usbipd has time to update its device list before we query it.
        worker.done.connect(lambda ok, msg: self._on_action_done(ok, msg, refresh_delay_ms=3000))
        self._workers.append(worker)
        worker.start()

    def _unbind_selected(self):
        dev = self._selected_device()
        if not dev:
            return
        worker = UnbindUsbWorker(dev.busid, parent=self)
        worker.done.connect(self._on_action_done)
        self._workers.append(worker)
        worker.start()

    def _on_action_done(self, success: bool, msg: str, refresh_delay_ms: int = 0):
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
                duration=6000, parent=self,
            )
        if refresh_delay_ms > 0:
            QTimer.singleShot(refresh_delay_ms, self.refresh)
        else:
            self.refresh()

