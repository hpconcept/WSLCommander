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

## Suggested short release summary

WSL Commander's next update focuses on usability improvements for USB sharing and distro installation. USB device management is now easier with color-coded states, sortable tables, automatic re-attach support, and UAC elevation for privileged actions. The distro catalogue also gets a cleaner inline install experience.

## GitHub release body

WSL Commander `v1.1.0` focuses on usability improvements for USB sharing and distro installation.

### What's new

- Color-coded USB device states
- Sortable USB device table
- USB auto-attach support, including unplugged-device support
- Automatic UAC elevation for USB bind and unbind operations
- Inline Install button on the selected distro card

### Notes

- USB sharing still requires [`usbipd-win`](https://github.com/dorssel/usbipd-win).
- Binding and unbinding USB devices may prompt for administrator approval through Windows UAC.


