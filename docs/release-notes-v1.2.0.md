# WSL Commander v1.2.0

Release date: 2026-08-27

This release brings **WSL container management** to WSL Commander. Containers now live
alongside your distributions on a unified Distributions page, powered by Microsoft's
`wslc.exe` container CLI that ships with WSL 2.9.3+.

---

## Highlights

- Manage WSL containers and distributions together on a single, filterable Distributions page
- Rich, expandable container details with ports, volumes, environment, network, and usage
- Container lifecycle actions: start, stop, remove, and a logs viewer
- Graceful degradation on older WSL versions — the app still manages distributions normally

## Changes

### WSL container support

- Added a unified Distributions page with an **All / Distros Only / Containers Only** filter.
- Added container cards showing name, image, status, and a published-port summary.
- Added **expandable container details** covering ID, ports, volumes, environment (with
  masked secrets), network, restart policy, created time, and best-effort CPU/memory usage.
- Added container actions: **Start**, **Stop**, **Remove**, and a **Logs** viewer.
- Added a session-mismatch hint: when no containers are visible but another `wslc` session
  with a different elevation exists, an info bar suggests running WSL Commander as
  administrator (or as a normal user) so the containers become visible.

### Compatibility & polish

- Added graceful degradation: the container filter is hidden with an informational note
  when a compatible WSL version (2.9.3+) isn't installed.
- Added an explicit Windows AppUserModelID so the app shows its own icon in the taskbar
  when run from source.

### Requirements

- Container management requires **WSL 2.9.3 or higher** (currently a pre-release). Enable it
  with `wsl --update --pre-release` and confirm with `wsl --version`. Without it, WSL
  Commander runs normally and simply hides the container filter.
