# WSL Commander v1.1.0

Release date: 2026-06-04

This release builds on `v1.0.1` with a strong focus on USB device management and a cleaner distro install experience.

---

## Highlights

- Improved USB device management with color-coded states and sortable device lists
- Added USB auto-attach support, including support for unplugged devices
- Added automatic UAC elevation for USB bind and unbind operations
- Streamlined distro installation with an inline Install button in the catalogue

## Changes

### USB sharing improvements

- Added color-coded USB device states to make attached, shared, and unavailable devices easier to distinguish at a glance.
- Added sorting support to the USB device table.
- Added an **Auto-Attach** action so supported USB devices can reconnect to WSL automatically.
- Added optional support for auto-attach when a device is currently unplugged.
- Improved lifecycle handling so auto-attach workers are stopped during detach and page cleanup.
- Added automatic UAC elevation for `usbipd` bind and unbind commands when administrator rights are required.

### Install experience

- Moved the distro install action onto the selected catalogue card with an inline **Install** button.
- Simplified the install flow by removing the separate install action row.

### Maintenance

- Removed unused imports and performed minor internal cleanup.
- Updated USB page screenshot to reflect the new color-coded states and UI improvements.


