[![PyPI version](https://badge.fury.io/py/fhem.svg)](https://badge.fury.io/py/fhem)
[![Python package](https://github.com/domschl/python-fhem/actions/workflows/python-fhem-test.yaml/badge.svg)](https://github.com/domschl/python-fhem/actions/workflows/python-fhem-test.yaml)
[![License](http://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-stable-blue.svg)](https://domschl.github.io/python-fhem/index.html)

# python-fhem

Python FHEM (home automation server) API

Simple API to connect to the [FHEM home automation server](https://fhem.de/) via sockets or http(s), using the telnet or web port on FHEM with optional SSL (TLS) and password or basicAuth support.

**Note:** Python 2.x deprecation warning. `python-fhem` versions 0.6.x will be the last versions supporting Python 2.x.

## Installation

### PIP installation (PyPI)

See the [PyPI page](https://pypi.python.org/pypi?:action=display&name=fhem) for additional information about the package.

```bash
pip install [-U] fhem
```

### From source

In `python-fhem/fhem`:

Get a copy of README for the install (required by setup.py):

```bash
cp ../README.md .
```

then:

```bash
pip install [-U] .
```

or, as developer installation, allowing inplace editing:

```bash
pip install [-U] -e .
```

## History

* 0.7.0 (2023-08-17): [unpublished] Ongoing: move Travis CI -> Github actions, Python 2.x support removed, modernize python packaging.
* 0.6.6 (2022-11-09): [unpublished] Fix for new option that produces fractional seconds in event data.
* 0.6.5 (2020-03-24): New option `raw_value` for `FhemEventQueue`. Default `False` (old behavior), on `True`, the full, unparsed reading is returned, without looking for a unit.
* 0.6.4 (2020-03-24): Bug fix for [#21](https://github.com/domschl/python-fhem/issues/21), Index out-of-range in event loop background thread for non-standard event formats.  
* 0.6.3 (2019-09-26): Bug fixes for socket connection exceptions [#18](https://github.com/domschl/python-fhem/issues/18) by [TK67](https://forum.fhem.de/index.php/topic,63816.msg968089.html#msg968089) [FHEM forum] and EventQueue crashes in datetime parsing [#19](https://github.com/domschl/python-fhem/issues/19) by party-pansen. Self-test now also covers FhemEventQueue() class.
* 0.6.2 (2019-06-06): Bug fix, get_device_reading() could return additional unrelated readings. [#14](https://github.com/domschl/python-fhem/issues/14). Default blocking mode for telnet has been set to non-blocking. This can be changed with parameter `blocking=True` (telnet only). Use of HTTP(S) is recommended (superior
performance and faster)
* [build environment] (2019-07-22): Initial support for TravisCI automated self-tests.
* 0.6.1 (2018-12-26): New API used telnet non-blocking on get which caused problems (d1nd141, [#12](https://github.com/domschl/python-fhem/issues/12)), fixed
by using blocking telnet i/o.
* 0.6.0 (2018-12-16): Enhanced and expanded get-API (Andre0512 [#10](https://github.com/domschl/python-fhem/pull/10)). See [online documentation](https://domschl.github.io/python-fhem/doc/_build/html/index.html), especially the new get() method for details on the new functionality. Proprietary logging functions marked deprecated. 
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

logging.basicConfig(level=logging.DEBUG)

## Connect via HTTP, port 8083:
fh = fhem.Fhem("myserver.home.org", protocol="http", port=8083)
# Send a command to FHEM (this automatically connects() in case of telnet)
fh.send_cmd("set lamp on")
# Get temperatur of LivingThermometer
temp = fh.get_device_reading("LivingThermometer", "temperature")
# return a dictionary with reading-value and time of last change:
# {'Value': 25.6, 'Time': datetime.datetime(2019, 7, 27, 8, 19, 24)}
print("The living-room temperature is {}, measured at {}".format(temp["Value"], temp["Time"]))
# Output: The living-room temperature is 25.6, measured at 2019-07-27 08:19:24

# Get a dict of kitchen lights with light on:
lights = fh.get_states(group="Kitchen", state="on", device_type="light", value_only=True)
# Get all data of specific tvs
tvs = fh.get(device_type=["LGTV", "STV"])
# Get indoor thermometers with low battery
low = fh.get_readings(name=".*Thermometer", not_room="outdoor", filter={"battery!": "ok"})
# Get temperature readings from all devices that have a temperature reading:
all_temps = fh.get_readings('temperature')
```

HTTPS connection:

```python
fh = fhem.Fhem('myserver.home.org', port=8085, protocol='https')
```

Self-signed certs are accepted (since no `cafile` option is given).

To connect via https with SSL and basicAuth:

```python
fh = fhem.Fhem('myserver.home.org', port=8086, protocol='https',
               cafile=mycertfile, username="myuser", password="secretsauce")
```

If no public certificate `cafile` is given, then self-signed certs are accepted.

### Connect via default protocol telnet, default port 7072: (deprecated)

*Note*: Connection via telnet is not reliable for large requests, which
includes everything that uses wildcard-funcionality.

```python
fh = fhem.Fhem("myserver.home.org")
```

To connect via telnet with SSL and password:

```python
fh = fhem.Fhem("myserver.home.org", port=7073, use_ssl=True, password='mysecret')
fh.connect()
if fh.connected():
    # Do things
```

It is recommended to use HTTP(S) to connect to Fhem instead.

## Event queues (currently telnet only)

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

see: [python-fhem documentation](https://domschl.github.io/python-fhem/index.html)

# References

* [Fhem home automation project page](https://fhem.de/)
* [Fhem server wiki](https://wiki.fhem.de/)
