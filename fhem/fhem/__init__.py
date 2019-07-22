'''API for FHEM homeautomation server, supporting telnet or HTTP/HTTPS connections with authentication and CSRF-token support.'''
import datetime
import json
import logging
import re
import socket
import ssl
import threading
import time

try:
    # Python 3.x
    from urllib.parse import quote
    from urllib.parse import urlencode
    from urllib.request import urlopen
    from urllib.error import URLError
    from urllib.request import HTTPSHandler
    from urllib.request import HTTPPasswordMgrWithDefaultRealm
    from urllib.request import HTTPBasicAuthHandler
    from urllib.request import build_opener
    from urllib.request import install_opener
except ImportError:
    # Python 2.x
    from urllib import urlencode
    from urllib2 import quote
    from urllib2 import urlopen
    from urllib2 import URLError
    from urllib2 import HTTPSHandler
    from urllib2 import HTTPPasswordMgrWithDefaultRealm
    from urllib2 import HTTPBasicAuthHandler
    from urllib2 import build_opener
    from urllib2 import install_opener

# needs to be in sync with setup.py and documentation (conf.py, branch gh-pages)
__version__ = '0.6.2'

# create logger with 'python_fhem'
# logger = logging.getLogger(__name__)


class Fhem:
    '''Connects to FHEM via socket communication with optional SSL and password
    support'''

    def __init__(self, server, port=7072,
                 use_ssl=False, protocol="telnet", username="", password="", csrf=True,
                 cafile="", loglevel=1):
        '''
        Instantiate connector object.

        :param server: address of FHEM server
        :param port: telnet/http(s) port of server
        :param use_ssl: boolean for SSL (TLS) [https as protocol sets use_ssl=True]
        :param protocol: 'telnet', 'http' or 'https'
        :param username: username for http(s) basicAuth validation
        :param password: (global) telnet or http(s) password
        :param csrf: (http(s)) use csrf token (FHEM 5.8 and newer), default True
        :param cafile: path to public certificate of your root authority, if left empty, https protocol will ignore certificate checks.
        :param loglevel: deprecated, will be removed. Please use standard python logging API with logger 'Fhem'.
        '''
        self.log = logging.getLogger("Fhem")

        validprots = ['http', 'https', 'telnet']
        self.server = server
        self.port = port
        self.ssl = use_ssl
        self.csrf = csrf
        self.csrftoken = ''
        self.username = username
        self.password = password
        self.loglevel = loglevel
        self.connection = False
        self.cafile = cafile
        self.nolog = False
        self.bsock = None
        self.sock = None
        self.https_handler = None

        # Set LogLevel
        # self.set_loglevel(loglevel)

        # Check if protocol is supported
        if protocol in validprots:
            self.protocol = protocol
        else:
            self.log.error("Invalid protocol: {}".format(protocol))

        # Set authenticication values if#
        # the protocol is http(s) or use_ssl is True
        if protocol != "telnet":
            tmp_protocol = "http"
            if (protocol == "https") or (use_ssl is True):
                self.ssl = True
                tmp_protocol = "https"

            self.baseurlauth = "{}://{}:{}/".format(tmp_protocol, server, port)
            self.baseurltoken = "{}fhem".format(self.baseurlauth)
            self.baseurl = "{}fhem?XHR=1&cmd=".format(self.baseurlauth)

            self._install_opener()

    def connect(self):
        '''create socket connection to server (telnet protocol only)'''
        if self.protocol == 'telnet':
            try:
                self.log.debug("Creating socket...")
                if self.ssl:
                    self.bsock = socket.socket(socket.AF_INET,
                                               socket.SOCK_STREAM)
                    self.sock = ssl.wrap_socket(self.bsock)
                    self.log.info("Connecting to {}:{} with SSL (TLS)".format(
                        self.server, self.port))
                else:
                    self.sock = socket.socket(socket.AF_INET,
                                              socket.SOCK_STREAM)
                    self.log.info("Connecting to {}:{} without SSL".format(
                        self.server, self.port))

                self.sock.connect((self.server, self.port))
                self.connection = True
                self.log.info("Connected to {}:{}".format(
                    self.server, self.port))
            except socket.error:
                self.connection = False
                self.log.error("Failed to connect to {}:{}".format(
                    self.server, self.port))
                return

            if self.password != "":
                # time.sleep(1.0)
                # self.send_cmd("\n")
                # prmpt = self._recv_nonblocking(4.0)
                prmpt = self.sock.recv(32000)
                self.log.debug("auth-prompt: {}".format(prmpt))

                self.nolog = True
                self.send_cmd(self.password)
                self.nolog = False
                time.sleep(0.1)

                try:
                    po1 = self.sock.recv(32000)
                    self.log.debug("auth-repl1: {}".format(po1))
                except socket.error:
                    self.log.error("Failed to recv auth reply")
                    self.connection = False
                    return
                self.log.info("Auth password sent to {}".format(self.server))
        else:  # http(s)
            if self.csrf:
                dat = self.send("")
                if dat is not None:
                    dat = dat.decode("UTF-8")
                    stp = dat.find("csrf_")
                    if stp != -1:
                        token = dat[stp:]
                        token = token[:token.find("'")]
                        self.csrftoken = token
                        self.connection = True
                    else:
                        self.log.error(
                            "CSRF token requested for server that doesn't know CSRF")
                else:
                    self.log.error(
                        "No valid answer on send when expecting csrf.")
            else:
                self.connection = True

    def connected(self):
        '''Returns True if socket/http(s) session is connected to server.'''
        return self.connection

    def set_loglevel(self, level):
        '''Set logging level. [Deprecated, will be removed, use python logging.setLevel]

        :param level: 0: critical, 1: errors, 2: info, 3: debug
        '''
        self.log.warning(
            "Deprecation: please set logging levels using python's standard logging for logger 'Fhem'")
        if level == 0:
            self.log.setLevel(logging.CRITICAL)
        elif level == 1:
            self.log.setLevel(logging.ERROR)
        elif level == 2:
            self.log.setLevel(logging.INFO)
        elif level == 3:
            self.log.setLevel(logging.DEBUG)

    def close(self):
        '''Closes socket connection. (telnet only)'''
        if self.protocol == 'telnet':
            if self.connected():
                time.sleep(0.2)
                self.sock.close()
                self.connection = False
                self.log.info("Disconnected from fhem-server")
            else:
                self.log.error("Cannot disconnect, not connected")
        else:
            self.connection = False

    def _install_opener(self):
        self.opener = None
        if self.username != "":
            self.password_mgr = HTTPPasswordMgrWithDefaultRealm()
            self.password_mgr.add_password(None, self.baseurlauth,
                                           self.username, self.password)
            self.auth_handler = HTTPBasicAuthHandler(self.password_mgr)
        if self.ssl is True:
            if self.cafile == "":
                self.context = ssl.create_default_context()
                self.context.check_hostname = False
                self.context.verify_mode = ssl.CERT_NONE
            else:
                self.context = ssl.create_default_context()
                self.context.load_verify_locations(cafile=self.cafile)
                self.context.verify_mode = ssl.CERT_REQUIRED
            self.https_handler = HTTPSHandler(context=self.context)
            if self.username != "":
                self.opener = build_opener(self.https_handler,
                                           self.auth_handler)
            else:
                self.opener = build_opener(self.https_handler)
        else:
            if self.username != "":
                self.opener = build_opener(self.auth_handler)
        if self.opener is not None:
            self.log.debug("Setting up opener on: {}".format(self.baseurlauth))
            install_opener(self.opener)

    def send(self, buf, timeout=10):
        '''Sends a buffer to server

        :param buf: binary buffer'''
        if len(buf) > 0:
            if not self.connected():
                self.log.debug("Not connected, trying to connect...")
                self.connect()
        if self.protocol == 'telnet':
            if self.connected():
                self.log.debug("Connected, sending...")
                try:
                    self.sock.sendall(buf)
                    self.log.info("Sent msg, len={}".format(len(buf)))
                    return None
                except OSError as err:
                    self.log.error(
                        "Failed to send msg, len={}. Exception raised: {}".format(len(buf), err))
                    self.connection = None
                    return None
            else:
                self.log.error(
                    "Failed to send msg, len={}. Not connected.".format(len(buf)))
                return None
        else:  # HTTP(S)
            paramdata = None
            if self.csrf and len(buf) > 0:
                if len(self.csrftoken) == 0:
                    self.log.error("CSRF token not available!")
                    self.connection = False
                else:
                    datas = {'fwcsrf': self.csrftoken}
                    paramdata = urlencode(datas).encode('UTF-8')

            try:
                self.log.debug("Cmd: {}".format(buf))
                cmd = quote(buf)
                self.log.debug("Cmd-enc: {}".format(cmd))

                if len(cmd) > 0:
                    ccmd = self.baseurl + cmd
                else:
                    ccmd = self.baseurltoken

                self.log.info("Request: {}".format(ccmd))
                if ccmd.lower().startswith('http'):
                    ans = urlopen(ccmd, paramdata, timeout=timeout)
                else:
                    self.log.error(
                        "Invalid URL {}, Failed to send msg, len={}, {}".format(ccmd, len(buf), err))
                    return None
                data = ans.read()
                return data
            except URLError as err:
                self.connection = False
                self.log.error(
                    "Failed to send msg, len={}, {}".format(len(buf), err))
                return None
            except socket.timeout as err:
                # Python 2.7 fix
                self.log.error(
                    "Failed to send msg, len={}, {}".format(len(buf), err))
                return None

    def send_cmd(self, msg, timeout=10.0):
        '''Sends a command to server.

        :param msg: string with FHEM command, e.g. 'set lamp on'
        :param timeout: timeout on send (sec).
        '''
        if not self.connected():
            self.connect()
        if not self.nolog:
            self.log.debug("Sending: {}".format(msg))
        if self.protocol == 'telnet':
            if self.connection:
                msg = "{}\n".format(msg)
                cmd = msg.encode('utf-8')
                return self.send(cmd)
            else:
                self.log.error(
                    "Failed to send msg, len={}. Not connected.".format(len(msg)))
                return None
        else:
            return self.send(msg, timeout=timeout)

    def _recv_nonblocking(self, timeout=0.1):
        if not self.connected():
            self.connect()
        data = b''
        if self.connection:
            self.sock.setblocking(False)
            data = b''
            try:
                data = self.sock.recv(32000)
            except socket.error as err:
                self.log.debug(
                    "Exception in non-blocking. Error: {}".format(err))
                time.sleep(timeout)

            wok = 1
            while len(data) > 0 and wok > 0:
                time.sleep(timeout)
                datai = b''

                try:
                    datai = self.sock.recv(32000)
                    if len(datai) == 0:
                        wok = 0
                    else:
                        data += datai
                except socket.error as err:
                    wok = 0
                    self.log.debug(
                        "Exception in non-blocking. Error: {}".format(err))
            self.sock.setblocking(True)
        return data

    def send_recv_cmd(self, msg, timeout=0.1, blocking=False):
        '''
        Sends a command to the server and waits for an immediate reply.

        :param msg: FHEM command (e.g. 'set lamp on')
        :param timeout: waiting time for reply
        :param blocking: (telnet only) on True: use blocking socket communication (bool)
        '''
        data = b''
        if not self.connected():
            self.connect()
        if self.protocol == 'telnet':
            if self.connection:
                self.send_cmd(msg)
                time.sleep(timeout)
                data = []
                if blocking is True:
                    print("BLOCKING!")
                    try:
                        # This causes failures if reply is larger!
                        data = self.sock.recv(64000)
                    except socket.error:
                        self.log.error("Failed to recv msg. {}".format(data))
                        return {}
                else:
                    print("NON_BLOCKING!")
                    data = self._recv_nonblocking(timeout)

                self.sock.setblocking(True)
            else:
                self.log.error(
                    "Failed to send msg, len={}. Not connected.".format(len(msg)))
        else:
            data = self.send_cmd(msg)
            if data is None:
                return None

        if len(data) == 0:
            return {}

        try:
            sdata = data.decode('utf-8')
            jdata = json.loads(sdata)
        except Exception as err:
            self.log.error(
                "Failed to decode json, exception raised. {} {}".format(data, err))
            return {}
        if len(jdata[u'Results']) == 0:
            self.log.error("Query had no result.")
            return {}
        else:
            self.log.info("JSON answer received.")
            return jdata

    def get_dev_state(self, dev, timeout=0.1):
        self.log.warning(
            "Deprecation: use get_device('device') instead of get_dev_state")
        return self.get_device(dev, timeout=timeout, raw_result=True)

    def get_dev_reading(self, dev, reading, timeout=0.1):
        self.log.warning(
            "Deprecation: use get_device_reading('device', 'reading') instead of get_dev_reading")
        return self.get_device_reading(dev, reading, value_only=True, timeout=timeout)

    def getDevReadings(self, dev, reading, timeout=0.1):
        self.log.warning(
            "Deprecation: use get_device_reading('device', ['reading']) instead of getDevReadings")
        return self.get_device_reading(dev, timeout=timeout, value_only=True, raw_result=True)

    def get_dev_readings(self, dev, readings, timeout=0.1):
        self.log.warning(
            "Deprecation: use get_device_reading('device', ['reading']) instead of get_dev_readings")
        return self.get_device_reading(dev, readings, timeout=timeout, value_only=True, raw_result=True)

    def get_dev_reading_time(self, dev, reading, timeout=0.1):
        self.log.warning(
            "Deprecation: use get_device_reading('device', 'reading', time_only=True) instead of get_dev_reading_time")
        return self.get_device_reading(dev, reading, timeout=timeout, time_only=True)

    def get_dev_readings_time(self, dev, readings, timeout=0.1):
        self.log.warning(
            "Deprecation: use get_device_reading('device', ['reading'], time_only=True) instead of get_dev_reading_time")
        return self.get_device_reading(dev, readings, timeout=timeout, time_only=True)

    def getFhemState(self, timeout=0.1):
        self.log.warning(
            "Deprecation: use get() without parameters instead of getFhemState")
        return self.get(timeout=timeout, raw_result=True)

    def get_fhem_state(self, timeout=0.1):
        self.log.warning(
            "Deprecation: use get() without parameters instead of get_fhem_state")
        return self.get(timeout=timeout, raw_result=True)

    @staticmethod
    def _sand_down(value):
        return value if len(value.values()) - 1 else list(value.values())[0]

    @staticmethod
    def _append_filter(name, value, compare, string, filter_list):
        value_list = [value] if isinstance(value, str) else value
        values = ",".join(value_list)
        filter_list.append(string.format(name, compare, values))

    def _response_filter(self, response, arg, value, value_only=None, time_only=None):
        if len(arg) > 2:
            self.log.error("Too many positional arguments")
            return {}
        result = {}
        for r in response if 'totalResultsReturned' not in response else response['Results']:
            arg = [arg[0]] if len(arg) and isinstance(arg[0], str) else arg
            if value_only:
                result[r['Name']] = {k: v['Value'] for k, v in r[value].items() if
                                     'Value' in v and (not len(arg) or (len(arg) and k == arg[0]))}  # k in arg[0]))} fixes #14
            elif time_only:
                result[r['Name']] = {k: v['Time'] for k, v in r[value].items() if
                                     'Time' in v and (not len(arg) or (len(arg) and k == arg[0]))}  # k in arg[0]))}
            else:
                result[r['Name']] = {k: v for k, v in r[value].items() if
                                     (not len(arg) or (len(arg) and k == arg[0]))}  # k in arg[0]))}
            if not result[r['Name']]:
                result.pop(r['Name'], None)
            elif len(result[r['Name']].values()) == 1:
                result[r['Name']] = list(result[r['Name']].values())[0]
        return result

    def _parse_filters(self, name, value, not_value, filter_list, case_sensitive):
        compare = "=" if case_sensitive else "~"
        if value:
            self._append_filter(name, value, compare, "{}{}{}", filter_list)
        elif not_value:
            self._append_filter(name, not_value, compare,
                                "{}!{}{}", filter_list)

    def _convert_data(self, response, k, v):
        try:
            test_type = unicode
        except NameError:
            test_type = str
        if isinstance(v, test_type):
            if re.findall("^[0-9]+$", v):
                response[k] = int(v)
            elif re.findall(r"^[0-9]+\.[0-9]+$", v):
                response[k] = float(v)
            elif re.findall("^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$", v):
                response[k] = datetime.datetime.strptime(
                    v, '%Y-%m-%d %H:%M:%S')
        if isinstance(v, dict):
            self._parse_data_types(response[k])
        if isinstance(v, list):
            self._parse_data_types(response[k])

    def _parse_data_types(self, response):
        if isinstance(response, dict):
            for k, v in response.items():
                self._convert_data(response, k, v)
        if isinstance(response, list):
            for i, v in enumerate(response):
                self._convert_data(response, i, v)

    def get(self, name=None, state=None, group=None, room=None, device_type=None, not_name=None, not_state=None, not_group=None,
            not_room=None, not_device_type=None, case_sensitive=None, filters=None, timeout=0.1, blocking=False, raw_result=None):
        """
        Get FHEM data of devices, can filter by parameters or custom defined filters.
        All filters use regular expressions (except full match), so don't forget escaping.
        Filters can be used by all other get functions.
        For more information about filters, see https://FHEM.de/commandref.html#devspec

        :param name: str or list, device name in FHEM
        :param state: str or list, state in FHEM
        :param group: str or list, filter FHEM groups
        :param room: str or list, filter FHEM room
        :param device_type: str or list, FHEM device type
        :param not_name: not name
        :param not_state: not state
        :param not_group: not group
        :param not_room: not room
        :param not_device_type: not device_type
        :param case_sensitive: bool, use case_sensitivity for all filter functions
        :param filters: dict of filters - key=attribute/internal/reading, value=regex for value, e.g. {"battery": "ok"}
        :param raw_result: On True: Don't convert to python types and send full FHEM response
        :param timeout: timeout for reply
        :param blocking: telnet socket mode, default blocking=False
        :return: dict of FHEM devices
        """
        if not self.connected():
            self.connect()
        if self.connected():
            filter_list = []
            self._parse_filters("NAME", name, not_name,
                                filter_list, case_sensitive)
            self._parse_filters("STATE", state, not_state,
                                filter_list, case_sensitive)
            self._parse_filters("group", group, not_group,
                                filter_list, case_sensitive)
            self._parse_filters("room", room, not_room,
                                filter_list, case_sensitive)
            self._parse_filters("TYPE", device_type,
                                not_device_type, filter_list, case_sensitive)
            if filters:
                for key, value in filters.items():
                    filter_list.append("{}{}{}".format(
                        key, "=" if case_sensitive else "~", value))
            cmd = "jsonlist2 {}".format(":FILTER=".join(filter_list))
            if self.protocol == 'telnet':
                result = self.send_recv_cmd(
                    cmd, blocking=blocking, timeout=timeout)
            else:
                result = self.send_recv_cmd(
                    cmd, blocking=False, timeout=timeout)
            if not result or raw_result:
                return result
            result = result['Results']
            self._parse_data_types(result)
            return result
        else:
            self.log.error("Failed to get fhem state. Not connected.")
            return {}

    def get_states(self, **kwargs):
        """
        Return only device states, can use filters from get().

        :param kwargs: Use keyword arguments from :py:meth:`Fhem.get` function
        :return: dict of FHEM devices with states
        """
        response = self.get(**kwargs)
        if not response:
            return response
        return {r['Name']: r['Readings']['state']['Value'] for r in response if 'state' in r['Readings']}

    def get_readings(self, *arg, **kwargs):
        """
        Return readings of a device, can use filters from get().

        :param arg: str, Get only a specified reading, return all readings of device when parameter not given
        :param value_only: return only value of reading, not timestamp
        :param time_only: return only timestamp of reading
        :param kwargs: use keyword arguments from :py:meth:`Fhem.get` function
        :return: dict of FHEM devices with readings
        """
        value_only = kwargs['value_only'] if 'value_only' in kwargs else None
        time_only = kwargs['time_only'] if 'time_only' in kwargs else None
        kwargs.pop('value_only', None)
        kwargs.pop('time_only', None)
        response = self.get(**kwargs)
        return self._response_filter(response, arg, 'Readings', value_only=value_only, time_only=time_only)

    def get_attributes(self, *arg, **kwargs):
        """
        Return attributes of a device, can use filters from get()

        :param arg: str, Get only specified attribute, return all attributes of device when parameter not given
        :param kwargs: use keyword arguments from :py:meth:`Fhem.get` function
        :return: dict of FHEM devices with attributes
        """
        response = self.get(**kwargs)
        return self._response_filter(response, arg, 'Attributes')

    def get_internals(self, *arg, **kwargs):
        """
        Return internals of a device, can use filters from get()

        :param arg: str, Get only specified internal, return all internals of device when parameter not given
        :param kwargs: use keyword arguments from :py:meth:`Fhem.get` function
        :return: dict of FHEM devices with internals
        """
        response = self.get(**kwargs)
        return self._response_filter(response, arg, 'Internals')

    def get_device(self, device, **kwargs):
        """
        Get all data from a device

        :param device: str or list,
        :param kwargs: use keyword arguments from :py:meth:`Fhem.get` function
        :return: dict with data of specific FHEM device
        """
        return self.get(name=device, **kwargs)

    def get_device_state(self, device, **kwargs):
        """
        Get state of one device

        :param device: str or list,
        :param kwargs: use keyword arguments from :py:meth:`Fhem.get` and :py:meth:`Fhem.get_states` functions
        :return: str, int, float when only specific value requested else dict
        """
        result = self.get_states(name=device, **kwargs)
        return self._sand_down(result)

    def get_device_reading(self, device, *arg, **kwargs):
        """
        Get reading(s) of one device

        :param device: str or list,
        :param arg: str for one reading, list for special readings, empty for all readings
        :param kwargs: use keyword arguments from :py:meth:`Fhem.get` and :py:meth:`Fhem.get_readings` functions
        :return: str, int, float when only specific value requested else dict
        """
        result = self.get_readings(*arg, name=device, **kwargs)
        return self._sand_down(result)

    def get_device_attribute(self, device, *arg, **kwargs):
        """
        Get attribute(s) of one device

        :param device: str or list,
        :param arg: str for one attribute, list for special attributes, empty for all attributes
        :param kwargs: use keyword arguments from :py:meth:`Fhem.get` function
        :return: str, int, float when only specific value requested else dict
        """
        result = self.get_attributes(*arg, name=device, **kwargs)
        return self._sand_down(result)

    def get_device_internal(self, device, *arg, **kwargs):
        """
        Get internal(s) of one device

        :param device: str or list,
        :param arg: str for one internal value, list for special internal values, empty for all internal values
        :param kwargs: use keyword arguments from :py:meth:`Fhem.get` function
        :return: str, int, float when only specific value requested else dict
        """
        result = self.get_internals(*arg, name=device, **kwargs)
        return self._sand_down(result)


