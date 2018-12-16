[![PyPI version](https://badge.fury.io/py/fhem.svg)](https://badge.fury.io/py/fhem)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/116e9e988d934aaa9cfbfa5b8aef7f78)](https://www.codacy.com/app/dominik.schloesser/python-fhem?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=domschl/python-fhem&amp;utm_campaign=Badge_Grade)
[![License](http://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat)](LICENSE)

# python-fhem

Python FHEM (home automation server) API

Simple API to connect to the FHEM home automation server via sockets or http(s), using the telnet or web port on FHEM with optional SSL (TLS) and password or basicAuth support.

## Installation

### PIP installation (PyPI)

See the [PyPI page](https://pypi.python.org/pypi?:action=display&name=fhem) for additional information about the package.

```bash
pip install [-U] fhem
```

### From source

In ```python-fhem/fhem```:

```bash
pip install [-U] .
```

or, as developer installation, allowing inplace editing:

```bash
pip install [-U] -e .
```

## History

* 0.6.0 (2018-12-16): Enhanced and expanded get-API (Andre0512 [#10](https://github.com/domschl/python-fhem/pull/10)), proprietary logging removed. Breaking changes in API.
* 0.5.5 (2018-08-26): Documentation cleanup, automatic documentation with sphinx.
* 0.5.3 (2018-08-26): Fix syntax in exception handler
* 0.5.2 (2018-06-09): Fix for crash on invalid csrf-return
* 0.5.1 (2018-01-29): Removed call to logging.basicConfig(), since it was unnecessary and causes breakage if other modules use this too. (heilerich [#8](https://github.com/domschl/python-fhem/issues/8))
* 0.5: API cleanup (breaking change!). Removed deprecated functions: sendCmd, sendRcvCmd, getDevState, getDevReading (replaced with PEP8 conform names, s.b.). Renamed parameter ssl= -> use_ssl=
* 0.4.4: Merged python logger support (ChuckMoe, [#6](https://github.com/domschl/python-fhem/commit/25843d79986031cd654f87781f37d1266d0b116b))
* 0.4.3: Merged API extensions for getting time of last reading change (logi85, [#5](https://github.com/domschl/python-fhem/commit/11719b41b29a8c2c6192210e3848d9d8aedc5337))
* 0.4.2: deprecation error message fixed (Ivermue, [#4](https://github.com/domschl/python-fhem/commit/098cd774f2f714267645adbf2ee4556edf426229))
* 0.4.0: csrf token support (FHEM 5.8 requirement)

## Usage

### Set and get transactions

Default telnet connection without password and without encryption:

```python
import logging
import fhem

logging.basicConfig()  # Python 2 needs this, or you won't see errors

# Connect via default protocol telnet, default port 7072:
fh = fhem.Fhem("myserver.home.org")
# Send a command to FHEM (this automatically connects() in case of telnet)
fh.send_cmd("set lamp on")
# Get temperatur of LivingThermometer
temp = fh.get_device_reading("LivingThermometer", "temperature")
# Get a dict of kitchen lights with light on
lights = fh.get_states(group="Kitchen", state="on", device_type="light", value_only=True)
# Get all data of specific tvs
tvs = fh.get(device_type=["LGTV", "STV"])
# Get indoor thermometers with low battery
low = fh.get_readings(name=".*Thermometer", not_room="outdoor", filter={"battery!": "ok"})
```

To connect via telnet with SSL and password:

```python
fh = fhem.Fhem("myserver.home.org", port=7073, use_ssl=True, password='mysecret')
fh.connect()
if fh.connected():
    # Do things
```

To connect via https with SSL and basicAuth:

```python
fh = fhem.Fhem('myserver.home.org', port=8086, protocol='https', loglevel=3,
               cafile=mycertfile, username="myuser", password="secretsauce")
```

### Event queues (currently telnet only)

The library can create an event queue that uses a background thread to receive
and dispatch FHEM events:

```python
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

see: [fhem documentation](https://domschl.github.io/python-fhem/index.html)
