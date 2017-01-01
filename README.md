# python-fhem
Python FHEM (home automation server) API

Simple API to connect to the FHEM home automation server via sockets, using
the telnet port on FHEM with optional SSL (TLS) and password support.
## Installation:
### PIP installation (PyPI):
```
pip install fhem
```

### From source:
In ```python-fhem/fhem```:

```
pip install .
```
or, as developer installation, allowing inplace editing:
```
pip install -e .
```

## Usage:
### Set and get transactions

```
import fhem

fh = fhem.Fhem("myserver.home.org")
# Send a command to FHEM (this automatically connects())
fh.sendCmd("set lamp on")
# Get a specific reading from a device
temp = fh.getDevReading("LivingThermometer", "temperature")
```
To connect with SSL and password:
```
fh = fhem.Fhem("myserver.home.org", port=7073, bSsl=True, password='mysecret')
fh.connect()
if fh.connected():
    # Do things
```

### Event queues

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
Connects to FHEM via socket communication with optional SSL and password support

### __init__(self, server, port=7072, bSsl=False, password='', loglevel=1)
Instantiate connector object, socket is not opened, use connect() to
actually open the socket.
* server: address of FHEM server
* port: telnet port of server
* bSsl: boolean for SSL (TLS)
* passord: (global) telnet password
* loglevel: 0: no log, 1: errors, 2: info, 3: debug
### close(self)
Closes socket connection.
connect(self)
create socket connection to server
connected(self)
Returns True if socket is connected to server.
### getDevReading(self, dev, reading, timeout=0.1)
Get a specific reading from a FHEM device
* dev: FHEM device
* reading: name of FHEM reading
* timeout: timeout for reply
### getDevReadings(self, dev, readings, timeout=0.1)
Get a list of readings for one FHEM device
* dev: FHEM device
* readings: array of FHEM reading names
* timeout: timeout for reply
### getDevState(self, dev, timeout=0.1)
Get all FHEM device properties as JSON object
* dev: FHEM device name
* timeout: timeout for reply
### getFhemState(self, timeout=0.1)
Get FHEM state of all devices, returns a large JSON object with
every single FHEM device and reading state
* timeout: timeout for reply
### logging(self, level)
Set logging level,
* level: 0: no log, 1: errors, 2: info, 3: debug
### recvNonblocking(self, timeout=0.1)
Receives from server, if data available. Returns directly, if no
data is available.
* timeout: timeout in seconds
### send(self, buf)
Sends a buffer to server
* buf: binary buffer
### sendCmd(self, msg)
Sends a comamnd to server,
is appended.
* msg: string with FHEM command, e.g. 'set lamp on'
### sendRcvCmd(self, msg, timeout=0.1, blocking=True)
Sends a command to the server and waits for an immediate reply.
* msg: FHEM command (NL is appended)
* timeout: waiting time for reply
* blocking: on True: use blocking socket communication (bool)


## class FhemEventQueue()
Creates a thread that listens to FHEM events and dispatches them to a Python queue.

###__init__(self, server, que, port=7072, bSsl=False, password='', filterlist=None, timeout=0.1, eventtimeout=60, serverregex=None, loglevel=1)
* server: FHEM server address
* que: Python Queue object, receives FHEM events as dictionaries
* port: FHEM telnet port
* port: telnet port of server
* bSsl: boolean for SSL (TLS)
* passord: (global) telnet password
* filterlist: array of filter dictionaires [{"dev"="lamp1"},
{"dev"="livingtemp", "reading"="temperature"}]. A
filter dictionary can contain devstate (type of FHEM device), dev (FHEM
device name) and/or reading conditions.
The filterlist works on client side.
* timeout: internal timeout for socket receive (should be short)
* eventtimeout: larger timeout for server keep-alive messages
* serverregex: FHEM regex to restrict event messages on server
side.
* loglevel: 0: no log, 1: errors, 2: info, 3: debug
### close(self)
Stop event thread and close socket. Note: The thread is stopped asynchronously upon completion of current activity.
