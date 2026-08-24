from dataclasses import dataclass, field
from enum import Enum
from typing import List


class EntityType(Enum):
    """Distinguishes the kind of entity rendered on the Distributions page."""
    DISTRO = "distro"
    CONTAINER = "container"


class EntityFilter(Enum):
    """Filter states for the unified Distributions page."""
    ALL = "all"
    DISTROS_ONLY = "distros"
    CONTAINERS_ONLY = "containers"


@dataclass
class PortMapping:
    """A published container port mapping (host <-> container)."""
    host_ip: str = ""
    host_port: str = ""
    container_port: str = ""
    protocol: str = "tcp"

    def display(self) -> str:
        host = f"{self.host_ip}:" if self.host_ip and self.host_ip not in ("0.0.0.0", "::") else ""
        if self.host_port:
            return f"{host}{self.host_port}->{self.container_port}/{self.protocol}"
        return f"{self.container_port}/{self.protocol}"


@dataclass
class VolumeMapping:
    """A container volume / bind mount."""
    source: str = ""
    destination: str = ""
    mode: str = ""

    def display(self) -> str:
        base = f"{self.source}:{self.destination}" if self.source else self.destination
        return f"{base} ({self.mode})" if self.mode else base


@dataclass
class Container:
    """A WSL container as reported by `wslc list` / `wslc inspect`."""
    id: str
    name: str
    image: str = ""
    state: str = ""             # "running", "exited", "created", "paused"
    status: str = ""           # human-readable, e.g. "Up 2 minutes"
    command: str = ""
    created: str = ""
    ports: List[PortMapping] = field(default_factory=list)
    volumes: List[VolumeMapping] = field(default_factory=list)
    env: List[str] = field(default_factory=list)
    network: str = ""
    restart_policy: str = ""
    logo_path: str = ""

    @property
    def is_running(self) -> bool:
        return self.state.lower() == "running"

    @property
    def short_id(self) -> str:
        return self.id[:12] if self.id else ""

    def port_summary(self) -> str:
        if not self.ports:
            return "No published ports"
        return "  ".join(p.display() for p in self.ports)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    @staticmethod
    def _first(data: dict, *keys, default=""):
        """Return the first present, non-None value among ``keys``.

        `wslc`'s JSON field names may differ slightly by version; centralizing
        lookups here means schema surprises are fixed in one place.
        """
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
        return default

    @classmethod
    def from_json(cls, data: dict) -> "Container":
        """Build a Container from a single `wslc list --format json` entry.

        Defensive against field-name variation; see item 15 (verify against a
        live `wslc list --format json`).
        """
        cid = str(cls._first(data, "Id", "ID", "id", "ContainerId"))
        names = cls._first(data, "Names", "Name", "names", "name", default="")
        if isinstance(names, list):
            name = names[0] if names else ""
        else:
            name = str(names)
        name = name.lstrip("/").strip()

        image = str(cls._first(data, "Image", "image", "ImageName"))
        state = str(cls._first(data, "State", "state", "Status", default=""))
        status = str(cls._first(data, "Status", "status", default=""))
        command = str(cls._first(data, "Command", "command", default=""))
        created = str(cls._first(data, "CreatedAt", "Created", "created", default=""))

        ports = cls._parse_ports(cls._first(data, "Ports", "ports", default=[]))

        return cls(
            id=cid,
            name=name or cid[:12],
            image=image,
            state=_normalize_state(state, status),
            status=status,
            command=command,
            created=created,
            ports=ports,
        )

    @staticmethod
    def _parse_ports(raw) -> List[PortMapping]:
        result: List[PortMapping] = []
        if not raw:
            return result
        # Structured list of dicts.
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    result.append(PortMapping(
                        host_ip=str(item.get("HostIp", item.get("host_ip", "")) or ""),
                        host_port=str(item.get("HostPort", item.get("host_port", "")) or ""),
                        container_port=str(item.get("ContainerPort", item.get("container_port", item.get("PrivatePort", ""))) or ""),
                        protocol=str(item.get("Protocol", item.get("Type", item.get("protocol", "tcp"))) or "tcp"),
                    ))
                elif isinstance(item, str):
                    result.extend(Container._parse_port_string(item))
            return result
        # Comma-separated string form, e.g. "0.0.0.0:8080->80/tcp".
        if isinstance(raw, str):
            for chunk in raw.split(","):
                result.extend(Container._parse_port_string(chunk))
        return result

    @staticmethod
    def _parse_port_string(text: str) -> List[PortMapping]:
        text = text.strip()
        if not text:
            return []
        host_ip = host_port = ""
        proto = "tcp"
        container_part = text
        if "->" in text:
            host_side, container_part = text.split("->", 1)
            host_side = host_side.strip()
            if ":" in host_side:
                host_ip, host_port = host_side.rsplit(":", 1)
            else:
                host_port = host_side
        container_part = container_part.strip()
        if "/" in container_part:
            container_port, proto = container_part.split("/", 1)
        else:
            container_port = container_part
        return [PortMapping(
            host_ip=host_ip.strip(),
            host_port=host_port.strip(),
            container_port=container_port.strip(),
            protocol=proto.strip() or "tcp",
        )]


def _normalize_state(state: str, status: str) -> str:
    """Map assorted state/status strings to a canonical lowercase state."""
    s = (state or "").lower()
    known = ("running", "exited", "created", "paused", "restarting", "dead", "stopped")
    if s in known:
        return "running" if s == "running" else s
    text = f"{state} {status}".lower()
    for candidate in known:
        if candidate in text:
            return candidate
    if "up " in text:
        return "running"
    return s or "unknown"
