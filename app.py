#!/usr/bin/env python3
"""Entry point: starts the Modbus TCP server and the WebSocket bridge.

A single Modbus TCP endpoint hosts any number of independent simulated
devices, each addressed by its own Modbus unit id. Devices are created
lazily by the WebSocket side the first time a browser connects for a given
unit_id (see devices.py / ws_server.py) -- there's no fixed list to edit.
"""

import logging

from pyModbusTCP.server import ModbusServer

from devices import DeviceRegistry
from ws_data_handler import WsDataHandler

MODBUS_HOST = "0.0.0.0"
MODBUS_PORT = 8502
WS_HOST = "0.0.0.0"
WS_PORT = 8765

logging.basicConfig(level=logging.INFO)
logging.getLogger("pyModbusTCP.server").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


def main() -> None:
    registry = DeviceRegistry()
    data_handler = WsDataHandler(registry, ws_host=WS_HOST, ws_port=WS_PORT)
    modbus_server = ModbusServer(
        host=MODBUS_HOST, port=MODBUS_PORT, data_hdl=data_handler, no_block=True
    )

    modbus_server.start()
    logger.info("modbus server started on %s:%d", MODBUS_HOST, MODBUS_PORT)
    logger.info("waiting for browser clients to connect and register devices...")

    try:
        # Blocks the main thread until interrupted (Ctrl+C).
        data_handler.ws_server.start()
    except KeyboardInterrupt:
        logger.info("shutting down")
    finally:
        modbus_server.stop()


if __name__ == "__main__":
    main()