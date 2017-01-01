# python-fhem
Python FHEM (home automation server) API

Simple API to connect to the FHEM home automation server via sockets, using
the telnet port on FHEM with optional SSL (TLS) and password support.
## Installation:
In ```python-fhem/fhem```:

```
pip install .
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
