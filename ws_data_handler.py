"""Modbus DataHandler that routes each request to the right simulated
device (by Modbus unit id) and broadcasts PLC writes to the WebSocket
clients watching that same device.

Devices are created by the WebSocket side (see WsServer); this handler only
ever looks devices up. If the PLC polls a unit_id no browser has connected
as yet, it gets a Modbus "gateway path unavailable" exception.
"""

import json
import logging

from pyModbusTCP.constants import EXP_DATA_ADDRESS, EXP_GATEWAY_PATH_UNAVAILABLE, EXP_NONE
from pyModbusTCP.server import DataBank, DataHandler

from devices import DeviceRegistry
from ws_server import WsServer

logger = logging.getLogger(__name__)


class WsDataHandler(DataHandler):
    def __init__(self, registry: DeviceRegistry, ws_host: str = "0.0.0.0", ws_port: int = 8765):
        # DataHandler.__init__ wants *a* DataBank, but we never actually use
        # it: every method below is overridden to dispatch by unit id to the
        # matching per-device bank in `registry` instead.
        super().__init__(data_bank=DataBank())
        self.registry = registry
        self.ws_server = WsServer(registry, host=ws_host, port=ws_port)

    def _bank_for(self, srv_info):
        unit_id = srv_info.recv_frame.mbap.unit_id
        device = self.registry.get(unit_id)
        if device is None:
            logger.warning("PLC request for unit id %d with no simulated device", unit_id)
            return None
        return device.data_bank

    # ---- reads: just forward to the requested device's bank ----

    def read_coils(self, address, count, srv_info):
        bank = self._bank_for(srv_info)
        if bank is None:
            return DataHandler.Return(exp_code=EXP_GATEWAY_PATH_UNAVAILABLE)
        bits_l = bank.get_coils(address, count, srv_info)
        if bits_l is None:
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)
        return DataHandler.Return(exp_code=EXP_NONE, data=bits_l)

    def read_d_inputs(self, address, count, srv_info):
        bank = self._bank_for(srv_info)
        if bank is None:
            return DataHandler.Return(exp_code=EXP_GATEWAY_PATH_UNAVAILABLE)
        bits_l = bank.get_discrete_inputs(address, count, srv_info)
        if bits_l is None:
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)
        return DataHandler.Return(exp_code=EXP_NONE, data=bits_l)

    def read_h_regs(self, address, count, srv_info):
        bank = self._bank_for(srv_info)
        if bank is None:
            return DataHandler.Return(exp_code=EXP_GATEWAY_PATH_UNAVAILABLE)
        words_l = bank.get_holding_registers(address, count, srv_info)
        if words_l is None:
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)
        return DataHandler.Return(exp_code=EXP_NONE, data=words_l)

    def read_i_regs(self, address, count, srv_info):
        bank = self._bank_for(srv_info)
        if bank is None:
            return DataHandler.Return(exp_code=EXP_GATEWAY_PATH_UNAVAILABLE)
        words_l = bank.get_input_registers(address, count, srv_info)
        if words_l is None:
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)
        return DataHandler.Return(exp_code=EXP_NONE, data=words_l)

    # ---- writes: forward + notify only the clients watching this unit ----

    def write_coils(self, address, bits_l, srv_info):
        return self._write_and_notify("set_coils", "setCoils", address, bits_l, srv_info)

    def write_h_regs(self, address, words_l, srv_info):
        return self._write_and_notify(
            "set_holding_registers", "setHoldingRegisters", address, words_l, srv_info
        )

    def _write_and_notify(self, setter_name, event_type, address, value, srv_info):
        bank = self._bank_for(srv_info)
        if bank is None:
            return DataHandler.Return(exp_code=EXP_GATEWAY_PATH_UNAVAILABLE)

        setter = getattr(bank, setter_name)
        if not setter(address, value, srv_info):
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)

        unit_id = srv_info.recv_frame.mbap.unit_id
        event = {"type": event_type, "address": address, "value": value}
        self.ws_server.notify_clients(unit_id, json.dumps(event))
        return DataHandler.Return(exp_code=EXP_NONE)