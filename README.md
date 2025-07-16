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

{"type":"setDiscreteInputs", "address": 2, "value": [true, true]}

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

You can also try a working docker image with just issuing

```bash
docker run -d -p 8765:8765 -p 8502:8502 thomasdallapiazza/modbus_ws_proxy
```

## Create an all in one executable
Use pyinstaller to produce an all in one executable file (can be distributed).

First install pyinstaller:

```bash
pip install pyinstaller
```

The run the pyinstaller once:

```bash
pyinstaller --onefile app.py
```

This will create a "app.spec" file together with a build and dist folder. Modify the app.spec file to include the icon:

```
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='./icon.ico',
)
```

Then run the pyinstaller once again but withe the app.spec file as a target:

```bash
pyinstaller app.spec
```

The executable can be found in the "dist" folder ready to be distributed.

## Notice

This script implements just the strict minimum it is absolutely not robust agains clients failurs (wrong protocole or whatever can occure from clients) so it is absolutely not ready for production where we know clients do whatever they want....

## License

[MIT](https://choosealicense.com/licenses/mit/)
