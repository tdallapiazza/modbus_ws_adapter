#!/usr/bin/env python
"""WebSocket server bridging browser clients to per-device DataBanks.

Each simulated hardware model is a distinct Modbus unit id. A browser tab
declares which model it represents (and creates it, if it doesn't exist
yet) via the connection URL's query string, e.g.:

    ws://host:8765/?unit_id=2
    ws://host:8765/?unit_id=2&name=conveyor-belt   (optional friendly name)

Multiple tabs can connect with the *same* unit_id to share/view one device;
tabs with different unit_ids get fully isolated, independently-created
devices.
"""

import json
import logging
import threading
from typing import Dict, Set
from urllib.parse import parse_qs, urlparse

from websockets.sync.server import serve

from devices import DeviceRegistry

logger = logging.getLogger(__name__)


class WsServer:
    # Maps the "type" field of an incoming WS message to the DataBank setter
    # it should call.
    _WRITE_HANDLERS = {
        "setDiscreteInputs": "set_discrete_inputs",
        "setCoils": "set_coils",
        "setInputRegisters": "set_input_registers",
        "setHoldingRegisters": "set_holding_registers",
    }

    def __init__(self, registry: DeviceRegistry, host: str = "0.0.0.0", port: int = 8765):
        self.registry = registry
        self.host = host
        self.port = port

        # unit_id -> set of connected clients for that device.
        self._clients: Dict[int, Set] = {}
        # notify_clients() runs on the Modbus server thread while handler()
        # runs on a dedicated thread per client -> both touch self._clients,
        # so access to it must be locked.
        self._clients_lock = threading.Lock()

    @staticmethod
    def _connection_params(path: str):
        query = parse_qs(urlparse(path).query)
        try:
            unit_id = int(query["unit_id"][0])
        except (KeyError, ValueError, IndexError):
            return None, None
        name = query.get("name", [None])[0]
        return unit_id, name

    def handler(self, websocket) -> None:
        unit_id, name = self._connection_params(websocket.request.path)
        if unit_id is None:
            logger.warning("rejecting connection, missing unit_id (path=%r)", websocket.request.path)
            websocket.close(code=1008, reason="missing unit_id")
            return

        try:
            # Creates the device (DataBank + plumbing) on first use for this
            # unit_id; returns the existing one on subsequent connections.
            device = self.registry.get_or_create(unit_id, name=name)
        except ValueError as exc:
            logger.warning("rejecting connection: %s", exc)
            websocket.close(code=1008, reason=str(exc))
            return

        with self._clients_lock:
            self._clients.setdefault(unit_id, set()).add(websocket)
        logger.info("client connected to %r (unit_id=%d)", device.name, unit_id)

        try:
            for raw_message in websocket:
                try:
                    self._handle_message(device.data_bank, raw_message)
                except Exception:
                    logger.exception(
                        "error handling message %r, dropping it but keeping the connection open",
                        raw_message,
                    )
        finally:
            with self._clients_lock:
                self._clients[unit_id].discard(websocket)
            logger.info("client disconnected from %r (unit_id=%d)", device.name, unit_id)

    def _handle_message(self, data_bank, raw_message: str) -> None:
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

        setter = getattr(data_bank, setter_name)
        if setter(address, value):
            logger.info("%s address=%d value=%s -> OK", event_type, address, value)
        else:
            logger.error("failed to write %s at address %d", event_type, address)

    def notify_clients(self, unit_id: int, msg: str) -> None:
        with self._clients_lock:
            clients = list(self._clients.get(unit_id, ()))

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
                    self._clients[unit_id].discard(client)

    def _disconnect_all_clients(self) -> None:
        with self._clients_lock:
            all_clients = [c for clients in self._clients.values() for c in clients]
        if not all_clients:
            return
        logger.info("closing %d open connection(s) so the process can exit...", len(all_clients))
        for client in all_clients:
            try:
                client.close()
            except Exception:
                logger.warning("error closing a client connection", exc_info=True)

    def start(self) -> None:
        with serve(self.handler, self.host, self.port) as server:
            logger.info("websocket server started on %s:%d", self.host, self.port)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                self._disconnect_all_clients()
                raise