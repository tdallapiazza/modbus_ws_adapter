#!/usr/bin/env python
import json
import itertools
from websockets.sync.server import serve
from pyModbusTCP.server import DataBank

class WsServer():
    def __init__(self, data_bank):
        """Constructor

        Modbus server data handler constructor.

        :param data_bank: a reference to custom DefaultDataBank
        :type data_bank: DataBank
        """
        # check data_bank type
        if not isinstance(data_bank, DataBank):
            raise TypeError('data_bank arg is invalid')
        # public
        self.data_bank = data_bank
        self.event = None
        self.clients = set()
    
    def handler(self, websocket):

        # add the client in the clients list
        self.clients.add(websocket)
        print("client added")
        try:
            for message in websocket:
                # Parse a "setDiscreteInput" event from the browser.
                event = json.loads(message)
                match event["type"]:
                    case "setDiscreteInputs":
                        addr = event["address"]
                        value = event["value"]
                        print("updating discrete inputs")
                        update_ok = self.data_bank.set_discrete_inputs(addr, value)
                        if not update_ok:
                            print("could not write values in data_bank")
                    case "setCoils":
                        addr = event["address"]
                        value = event["value"]
                        print("updating coils")
                        update_ok = self.data_bank.set_coils(addr, value)
                        if not update_ok:
                            print("could not write values in data_bank")
                    case _:
                        print("Unknown action type")
        finally:
            self.clients.remove(websocket)
            print("client removed")


    def notify_clients(self,msg):
        print("Notifying clients")
        for client in self.clients:
            client.send(msg)



    def main(self):
        with serve(self.handler, "localhost", 8765) as server:
            print("websocket server started")
            server.serve_forever()
            

    def start(self):
        self.main()
        