'''API for FHEM homeautomation server, supporting telnet or HTTP/HTTPS connections with authentication and CSRF-token support.'''
import time
import datetime
import json
import socket
import ssl
import threading
import logging

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

__version__ = '0.5.4'  # needs to be in sync with setup.py and documentation (conf.py, branch gh-pages)

# create logger with 'python_fhem'
logger = logging.getLogger(__name__)


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
        :param loglevel: 0: critical, 1: errors, 2: info, 3: debug
        '''
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
        self.set_loglevel(loglevel)

        # Check if protocol is supported
        if protocol in validprots:
            self.protocol = protocol
        else:
            logger.error("Invalid protocol: {}".format(protocol))

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
                logger.debug("Creating socket...")
                if self.ssl:
                    self.bsock = socket.socket(socket.AF_INET,
                                               socket.SOCK_STREAM)
                    self.sock = ssl.wrap_socket(self.bsock)
                    logger.info("Connecting to {}:{} with SSL (TLS)".format(self.server, self.port))
                else:
                    self.sock = socket.socket(socket.AF_INET,
                                              socket.SOCK_STREAM)
                    logger.info("Connecting to {}:{} without SSL".format(self.server, self.port))

                self.sock.connect((self.server, self.port))
                self.connection = True
                logger.info("Connected to {}:{}".format(self.server, self.port))
            except socket.error:
                self.connection = False
                logger.error("Failed to connect to {}:{}".format(self.server, self.port))
                return

            if self.password != "":
                # time.sleep(1.0)
                # self.send_cmd("\n")
                # prmpt = self._recv_nonblocking(4.0)
                prmpt = self.sock.recv(32000)
                logger.debug("auth-prompt: {}".format(prmpt))

                self.nolog = True
                self.send_cmd(self.password)
                self.nolog = False
                time.sleep(0.1)

                try:
                    po1 = self.sock.recv(32000)
                    logger.debug("auth-repl1: {}".format(po1))
                except socket.error:
                    logger.error("Failed to recv auth reply")
                    self.connection = False
                    return
                logger.info("Auth password sent to {}".format(self.server))
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
                        logger.error("CSRF token requested for server that doesn't know CSRF")
                else:
                    logger.error("No valid answer on send when expecting csrf.")
            else:
                self.connection = True

    def connected(self):
        '''Returns True if socket/http(s) session is connected to server.'''
        return self.connection

    def set_loglevel(self, level):
        '''Set logging level.

        :param level: 0: critical, 1: errors, 2: info, 3: debug
        '''
        if level == 0:
            logger.setLevel(logging.CRITICAL)
        elif level == 1:
            logger.setLevel(logging.ERROR)
        elif level == 2:
            logger.setLevel(logging.INFO)
        elif level == 3:
            logger.setLevel(logging.DEBUG)

    def close(self):
        '''Closes socket connection. (telnet only)'''
        if self.protocol == 'telnet':
            if self.connected():
                time.sleep(0.2)
                self.sock.close()
                self.connection = False
                logger.info("Disconnected from fhem-server")
            else:
                logger.error("Cannot disconnect, not connected")
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
            logger.debug("Setting up opener on: {}".format(self.baseurlauth))
            install_opener(self.opener)

    def send(self, buf):
        '''Sends a buffer to server

        :param buf: binary buffer'''
        if len(buf) > 0:
            if not self.connected():
                logger.debug("Not connected, trying to connect...")
                self.connect()
        if self.protocol == 'telnet':
            if self.connected():
                logger.debug("Connected, sending...")
                try:
                    self.sock.sendall(buf)
                    logger.info("Sent msg, len={}".format(len(buf)))
                    return None
                except OSError as err:
                    logger.error("Failed to send msg, len={}. Exception raised: {}".format(len(buf), err))
                    self.connection = None
                    return None
            else:
                logger.error("Failed to send msg, len={}. Not connected.".format(len(buf)))
                return None
        else:  # HTTP(S)
            paramdata = None
            if self.csrf and len(buf) > 0:
                if len(self.csrftoken) == 0:
                    logger.error("CSRF token not available!")
                    self.connection = False
                else:
                    datas = {'fwcsrf': self.csrftoken}
                    paramdata = urlencode(datas).encode('UTF-8')

            try:
                logger.debug("Cmd: {}".format(buf))
                cmd = quote(buf)
                logger.debug("Cmd-enc: {}".format(cmd))

                if len(cmd) > 0:
                    ccmd = self.baseurl + cmd
                else:
                    ccmd = self.baseurltoken

                logger.info("Request: {}".format(ccmd))
                ans = urlopen(ccmd, paramdata)  # , data, 10)  # XXX timeout
                data = ans.read()
                return data
            except URLError as err:
                self.connection = False
                logger.error("Failed to send msg, len={}, {}".format(len(buf), err))
                return None

    def send_cmd(self, msg):
        '''Sends a command to server.

        :param msg: string with FHEM command, e.g. 'set lamp on'
        '''
        if not self.connected():
            self.connect()
        if not self.nolog:
            logger.debug("Sending: {}".format(msg))
        if self.protocol == 'telnet':
            if self.connection:
                msg = "{}\n".format(msg)
                cmd = msg.encode('utf-8')
                return self.send(cmd)
            else:
                logger.error("Failed to send msg, len={}. Not connected.".format(len(msg)))
                return None
        else:
            return self.send(msg)

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
                logger.debug("Exception in non-blocking. Error: {}".format(err))
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
                    logger.debug("Exception in non-blocking. Error: {}".format(err))
            self.sock.setblocking(True)
        return data

    def send_recv_cmd(self, msg, timeout=0.1, blocking=True):
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
                    try:
                        data = self.sock.recv(32000)
                    except socket.error:
                        logger.error("Failed to recv msg. {}".format(data))
                        return {}
                else:
                    data = self._recv_nonblocking(timeout)

                self.sock.setblocking(True)
            else:
                logger.error("Failed to send msg, len={}. Not connected.".format(len(msg)))
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
            logger.error("Failed to decode json, exception raised. {} {}".format(data, err))
            return {}
        if len(jdata[u'Results']) == 0:
            logger.error("Query had no result.")
            return {}
        else:
            logger.info("JSON answer received.")
            return jdata

    def get_dev_state(self, dev, timeout=0.1):
        '''
        Get all FHEM device properties as JSON object

        :param dev: FHEM device name
        :param timeout: timeout for reply
        '''
        if not self.connected():
            self.connect()

        if self.connected():
            return self.send_recv_cmd("jsonlist2 {}".format(dev), timeout=timeout)
        else:
            logger.error("Failed to get dev state for {}. Not connected.".format(dev))
            return {}

    def get_dev_reading(self, dev, reading, timeout=0.1):
        '''
        Get a specific reading from a FHEM device

        :param dev: FHEM device
        :param reading: name of FHEM reading
        :param timeout: timeout for reply
        '''
        read = None
        state = self.get_dev_state(dev, timeout=timeout)
        if state == {}:
            return None

        try:
            read = state['Results'][0]['Readings'][reading]['Value']
        except Exception as err:
            logger.error("Reading not defined: {}, {}, {}".format(dev, reading, err))
            return read
        return read

    def getDevReadings(self, dev, reading, timeout=0.1):
        logger.critical("Deprecation: use get_dev_readings instead of getDevReadings")
        self.get_dev_readings(dev, reading, timeout)

    def get_dev_readings(self, dev, readings, timeout=0.1):
        '''
        Get a list of readings for one FHEM device

        :param dev: FHEM device
        :param readings: array of FHEM reading names
        :param timeout: timeout for reply
        '''
        reads = {}
        state = self.get_dev_state(dev, timeout=timeout)
        if state == {}:
            return reads
        for reading in readings:
            try:
                rr1 = state['Results'][0]
                reads[reading] = rr1['Readings'][reading]['Value']
            except Exception as err:
                logger.error("Reading not defined: {}, {}, {}".format(dev, reading, err))
        return reads

    def get_dev_reading_time(self, dev, reading, timeout=0.1):
        '''
        Get the datetime of a specific reading from a FHEM device

        :param dev: FHEM device
        :param reading: name of FHEM reading
        :param timeout: timeout for reply
        '''
        read = None
        state = self.get_dev_state(dev, timeout=timeout)
        if state == {}:
            return None
        try:
            read = state['Results'][0]['Readings'][reading]['Time']
        except:
            logger.error("Reading not defined: {} {}".format(dev, reading))
            return None
        try:
            time = datetime.datetime.strptime(read, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError) as err:
            logger.error("Invalid time format: {}".format(err))
            return None
        return time

    def get_dev_readings_time(self, dev, readings, timeout=0.1):
        '''
        Get a list of datetimes of readings for one FHEM device

        :param dev: FHEM device
        :param readings: array of FHEM reading names
        :param timeout: timeout for reply
        '''
        reads = {}
        state = self.get_dev_state(dev, timeout=timeout)
        if state == {}:
            return reads
        for reading in readings:
            try:
                rr1 = state['Results'][0]
                read = rr1['Readings'][reading]['Time']
                try:
                    read_time = datetime.datetime.strptime(read, '%Y-%m-%d %H:%M:%S')
                    reads[reading] = read_time
                except (ValueError, TypeError) as err:
                    logger.error("Invalid time format: {}".format(err))
            except Exception as err:
                logger.error("Reading not defined: {} {} {}".format(dev, reading, err))
        return reads

    def getFhemState(self, timeout=0.1):
        logger.critical("Deprecation: use get() without parameters instead of getFhemState")
        self.get(timeout)

    def get_fhem_state(self, timeout=0.1):
        logger.critical("Deprecation: use get() without parameters instead of get_fhem_state")
        self.get(timeout)

    def _append_filter(self, name, value, compare, string, filter_list):
        value_list = [value] if isinstance(value, str) else value
        values = ",".join(value_list)
        filter_list.append(string.format(name, compare, values))

    def _parse_filters(self, name, value, not_value, filter_list, case_sensitive):
        compare = "=" if case_sensitive else "~"
        if value:
            self._append_filter(name, value, compare, "{}{}{}", filter_list)
        elif not_value:
            self._append_filter(name, not_value, compare, "{}!{}{}", filter_list)

    def _response_filter(self, response, arg, value, only_value=None):
        result = {}
        if len(arg) == 1:
            for r in response['Results']:
                if only_value:
                    if value in r and arg[0] in r[value] and 'Value' in r[value][arg[0]]:
                        result[r['Name']] = r[value][arg[0]]['Value']
                else:
                    if value in r and arg[0] in r[value]:
                        result[r['Name']] = r[value][arg[0]]
        elif not len(arg):
            for r in response['Results']:
                result[r['Name']] = r[value]
        else:
            logger.error("Only one positional argument allowed")
            return {}
        return result

    def get(self, name=None, state=None, group=None, room=None, device_type=None, nname=None, nstate=None, ngroup=None,
            nroom=None, ndevice_type=None, case_sensitive=None, filters=None, timeout=0.1):
        """
        Get FHEM state of devices, filter by parameters. See https://fhem.de/commandref.html#devspec
        This function abstracts often used filters and reduces transfered data size

        :param name: str or list, regex for device name in fhem
        :param state: str or list, regex for device state in fhem
        :param group: str or list, regex to filter fhem groups
        :param room: str or list, regex to filter fhem room
        :param device_type: str or list, regex to filter fhem device type
        :param nname: not name
        :param nstate: not state
        :param ngroup: not group
        :param nroom: not room
        :param ndevice_type: not type
        :param case_sensitive: bool, use case_sensitivity for all filter functions
        :param filters: dict of filters - key=attribute/internal/reading, value=regex for value, e.g. {"battery": "ok"}
        :param timeout: timeout for reply
        :return: dict of fhem devices
        """
        if not self.connected():
            self.connect()
        if self.connected():
            filter_list = []
            self._parse_filters("NAME", name, nname, filter_list, case_sensitive)
            self._parse_filters("STATE", state, nstate, filter_list, case_sensitive)
            self._parse_filters("group", group, ngroup, filter_list, case_sensitive)
            self._parse_filters("room", room, nroom, filter_list, case_sensitive)
            self._parse_filters("TYPE", device_type, ndevice_type, filter_list, case_sensitive)
            if filters:
                for key, value in filters.items():
                    filter_list.append("{}{}{}".format(key, "=" if case_sensitive else "~", value))
            cmd = "jsonlist2 {}".format(":FILTER=".join(filter_list))
            result = self.send_recv_cmd(cmd, blocking=False, timeout=timeout)
            return result
        else:
            logger.error("Failed to get fhem state. Not connected.")
            return {}

    def get_states(self, **kwargs):
        """
        Return only device states, can use filters from get()

        :param kwargs: use keyword arguments from get function
        :return: dict of fhem devices with states
        """
        response = self.get(**kwargs)
        return {r['Name']: r['Readings']['state']['Value'] for r in response['Results'] if 'state' in r['Readings']}

    def get_readings(self, arg, only_value=False, **kwargs):
        """
        Return readings of a device, can use filters from get()

        :param arg: str, Get only specified reading, return all readings of device when parameter not given
        :param only_value: return only value of reading, not timestamp
        :param kwargs: use keyword arguments from get function
        :return: dict of fhem devices with readings
        """
        response = self.get(**kwargs)
        return self._response_filter(response, [arg], 'Readings', only_value=only_value)

    def get_attributes(self, *arg, **kwargs):
        """
        Return attributes of a device, can use filters from get()

        :param arg: str, Get only specified attribute, return all attributes of device when parameter not given
        :param kwargs: use keyword arguments from get function
        :return: dict of fhem devices with attributes
        """
        response = self.get(**kwargs)
        return self._response_filter(response, arg, 'Attributes')

    def get_internals(self, *arg, **kwargs):
        """
        Return internals of a device, can use filters from get()

        :param arg: str, Get only specified internal, return all internals of device when parameter not given
        :param kwargs: use keyword arguments from get function
        :return: dict of fhem devices with internals
        """
        response = self.get(**kwargs)
        return self._response_filter(response, arg, 'Internals')


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
        :param loglevel: 0: no log, 1: errors, 2: info, 3: debug
        '''
        self.set_loglevel(loglevel)
        self.informcmd = "inform timer"
        if serverregex is not None:
            self.informcmd += " " + serverregex
        if protocol != 'telnet':
            logger.error("ONLY TELNET is currently supported for EventQueue")
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
        Set logging level,

        :param level: 0: critical, 1: errors, 2: info, 3: debug
        '''
        if level == 0:
            logger.setLevel(logging.CRITICAL)
        elif level == 1:
            logger.setLevel(logging.ERROR)
        elif level == 2:
            logger.setLevel(logging.INFO)
        elif level == 3:
            logger.setLevel(logging.DEBUG)

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
                logger.debug("Event-timeout, refreshing INFORM TIMER")
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

