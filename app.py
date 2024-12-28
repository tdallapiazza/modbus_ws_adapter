#!/usr/bin/env python3

import threading
import argparse
import logging
from ws_dataHandler import WsDataHandler

from pyModbusTCP.server import ModbusServer


# init logging
logging.basicConfig()
# parse args
parser = argparse.ArgumentParser()
parser.add_argument('-H', '--host', type=str, default='localhost', help='Host (default: localhost)')
parser.add_argument('-p', '--port', type=int, default=502, help='TCP port (default: 502)')
parser.add_argument('-d', '--debug', action='store_true', help='set debug mode')
args = parser.parse_args()
# logging setup
if args.debug:
    logging.getLogger('pyModbusTCP.server').setLevel(logging.DEBUG)

# start modbus server
dataHandler = WsDataHandler()
modbus_server = ModbusServer(host=args.host, port=args.port, data_hdl=dataHandler, no_block=True)
modbus_server.start()
print("modbus server started.")

# now start the websocket
dataHandler.ws_server.start()