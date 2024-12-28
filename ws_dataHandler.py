from pyModbusTCP.constants import (EXP_DATA_ADDRESS, EXP_NONE)
from pyModbusTCP.server import DataHandler
from ws_server import WsServer
import json

class WsDataHandler(DataHandler):
    # Constructor 
    def __init__(self): 
        super().__init__()  # Call parent constructor
        self.ws_server = WsServer(self.data_bank)

    # Override write_coils method
    def write_coils(self, address, bits_l, srv_info):
        """Call by server for writing in the coils space

        :param address: start address
        :type address: int
        :param bits_l: list of boolean to write
        :type bits_l: list
        :param srv_info: some server info
        :type srv_info: ModbusServer.ServerInfo
        :rtype: Return
        """
        # write bits to DataBank
        update_ok = self.data_bank.set_coils(address, bits_l, srv_info)
        # return DataStatus to server
        if update_ok:
            event = {
                "type": "setCoils",
                "address": address,
                "value": bits_l,
            }
            self.ws_server.notify_clients(json.dumps(event))
            return DataHandler.Return(exp_code=EXP_NONE)
        else:
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)