"""Modbus DataHandler that broadcasts write events to WebSocket clients.

The PLC (Modbus master) writes to coils and holding registers; whenever it
does, we mirror that write out to every connected browser over WebSocket so
the UI can stay in sync.
"""

import json
import logging

from pyModbusTCP.constants import EXP_DATA_ADDRESS, EXP_NONE
from pyModbusTCP.server import DataHandler

from ws_server import WsServer

logger = logging.getLogger(__name__)


class WsDataHandler(DataHandler):
    def __init__(self, ws_host: str = "0.0.0.0", ws_port: int = 8765):
        super().__init__()
        self.ws_server = WsServer(self.data_bank, host=ws_host, port=ws_port)

    def write_coils(self, address, bits_l, srv_info):
        """Called by the Modbus server when the PLC writes coils."""
        return self._write_and_notify(
            setter=self.data_bank.set_coils,
            event_type="setCoils",
            address=address,
            value=bits_l,
            srv_info=srv_info,
        )

    def write_h_regs(self, address, words_l, srv_info):
        """Called by the Modbus server when the PLC writes holding registers."""
        return self._write_and_notify(
            setter=self.data_bank.set_holding_registers,
            event_type="setHoldingRegisters",
            address=address,
            value=words_l,
            srv_info=srv_info,
        )

    def _write_and_notify(self, setter, event_type, address, value, srv_info):
        if not setter(address, value, srv_info):
            logger.error("failed to write %s at address %d", event_type, address)
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)

        event = {"type": event_type, "address": address, "value": value}
        self.ws_server.notify_clients(json.dumps(event))
        return DataHandler.Return(exp_code=EXP_NONE)