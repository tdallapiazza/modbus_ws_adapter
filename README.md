# modbus_ws_adapter

This is a python app hosting two services:

1. A modbus server with a large default data_bank 65536 elements on each data sector
2. A websocket server to handle communication from a browser page

A third pary software can connect through modbus (mb_clients) and clients can connect through websocket (ws_clients) to the server.
The beauty is that when the data_bank is altered from a modbus client, all connected ws_clients get notified with the type of
change and the new values. It is also possible for ws_clients to alter the data_bank. In this case, mb_clients can't be notified as the modbus protocole is a pure request/response protocole so the mb_clients must poll the server regularly to get changes.notification

## Websocket protocol
The communication through websocket is fairly easy. The data are axchanges through the JSON format with the following fields:

- type: can be one of the following
  - setCoils
  - setDiscreteInput
- address: this is the first address to alter the data
- value: this must be an array of values (bool or numeric) even if ther is only one element in the array

As an example, to write discrete inputs at address 2 and 3 to "1", the ws_client must send the following JSON data:

{"type":"setDiscteteInputs", "address": 2, "value": [true, true]}

The notification to the ws_clients are following the same protocole. When for instance a mb_client send a "write multiple coils" 
from address 3 to 5 and put the values to "1 0 1" to the modbus server, the ws_clients get notified with the following JSON data:

{"type": "setCoils", "address": 3, "value": [true, false, true]}

## Installation

Then clone this repo and cd to it. Create a python virtual environment.

```bash
python -m venv ./
```

Activate the virtual environment with:

```bash
source ./bin/activate
```

Install the following two packaged with pip:

```bash
pip install websockets pymodbustcp
```
Finally run the app.

```bash
sudo ./bin/python app.py 
```
Where ./bin is where your python venv executable is located. Note that we must run is as root to have access to raw TCP sockets.

## Build and run with Docker
Just issue the following command

```bash
docker compose up
```
The websocket server is listening on port *8765* and the modbus server is listening on port *8502*

## Notice

This script implements just the strict minimum it is absolutely not robust agains clients failurs (wrong protocole or whatever can occure from clients) so it is absolutely not ready for production where we know clients do whatever they want....

## License

[MIT](https://choosealicense.com/licenses/mit/)