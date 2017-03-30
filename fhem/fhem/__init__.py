import time
import datetime
import json
import socket
import ssl
import threading
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

    
'''API for FHEM homeautomation server'''
__version__ = '0.4.0'


class Fhem:
    '''Connects to FHEM via socket communication with optional SSL and password
    support'''
    def __init__(self, server, port=7072,
                 ssl=False, protocol="telnet", username="", password="", csrf=True,
                 cafile="", loglevel=1):
        '''Instantiate connector object.
        :param server: address of FHEM server
        :param port: telnet/http(s) port of server
        :param protocol: 'telnet', 'http' or 'https'
        :param ssl: boolean for SSL (TLS) [https as protocol sets ssl=True]
        :param cafile: path to public certificate of your root authority, if
        left empty, https protocol will ignore certificate checks.
        :param username: username for http(s) basicAuth validation
        :param password: (global) telnet or http(s) password
        :param csrf: (http(s)) use csrf token (FHEM 5.8 and newer), default True
        :param loglevel: 0: no log, 1: errors, 2: info, 3: debug
        '''
        validprots = ['http', 'https', 'telnet']
        self.server = server
        self.port = port
        self.ssl = ssl
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
        self.httpsHandler = None
        if protocol in validprots:
            self.protocol = protocol
        else:
            if loglevel > 0:
                print("E - Invalid protocol: ", protocol)
        if (protocol == "https") or (ssl is True):
            self.ssl = True
            self.baseurlauth = "https://"+server+":"+str(port)+"/"
            self.baseurltoken = self.baseurlauth + "fhem"
            self.baseurl = self.baseurlauth + "fhem?XHR=1&cmd="
        else:
            if protocol == "http":
                self.baseurlauth = "http://"+server+":"+str(port)+"/"
                self.baseurltoken = self.baseurlauth + "fhem"
                self.baseurl = self.baseurlauth + "fhem?XHR=1&cmd="
        if protocol == "https" or protocol == "http":
            self._install_opener()

    def connect(self):
        if self.protocol == 'telnet':
            '''create socket connection to server (telnet protocol only)'''
            try:
                if self.loglevel > 2:
                    print("D - creating socket...")
                if self.ssl:
                    self.bsock = socket.socket(socket.AF_INET,
                                               socket.SOCK_STREAM)
                    self.sock = ssl.wrap_socket(self.bsock)
                    self.sock.connect((self.server, self.port))
                    if self.loglevel > 1:
                        print("I - Connecting to", self.server, "on port:",
                              self.port, " with SSL (TLS)")
                else:
                    self.sock = socket.socket(socket.AF_INET,
                                              socket.SOCK_STREAM)
                    self.sock.connect((self.server, self.port))
                    if self.loglevel > 1:
                        print("I - Connecting to", self.server, "on port:",
                              self.port, " no SSL")
                self.connection = True
                if self.loglevel > 1:
                    print("I - Connected to", self.server, "on port:",
                          self.port)
            except socket.error:
                self.connection = False
                if self.loglevel > 0:
                    print("E - Failed to connected to", self.server,
                          "on port:", self.port)
                return
            if self.password != "":
                # time.sleep(1.0)
                # self.send_cmd("\n")
                # prmpt = self._recv_nonblocking(4.0)
                prmpt = self.sock.recv(32000)
                if self.loglevel > 2:
                    print("auth-prompt:", prmpt)
                self.nolog = True
                self.send_cmd(self.password)
                self.nolog = False
                time.sleep(0.1)
                try:
                    po1 = self.sock.recv(32000)
                    if self.loglevel > 2:
                        print("auth-repl1:", po1)
                except socket.error:
                    if self.loglevel > 0:
                        print("E - Failed to recv auth reply.")
                    self.connection = False
                    return
                if self.loglevel > 1:
                    print("I - Auth password sent to", self.server)
        else:  # http(s)
            if self.csrf:
                dat = self.send("").decode("UTF-8")
                stp = dat.find("csrf_")
                if stp != -1:
                    token = dat[stp:]
                    token = token[:token.find("'")]
                    self.csrftoken = token
                    self.connection = True
                else:
                    print("E - CSRF token requested for server that doesn't know CSRF")
            else:
                self.connection = True

    def connected(self):
        '''Returns True if socket/http(s) session is connected to server.'''
        return self.connection

    def logging(self, level):
        '''Set logging level,
        :param level: 0: no log, 1: errors, 2: info, 3: debug
        '''
        self.loglevel = level

    def close(self):
        '''Closes socket connection. (telnet only)'''
        if self.protocol == 'telnet':
            if self.connected():
                time.sleep(0.2)
                self.sock.close()
                self.connection = False
                if self.loglevel > 1:
                    print("I - Disconnected from fhemserver")
            else:
                if self.loglevel > 0:
                    print("E - Cannot disconnect, not connected.")
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
            self.httpsHandler = HTTPSHandler(context=self.context)
            if self.username != "":
                self.opener = build_opener(self.httpsHandler,
                                           self.auth_handler)
            else:
                self.opener = build_opener(self.httpsHandler)
        else:
            if self.username != "":
                self.opener = build_opener(self.auth_handler)
        if self.opener is not None:
            if self.loglevel > 2:
                print("D - Setting up opener on: ", self.baseurlauth)
            install_opener(self.opener)

    def send(self, buf):
        '''Sends a buffer to server
        :param buf: binary buffer'''
        if len(buf)>0:
            if not self.connected():
                if self.loglevel > 2:
                    print("D - Not connected, trying to connect...")
                self.connect()
        if self.protocol == 'telnet':
            if self.connected():
                if self.loglevel > 2:
                    print("D - Connected, sending...")
                try:
                    self.sock.sendall(buf)
                    if self.loglevel > 1:
                        print("I - Sent msg, len=", len(buf))
                    return None
                except OSError as e:
                    if self.loglevel > 0:
                        print("E - Failed to send msg, len=", len(buf),
                              "exception raised: ", e)
                    self.connection = None
                    return None
            else:
                if self.loglevel > 0:
                    print("E - Failed to send msg, len=", len(buf),
                          "not connected.")
                return None
        else:  # HTTP(S)
            paramdata = None
            if self.csrf and len(buf) > 0:
                if len(self.csrftoken) == 0:
                    print("E - csrf token not available!")
                    self.connection = False
                else:
                    datas = {'fwcsrf': self.csrftoken}
                    paramdata = urlencode(datas).encode('UTF-8')
            try:
                if self.loglevel > 2:
                    print("D - Cmd:", buf)
                cmd = quote(buf)
                if self.loglevel > 2:
                    print("D - Cmd-enc:", cmd)
                if len(cmd) > 0:
                    ccmd = self.baseurl + cmd
                else:
                    ccmd = self.baseurltoken
                if self.loglevel > 1:
                    print("I - request: ", ccmd)
                ans = urlopen(ccmd, paramdata) # , data, 10)  # XXX timeout
                data = ans.read()
                return data
            except URLError as e:
                self.connection=False
                if self.loglevel > 0:
                    print("E - Failed to send msg, len=", len(buf), e)
                return None

    def sendCmd(self, msg):
        if self.loglevel > 0:
            print("Deprecation: please use self_cmd instead of selfCmd")
        return self.send_cmd(msg)

    def send_cmd(self, msg):
        '''Sends a command to server.
        :param msg: string with FHEM command, e.g. 'set lamp on'
        '''
        if not self.connected():
            self.connect()
        if self.loglevel > 2 and self.nolog is not True:
            print("D - Sending: ", msg)
        if self.protocol == 'telnet':
            if self.connection:
                msg = msg + "\n"
                cmd = msg.encode('utf-8')
                return self.send(cmd)
            else:
                if self.loglevel > 0:
                    print("E - Failed to send msg, len=", len(msg),
                          "not connected.")
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
            except socket.error:
                if self.loglevel > 3:
                    print("D - exception in non-blocking")
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
                except socket.error:
                    wok = 0
                    if self.loglevel > 3:
                        print("D - exception in non-blocking")
            self.sock.setblocking(True)
        return data

    def sendRcvCmd(self, msg, timeout=0.1, blocking=True):
        if self.loglevel > 0:
            print("Deprecation: use send_recv_cmd instead of sendRcvCmd")
            self.send_recv_cmd(msg, timeout, blocking)

    def send_recv_cmd(self, msg, timeout=0.1, blocking=True):
        '''Sends a command to the server and waits for an immediate reply.
        :param msg: FHEM command (e.g. 'set lamp on')
        :param timeout: waiting time for reply
        :param blocking: (telnet only) on True: use blocking socket
        communication (bool)'''
        data = b''
        if not self.connected():
            self.connect()
        if self.protocol == 'telnet':
            if self.connection:
                if self.send_cmd(msg):
                    time.sleep(timeout)
                    data = []
                    if blocking is True:
                        try:
                            data = self.sock.recv(32000)
                        except socket.error:
                            if self.loglevel > 0:
                                print("E - Failed to recv msg.", data)
                            return {}
                    else:
                        data = self._recv_nonblocking(timeout)
                    self.sock.setblocking(True)
                else:
                    if self.loglevel > 0:
                        print("E - Failed to send msg, len=", len(msg),
                              "send_cmd failed.")
            else:
                if self.loglevel > 0:
                    print("E - Failed to send msg, len=", len(msg),
                          "not connected.")
        else:
            data = self.send_cmd(msg)
            if data is None:
                return None
        if len(data) == 0:
            return {}
        try:
            sdata = data.decode('utf-8')
            jdata = json.loads(sdata)
        except:
            if self.loglevel > 0:
                print("E - Failed to decode json, exception raised.",
                      data)
            return {}
        if len(jdata[u'Results']) == 0:
            if self.loglevel > 0:
                print("E - Query had no result.")
            return {}
        else:
            if self.loglevel > 1:
                print("I - JSON answer received.")
            return jdata

    def getDevState(self, dev, timeout=0.1):
        if self.loglevel > 0:
            print("Deprecation: use get_dev_state insteadd of getDevState")
            self.get_dev_state(dev, timeout)

    def get_dev_state(self, dev, timeout=0.1):
        '''Get all FHEM device properties as JSON object
        :param dev: FHEM device name
        :param timeout: timeout for reply'''
        if not self.connected():
            self.connect()
        if self.connected():
            return self.send_recv_cmd("jsonlist2 " + dev, timeout=timeout)
        else:
            if self.loglevel > 0:
                print("E - Failed to get dev state for", dev,
                      "- not connected.")
            return {}

    def getDevReading(self, dev, reading, timeout=0.1):
        if self.loglevel > 0:
            print("Deprecation: use get_dev_reading instead of getDevReading")
            self.get_dev_reading(dev, reading, timeout)

    def get_dev_reading(self, dev, reading, timeout=0.1):
        '''Get a specific reading from a FHEM device
        :param dev: FHEM device
        :param reading: name of FHEM reading
        :param timeout: timeout for reply'''
        read = None
        state = self.get_dev_state(dev, timeout=timeout)
        if state == {}:
            return None
        try:
            read = state['Results'][0]['Readings'][reading]['Value']
        except:
            if self.loglevel > 0:
                print("E - Reading not defined:", dev, reading)
            return read
        return read

    def getDevReadings(self, dev, reading, timeout=0.1):
        if self.loglevel > 0:
            print("Deprecation: use get_dev_reading instead of getDevReading")
            self.get_dev_readings(dev, reading, timeout)

    def get_dev_readings(self, dev, readings, timeout=0.1):
        '''Get a list of readings for one FHEM device
        :param dev: FHEM device
        'param readings': array of FHEM reading names
        :param timeout: timeout for reply'''
        reads = {}
        state = self.get_dev_state(dev, timeout=timeout)
        if state == {}:
            return reads
        for reading in readings:
            try:
                rr1 = state['Results'][0]
                reads[reading] = rr1['Readings'][reading]['Value']
            except:
                if self.loglevel > 0:
                    print("E - Reading not defined:", dev, reading)
        return reads

    def getFhemState(self, timeout=0.1):
        if self.loglevel > 0:
            print("Deprecation: use get_fhem_state instead of getFhemState")
            self.get_fhem_state(timeout)

    def get_fhem_state(self, timeout=0.1):
        '''Get FHEM state of all devices, returns a large JSON object with
        every single FHEM device and reading state
        :param timeout: timeout for reply'''
        if not self.connected():
            self.connect()
        if self.connected():
            return self.send_recv_cmd("jsonlist2", blocking=False,
                                      timeout=timeout)
        else:
            if self.loglevel > 0:
                print("E - Failed to get fhem state - not connected.")
            return {}


