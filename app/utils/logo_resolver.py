import os
import re

# Base directory for distro logos - resolve from project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ASSETS_DIR = os.path.join(_PROJECT_ROOT, "assets", "distros")

_KEYWORD_MAP = [
    ("ubuntu",   "ubuntu.png"),
    ("debian",   "debian.png"),
    ("kali",     "kali.png"),
    ("arch",     "arch.png"),
    ("fedora",   "fedora.png"),
    ("oracle",   "oracle.png"),
    ("opensuse", "opensuse.png"),
    ("suse",     "opensuse.png"),
    ("alma",     "alma.png"),
]

_FALLBACK = "linux.png"


def resolve_logo_path(name: str) -> str:
    """Return the absolute path to the best-matching distro logo PNG."""
    normalized = re.sub(r"[-_.\s]", "", name.lower())
    for keyword, filename in _KEYWORD_MAP:
        if keyword in normalized:
            return os.path.join(_ASSETS_DIR, filename)
    return os.path.join(_ASSETS_DIR, _FALLBACK)