class FhemEventQueue:
    '''Creates a thread that listens to FHEM events and dispatches them to
    a Python queue.'''

    def __init__(self, server, que, port=7072, protocol='telnet',
                 use_ssl=False, username="", password="", csrf=True, cafile="",
                 filterlist=None, timeout=0.1,
                 eventtimeout=60, serverregex=None, loglevel=1):
        '''
        Construct an event queue object, FHEM events will be queued into the queue given at initialization.

        :param server: FHEM server address
        :param que: Python Queue object, receives FHEM events as dictionaries
        :param port: FHEM telnet port
        :param protocol: 'telnet', 'http' or 'https'. NOTE: for FhemEventQueue, currently only 'telnet' is supported!
        :param use_ssl: boolean for SSL (TLS)
        :param username: http(s) basicAuth username
        :param password: (global) telnet password or http(s) basicAuth password
        :param csrf: (http(s)) use csrf token (FHEM 5.8 and newer), default True (currently not used, since telnet-only)
        :param cafile: path to public certificate of your root authority, if left empty, https protocol will ignore certificate checks.
        :param filterlist: array of filter dictionaires [{"dev"="lamp1"}, {"dev"="livingtemp", "reading"="temperature"}]. A filter dictionary can contain devstate (type of FHEM device), dev (FHEM device name) and/or reading conditions. The filterlist works on client side.
        :param timeout: internal timeout for socket receive (should be short)
        :param eventtimeout: larger timeout for server keep-alive messages
        :param serverregex: FHEM regex to restrict event messages on server side.
        :param loglevel: deprecated, will be removed. Use standard python logging function for logger 'FhemEventQueue', old: 0: no log, 1: errors, 2: info, 3: debug
        '''
        # self.set_loglevel(loglevel)
        self.log = logging.getLogger('FhemEventQueue')
        self.informcmd = "inform timer"
        if serverregex is not None:
            self.informcmd += " " + serverregex
        if protocol != 'telnet':
            self.log.error("ONLY TELNET is currently supported for EventQueue")
            return
        self.fhem = Fhem(server=server, port=port, use_ssl=use_ssl, username=username,
                         password=password, cafile=cafile, loglevel=loglevel)
        self.fhem.connect()
        self.EventThread = threading.Thread(target=self._event_worker_thread,
                                            args=(que, filterlist,
                                                  timeout, eventtimeout))
        self.EventThread.setDaemon(True)
        self.EventThread.start()

    def set_loglevel(self, level):
        '''
        Set logging level, [Deprecated, will be removed, use python's logging.setLevel]

        :param level: 0: critical, 1: errors, 2: info, 3: debug
        '''
        self.log.warning(
            "Deprecation: please set logging levels using python's standard logging for logger 'Fhem'")
        if level == 0:
            self.log.setLevel(logging.CRITICAL)
        elif level == 1:
            self.log.setLevel(logging.ERROR)
        elif level == 2:
            self.log.setLevel(logging.INFO)
        elif level == 3:
            self.log.setLevel(logging.DEBUG)

    def _event_worker_thread(self, que, filterlist, timeout=0.1,
                             eventtimeout=120):
        self.fhem.send_cmd(self.informcmd)
        data = ""
        lastreceive = time.time()
        eventThreadActive = True
        while eventThreadActive is True:
            while self.fhem.connected() is not True:
                self.fhem.connect()
                if self.fhem.connected():
                    lastreceive = time.time()
                else:
                    time.sleep(5.0)

            if time.time() - lastreceive > eventtimeout:
                self.log.debug("Event-timeout, refreshing INFORM TIMER")
                self.fhem.send_cmd(self.informcmd)
                if self.fhem.connected() is True:
                    lastreceive = time.time()

            if self.fhem.connected() is True:
                data = self.fhem._recv_nonblocking(timeout)
                lines = data.decode('utf-8').split('\n')
                for l in lines:
                    if len(l) > 0:
                        lastreceive = time.time()
                        li = l.split(' ')
                        if len(li) > 4:
                            dd = li[0].split('-')
                            tt = li[1].split(':')
                            dt = datetime.datetime(int(dd[0]), int(dd[1]),
                                                   int(dd[2]), int(tt[0]),
                                                   int(tt[1]), int(tt[2]))
                            devtype = li[2]
                            dev = li[3]
                            val = ''
                            for i in range(4, len(li)):
                                val += li[i]
                                if i < len(li) - 1:
                                    val += " "
                            vl = val.split(" ")
                            val = ''
                            unit = ''
                            if len(vl) > 0:
                                if vl[0][-1] == ':':
                                    read = vl[0][:-1]
                                    if len(vl) > 1:
                                        val = vl[1]
                                    if len(vl) > 2:
                                        unit = vl[2]
                                else:
                                    read = 'STATE'
                                    if len(vl) > 0:
                                        val = vl[0]
                                    if len(vl) > 1:
                                        unit = vl[1]

                                adQ = True
                                if filterlist is not None:
                                    adQ = False
                                    for f in filterlist:
                                        adQt = True
                                        for c in f:
                                            if c == 'devtype':
                                                if devtype != f[c]:
                                                    adQt = False
                                            if c == 'device':
                                                if dev != f[c]:
                                                    adQt = False
                                            if c == 'reading':
                                                if read != f[c]:
                                                    adQt = False
                                        if adQt:
                                            adQ = True
                                if adQ:
                                    ev = {
                                        'timestamp': dt,
                                        'devicetype': devtype,
                                        'device': dev,
                                        'reading': read,
                                        'value': val,
                                        'unit': unit
                                    }
                                    que.put(ev)
            time.sleep(timeout)
        self.fhem.close()
        return

    def close(self):
        '''Stop event thread and close socket.'''
        self.eventThreadActive = False
