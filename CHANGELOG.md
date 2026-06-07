# Changelog

All notable changes to this project will be documented in this file.

The format is based loosely on Keep a Changelog and uses semantic versioning for releases.

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

