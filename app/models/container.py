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

        The `wslc` list schema uses numeric enums (`State`, port `Protocol`)
        and epoch timestamps; parsing is centralized here so schema quirks are
        handled in one place.
        """
        cid = str(cls._first(data, "Id", "ID", "id", "ContainerId"))
        names = cls._first(data, "Names", "Name", "names", "name", default="")
        if isinstance(names, list):
            name = names[0] if names else ""
        else:
            name = str(names)
        name = name.lstrip("/").strip()

        image = str(cls._first(data, "Image", "image", "ImageName"))
        raw_state = cls._first(data, "State", "state", default="")
        raw_status = cls._first(data, "Status", "status", default="")
        state = _normalize_state(raw_state, raw_status)
        # `wslc list` provides no human status string; derive one from state so
        # the card shows e.g. "Running" instead of a raw enum value.
        status = str(raw_status) if raw_status else state.capitalize()
        command = str(cls._first(data, "Command", "command", default=""))
        created = _format_created(cls._first(data, "CreatedAt", "Created", "created", default=""))

        ports = cls._parse_ports(cls._first(data, "Ports", "ports", default=[]))

        return cls(
            id=cid,
            name=name or cid[:12],
            image=image,
            state=state,
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
                    host_ip = item.get("BindingAddress",
                                       item.get("HostIp", item.get("host_ip", "")))
                    proto = item.get("Protocol",
                                     item.get("Type", item.get("protocol", "tcp")))
                    result.append(PortMapping(
                        host_ip=str(host_ip or ""),
                        host_port=str(item.get("HostPort", item.get("host_port", "")) or ""),
                        container_port=str(item.get("ContainerPort", item.get("container_port", item.get("PrivatePort", ""))) or ""),
                        protocol=_normalize_protocol(proto),
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


def _normalize_protocol(proto) -> str:
    """Map a port protocol to a lowercase name.

    `wslc list` reports the IANA protocol number (6=tcp, 17=udp); the string
    forms are passed through.
    """
    numeric = {6: "tcp", 17: "udp", 132: "sctp"}
    if isinstance(proto, bool):
        return "tcp"
    if isinstance(proto, int):
        return numeric.get(proto, str(proto))
    text = str(proto).strip().lower()
    if text.isdigit():
        return numeric.get(int(text), text)
    return text or "tcp"


def _normalize_state(state, status="") -> str:
    """Map assorted state/status values to a canonical lowercase state.

    `wslc list` reports `State` as a numeric enum
    (1=created, 2=running, 3=exited); `inspect` reports a string.
    """
    numeric = {0: "unknown", 1: "created", 2: "running", 3: "exited", 4: "paused"}
    if isinstance(state, bool):
        state = ""
    if isinstance(state, int):
        return numeric.get(state, "unknown")

    s = str(state or "").strip().lower()
    if s.isdigit():
        return numeric.get(int(s), "unknown")

    known = ("running", "exited", "created", "paused", "restarting", "dead", "stopped")
    if s in known:
        return s
    text = f"{state} {status}".lower()
    for candidate in known:
        if candidate in text:
            return candidate
    if "up " in text:
        return "running"
    return s or "unknown"


def _format_created(value) -> str:
    """Format a created timestamp (epoch seconds or ISO string) for display."""
    if value in (None, "", 0):
        return ""
    # Epoch seconds (int, or numeric string).
    epoch = None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        epoch = int(value)
    elif isinstance(value, str) and value.isdigit():
        epoch = int(value)
    if epoch is not None:
        try:
            from datetime import datetime
            return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OverflowError, OSError):
            return str(value)
    return str(value)