class FhemEventQueue:
    '''Creates a thread that listens to FHEM events and dispatches them to
    a Python queue.'''
    def __init__(self, server,  que, port=7072, protocol='telnet',
                 ssl=False, username="", password="", cafile="",
                 filterlist=None, timeout=0.1,
                 eventtimeout=60, serverregex=None, loglevel=1):
        ''':param server: FHEM server address
        :param que: Python Queue object, receives FHEM events as dictionaries
        :param port: FHEM telnet port
        :param protocol: 'telnet', 'http' or 'https'
          NOTE: for FhemEventQueue, currently only 'telnet' is supported!
        :param port: telnet/http(s) port of server
        :param ssl: boolean for SSL (TLS)
        :param username: http(s) basicAuth username
        :param password: (global) telnet password or http(s) basicAuth password
        :param filterlist: array of filter dictionaires [{"dev"="lamp1"},
        {"dev"="livingtemp", "reading"="temperature"}]. A
        filter dictionary can contain devstate (type of FHEM device), dev (FHEM
        device name) and/or reading conditions.
        The filterlist works on client side.
        :param timeout: internal timeout for socket receive (should be short)
        :param eventtimeout: larger timeout for server keep-alive messages
        :param serverregex: FHEM regex to restrict event messages on server
        side.
        :param loglevel: 0: no log, 1: errors, 2: info, 3: debug
        '''
        self.loglevel = loglevel
        self.informcmd = "inform timer"
        if serverregex is not None:
            self.informcmd += " " + serverregex
        if protocol != 'telnet':
            print("E - ONLY TELNET is currently supported for EventQueue")
            return
        self.fhem = Fhem(server=server, port=port, ssl=ssl, username=username,
                         password=password, cafile=cafile, loglevel=loglevel)
        self.fhem.connect()
        self.EventThread = threading.Thread(target=self._event_worker_thread,
                                            args=(que, filterlist,
                                                  timeout, eventtimeout))
        self.EventThread.setDaemon(True)
        self.EventThread.start()

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
                if self.loglevel > 2:
                    print("D - Event-timeout, refreshing INFORM TIMER")
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
                                if i < len(li)-1:
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
