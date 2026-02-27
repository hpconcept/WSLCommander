from dataclasses import dataclass


@dataclass
class UsbDevice:
    busid: str
    description: str
    state: str          # "Not shared", "Shared", "Attached", etc.

