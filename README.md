[![PyPI version](https://badge.fury.io/py/fhem.svg)](https://badge.fury.io/py/fhem)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/116e9e988d934aaa9cfbfa5b8aef7f78)](https://www.codacy.com/app/dominik.schloesser/python-fhem?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=domschl/python-fhem&amp;utm_campaign=Badge_Grade)
# python-fhem
Python FHEM (home automation server) API

Simple API to connect to the FHEM home automation server via sockets or http(s), using the telnet or web port on FHEM with optional SSL (TLS) and password or basicAuth support.

## Installation:
### PIP installation (PyPI):
See the [PyPI page](https://pypi.python.org/pypi?:action=display&name=fhem) for additional information about the package.
```
pip install [-U] fhem
```

### From source:
In ```python-fhem/fhem```:

```
pip install [-U] .
```
or, as developer installation, allowing inplace editing:
```
pip install [-U] -e .
```


## History
0.5: API cleanup
sendCmd, sendRcvCmd, getDevState, getDevReading
ssl= -> use_ssl=

0.4.4: Merged python logger support (ChuckMoe, [#6](https://github.com/domschl/python-fhem/commit/25843d79986031cd654f87781f37d1266d0b116b))

0.4.3: Merged API extensions for getting time of last reading change (logi85, [#5](https://github.com/domschl/python-fhem/commit/11719b41b29a8c2c6192210e3848d9d8aedc5337))

0.4.2: deprecation error message fixed (Ivermue, [#4](https://github.com/domschl/python-fhem/commit/098cd774f2f714267645adbf2ee4556edf426229))

0.4.0: csrf token support (FHEM 5.8 requirement)


## Usage:
### Set and get transactions

Default telnet connection without password and without encryption:
```
import fhem

# Connect via default protocol telnet, default port 7072:
fh = fhem.Fhem("myserver.home.org")
# Send a command to FHEM (this automatically connects() in case of telnet)
fh.send_cmd("set lamp on")
# Get a specific reading from a device
temp = fh.get_dev_reading("LivingThermometer", "temperature")
```
To connect via telnet with SSL and password:
```
fh = fhem.Fhem("myserver.home.org", port=7073, use_ssl=True, password='mysecret')
fh.connect()
if fh.connected():
    # Do things
```
To connect via https with SSL and basicAuth:
```
fh = fhem.Fhem('myserver.home.org', port=8086, protocol='https', loglevel=3,
               cafile=mycertfile, username="myuser", password="secretsauce")
```

### Event queues (currently telnet only)

The library can create an event queue that uses a background thread to receive
and dispatch FHEM events:
```
try:
    # Python 3.x
    import queue
except:
    # Python 2.x
    import Queue as queue
import fhem

que = queue.Queue()
fhemev = fhem.FhemEventQueue("myserver.home.org", que)

while True:
    ev = que.get()
    # FHEM events are parsed into a Python dictionary:
    print(ev)
    que.task_done()
```

# Documentation
## class Fhem()
Connects to FHEM via socket/https(s) communication with optional SSL and password support

### Fhem(server, protocol='telnet', port=7072, use_ssl=False, username='', password='', cafile='', loglevel=1)
Instantiate connector object, socket is not opened, use connect() to
actually open the socket.
* server: address of FHEM server
* param port: telnet/http(s) port of server
* protocol: 'telnet', 'http' or 'https'
* use_ssl: boolean for SSL (TLS) [https as protocol sets use_ssl=True]
* cafile: path to public certificate of your root authority, if
  left empty, https protocol will ignore certificate checks.
* username: username for http(s) basicAuth validation
* password: (global) telnet or http(s) password
* csrf: (http(s)) use csrf token (FHEM 5.8 and newer), default True
* loglevel: 0: no log, 1: errors, 2: info, 3: debug

### close()
Closes socket connection.

### connect()
create connection to server

### connected()
Telnet: Returns True if socket is connected to server.

### get_dev_reading(dev, reading, timeout=0.1)
Get a specific reading from a FHEM device
* dev: FHEM device
* reading: name of FHEM reading
* timeout: timeout for reply

### get_dev_readings(dev, readings, timeout=0.1)
Get a list of readings for one FHEM device
* dev: FHEM device
* readings: array of FHEM reading names
* timeout: timeout for reply

### get_dev_reading_time(dev, reading, timeout=0.1)
Get datetime of last change of a reading from a FHEM device
* dev: FHEM device
* reading: name of FHEM reading
* timeout: timeout for reply

### get_dev_readings_time(dev, readings, timeout=0.1)
Get a list of datetimes of last change of readings for one FHEM device
* dev: FHEM device
* readings: array of FHEM reading names
* timeout: timeout for reply

### get_dev_state(dev, timeout=0.1)
Get all FHEM device properties as JSON object
* dev: FHEM device name
* timeout: timeout for reply

### get_fhem_state(timeout=0.1)
Get FHEM state of all devices, returns a large JSON object with
every single FHEM device and reading state
* timeout: timeout for reply

### logging(level)
Set logging level,
* level: 0: no log, 1: errors, 2: info, 3: debug

### send(buf)
Sends a buffer to server
* buf: binary buffer

### send_cmd(msg)
Sends a command to server, NL is appended.
* msg: string with FHEM command, e.g. ```'set lamp on'```

### send_recv_cmd(msg, timeout=0.1, blocking=True)
Sends a command to the server and waits for an immediate reply.
* msg: FHEM command (NL is appended)
* timeout: waiting time for reply
* blocking: on True: use blocking socket communication (bool)


## class FhemEventQueue()
Creates a thread that listens to FHEM events and dispatches them to a Python queue.

### FhemEventQueue(server, que, port=7072, protocol='telnet', use_ssl=False, username='', password='', cafile='', filterlist=None, timeout=0.1, eventtimeout=60, serverregex=None, loglevel=1)
* server: FHEM server address
* que: Python Queue object, receives FHEM events as dictionaries
* port: FHEM telnet port
* protocol: 'telnet' (or not yet implemented: http, https)
* use_ssl: boolean for SSL (TLS)
* username: for http(s) basicAuth
* password: (global) telnet or http(s) basicAuth password
* cafile: path to a certificate authority PEM file, if ommitted server
SLL certificate is not checked.
* filterlist: array of filter dictionaires ```[{"dev"="lamp1"}, {"dev"="livingtemp", "reading"="temperature"}]```.
A filter dictionary can contain devstate (type of FHEM device), dev (FHEM device name) and/or reading conditions.
The filterlist works on client side.
* timeout: internal timeout for socket receive (should be short)
* eventtimeout: larger timeout for server keep-alive messages
* serverregex: FHEM regex to restrict event messages on server side.
* loglevel: 0: no log, 1: errors, 2: info, 3: debug

### close()
Stop event thread and close socket. Note: The thread is stopped asynchronously upon completion of current activity.

