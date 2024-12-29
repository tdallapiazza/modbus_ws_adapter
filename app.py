#!/usr/bin/env python3

import logging
from ws_dataHandler import WsDataHandler

from pyModbusTCP.server import ModbusServer


# init logging
logging.basicConfig()
# logging setup
logging.getLogger('pyModbusTCP.server').setLevel(logging.DEBUG)

# start modbus server
dataHandler = WsDataHandler()
modbus_server = ModbusServer(host="0.0.0.0", port=8502, data_hdl=dataHandler, no_block=True)
modbus_server.start()
print("modbus server started.")

# now start the websocket
dataHandler.ws_server.start()