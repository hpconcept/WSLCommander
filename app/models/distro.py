from dataclasses import dataclass, field


@dataclass
class Distro:
    name: str
    state: str          # "Running", "Stopped"
    version: str        # "1" or "2"
    is_default: bool = False
    logo_path: str = ""

