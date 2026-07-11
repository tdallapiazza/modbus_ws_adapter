"""Registry of simulated hardware models, keyed by Modbus unit id.

Unlike a static config, devices are NOT declared up front. A device (its
DataBank + identity) is created lazily, the first time a browser opens a
WebSocket connection for a given unit_id (see WsServer.handler). The Modbus
side only ever *reads* the registry -- it never creates a device on its
own, since a PLC polling a unit_id nobody has simulated yet should get a
proper Modbus error, not a freshly-spun-up empty device.

Note: this registry never evicts devices, so it grows for as long as the
process runs / for every distinct unit_id ever used. That's fine for a
small, trusted set of simulated models; if unit_ids are numerous or
short-lived in your deployment, add eviction (e.g. drop a device when its
last WebSocket client disconnects) or a max-devices guard.
"""

import logging
import threading
from typing import Dict, NamedTuple, Optional

from pyModbusTCP.server import DataBank

logger = logging.getLogger(__name__)

MIN_UNIT_ID = 0
MAX_UNIT_ID = 255


class Device(NamedTuple):
    unit_id: int
    name: str
    data_bank: DataBank


class DeviceRegistry:
    """Holds one isolated DataBank per unit id, created on demand."""

    def __init__(self):
        self._devices: Dict[int, Device] = {}
        self._lock = threading.Lock()

    def get(self, unit_id: int) -> Optional[Device]:
        """Read-only lookup used by the Modbus side. Never creates a device."""
        with self._lock:
            return self._devices.get(unit_id)

    def get_or_create(self, unit_id: int, name: Optional[str] = None) -> Device:
        """Used by the WebSocket side: lazily creates a Device (and its
        DataBank) the first time a browser connects for this unit_id.
        Returns the existing device if one is already registered.
        """
        if not (MIN_UNIT_ID <= unit_id <= MAX_UNIT_ID):
            raise ValueError(f"unit_id must be between {MIN_UNIT_ID} and {MAX_UNIT_ID}")

        with self._lock:
            device = self._devices.get(unit_id)
            if device is None:
                device = Device(
                    unit_id=unit_id,
                    name=name or f"model-{unit_id}",
                    data_bank=DataBank(),
                )
                self._devices[unit_id] = device
                logger.info("created simulated device unit_id=%d name=%r", unit_id, device.name)
            return device

    def __iter__(self):
        with self._lock:
            return iter(list(self._devices.values()))