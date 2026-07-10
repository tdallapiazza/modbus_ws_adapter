#!/usr/bin/env python
"""WebSocket server bridging browser clients to the Modbus DataBank.

Browser clients simulate the "field side" of the device (discrete inputs,
input registers) and can also force coils/holding registers directly. The
Modbus master (PLC) reads/writes through the normal Modbus TCP port; any
write it makes is relayed to browsers by WsDataHandler via notify_clients().
"""

import json
import logging
import threading

from websockets.sync.server import serve
from pyModbusTCP.server import DataBank

logger = logging.getLogger(__name__)


class WsServer:
    # Maps the "type" field of an incoming WS message to the DataBank setter
    # it should call. Centralizing this avoids a long if/elif ladder and
    # makes it trivial to add new writable spaces later.
    _WRITE_HANDLERS = {
        "setDiscreteInputs": "set_discrete_inputs",
        "setCoils": "set_coils",
        "setInputRegisters": "set_input_registers",
        "setHoldingRegisters": "set_holding_registers",
    }

    def __init__(self, data_bank: DataBank, host: str = "0.0.0.0", port: int = 8765):
        """Constructor

        :param data_bank: a reference to the Modbus server's DataBank
        :type data_bank: DataBank
        :param host: address to bind the WebSocket server to
        :param port: port to bind the WebSocket server to
        """
        if not isinstance(data_bank, DataBank):
            raise TypeError("data_bank arg is invalid")

        self.data_bank = data_bank
        self.host = host
        self.port = port

        self._clients = set()
        # notify_clients() runs on the Modbus server thread while handler()
        # runs on a dedicated thread per client -> both touch self._clients,
        # so access to it must be locked.
        self._clients_lock = threading.Lock()

    def handler(self, websocket) -> None:
        with self._clients_lock:
            self._clients.add(websocket)
        logger.info("client connected (%d total)", len(self._clients))

        try:
            for raw_message in websocket:
                self._handle_message(raw_message)
        finally:
            with self._clients_lock:
                self._clients.discard(websocket)
            logger.info("client disconnected (%d total)", len(self._clients))

    def _handle_message(self, raw_message: str) -> None:
        try:
            event = json.loads(raw_message)
            event_type = event["type"]
            address = event["address"]
            value = event["value"]
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("ignoring malformed message %r: %s", raw_message, exc)
            return

        setter_name = self._WRITE_HANDLERS.get(event_type)
        if setter_name is None:
            logger.warning("unknown event type %r", event_type)
            return

        setter = getattr(self.data_bank, setter_name)
        if not setter(address, value):
            logger.error("failed to write %s at address %d", event_type, address)

    def notify_clients(self, msg: str) -> None:
        with self._clients_lock:
            clients = list(self._clients)

        stale = []
        for client in clients:
            try:
                client.send(msg)
            except Exception:
                logger.warning("failed to notify a client, dropping it", exc_info=True)
                stale.append(client)

        if stale:
            with self._clients_lock:
                for client in stale:
                    self._clients.discard(client)

    def start(self) -> None:
        with serve(self.handler, self.host, self.port) as server:
            logger.info("websocket server started on %s:%d", self.host, self.port)
            server.serve_forever()