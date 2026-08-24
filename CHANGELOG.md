# Changelog

All notable changes to this project will be documented in this file.

The format is based loosely on Keep a Changelog and uses semantic versioning for releases.

## [Unreleased]

### Added
- **WSL container support** on the Distributions page, powered by Microsoft's
  `wslc.exe` container CLI (ships with WSL 2.9.3+).
  - Unified Distributions page with an **All / Distros Only / Containers Only** filter.
  - Container cards showing name, image, status, and published-port summary.
  - **Expandable container details** (ID, ports, volumes, environment with masked
    secrets, network, restart policy, created time, and best-effort CPU/memory usage).
  - Container actions: **Start**, **Stop**, **Remove**, and **Logs** viewer.
- Session-mismatch hint: when no containers are visible but another `wslc` session with a
  different elevation exists, an info bar suggests running WSL Commander as administrator (or as a
  normal user) so the containers become visible.
- Explicit Windows AppUserModelID so the app shows its own icon in the taskbar when run from source.
- Graceful degradation: the container filter is hidden with an informational note
  when a compatible WSL version isn't installed.

## [1.1.0] - 2026-06-04

### Added
- Inline **Install** button on the selected distribution card in the install catalogue.
- Color-coded USB device state labels.
- Sorting support for the USB device table.
- USB **Auto-Attach** support, including optional support for unplugged devices.
- Automatic UAC elevation for USB bind and unbind operations when administrator privileges are required.

### Changed
- Improved the USB page workflow for managing shared and attached devices.
- Streamlined the install experience by moving the install action onto the selected catalogue item.
- Updated the README to reflect the latest USB and install features.

### Fixed
- Minor internal cleanup and removal of unused imports.

## [1.0.1] - 2026-03-05

### Added
- Auto-refresh for the distros page after install and import actions.
- Signals to detect launched installs and completed distro imports.

### Changed
- Distros polling behavior now temporarily switches to long-running install-aware polling after catalogue installs.

## [1.0.0] - 2026-02-27

### Added
- Initial public release of WSL Commander.
- WSL distribution management for listing, launching, stopping, removing, exporting, installing, and importing distros.
- USB device listing and sharing support through the USB page.
- Windows build and release workflow with PyInstaller packaging.

