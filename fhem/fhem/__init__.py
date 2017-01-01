import time
import datetime
import json
import socket
import ssl
import threading
import sys

'''API for FHEM homeautomation server'''

class Fhem:
    '''Connects to FHEM via socket communication with optional SSL and password
    support'''
    def __init__(self, server, port=7072,
                 bSsl=False, password="", loglevel=1):
        '''Instantiate connector object, socket is not opened, use connect() to
        actually open the socket.
        :param server: address of FHEM server
        :param port: telnet port of server
        :param bSsl: boolean for SSL (TLS)
        :param passord: (global) telnet password
        :param loglevel: 0: no log, 1: errors, 2: info, 3: debug
        '''
        self.server = server
        self.port = port
        self.bSsl = bSsl
        self.password = password
        self.loglevel = loglevel
        self.connection = False

    def connect(self):
        '''create socket connection to server'''
        try:
            if self.loglevel > 2:
                print("D - creating socket...")
            if self.bSsl:
                self.bsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock = ssl.wrap_socket(self.bsock)
                self.sock.connect((self.server, self.port))
                if self.loglevel > 1:
                    print("I - Connecting to", self.server, "on port:",
                          self.port, " with SSL (TLS)")
            else:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.server, self.port))
                if self.loglevel > 1:
                    print("I - Connecting to", self.server, "on port:",
                          self.port, " no SSL")
            self.connection = True
            if self.loglevel > 1:
                print("I - Connected to", self.server, "on port:", self.port)
        except:
            self.connection = False
            if self.loglevel > 0:
                print("E - Failed to connected to", self.server, "on port:",
                      self.port)
            return
        if self.password != "":
            time.sleep(0.1)
            self.sendCmd(self.password)
            time.sleep(0.1)
            try:
                self.sock.setblocking(True)
                self.sock.recv(32000)
                self.sock.recv(32000)
            except:
                if self.loglevel > 0:
                    print("E - Failed to recv auth reply, exception raised.")
                self.connection = False
            if self.loglevel > 1:
                print("I - Auth password sent to", self.server)

    def connected(self):
        '''Returns True if socket is connected to server.'''
        return self.connection

    def logging(self, level):
        '''Set logging level,
        :param level: 0: no log, 1: errors, 2: info, 3: debug
        '''
        self.loglevel = level

    def close(self):
        '''Closes socket connection.'''
        if self.connection:
            time.sleep(0.2)
            self.sock.close()
            self.connection = False
            if self.loglevel > 1:
                print("I - Disconnected from fhemserver")
        else:
            if self.loglevel > 0:
                print("E - Cannot disconnect, not connected.")

    def send(self, buf):
        '''Sends a buffer to server
        :param buf: binary buffer'''
        if not self.connected():
            self.connect()
        if self.connection:
            try:
                self.sock.sendall(buf)
                if self.loglevel > 1:
                    print("I - Sent msg, len=", len(buf))
                return True
            except:
                if self.loglevel > 0:
                    print("E - Failed to send msg, len=", len(buf),
                          "exception raised.")
                self.connection = False
                return False
        else:
            if self.loglevel > 0:
                print("E - Failed to send msg, len=", len(buf),
                      "not connected.")
            return False

    def sendCmd(self, msg):
        '''Sends a command to server, \n is appended.
        :param msg: string with FHEM command, e.g. 'set lamp on'
        '''
        if not self.connected():
            self.connect()
        if self.connection:
            msg = msg + "\n"
            cmd = msg.encode('utf-8')
            return self.send(cmd)
        else:
            if self.loglevel > 0:
                print("E - Failed to send msg, len=", len(msg),
                      "not connected.")
            return False

    def recvNonblocking(self, timeout=0.1):
        '''Receives from server, if data available. Returns directly, if no
        data is available.
        :param timeout: timeout in seconds'''
        if not self.connected():
            self.connect()
        data = b''
        if self.connection:
            self.sock.setblocking(False)
            data = b''
            try:
                data = self.sock.recv(32000)
            except:  # (socket.timeout, ssl.SSLWantReadError):
                if self.loglevel > 3:
                    print("D - exception in non-blocking")
                    time.sleep(timeout)
            # except:
            #    self.connection = False
            #    if self.loglevel > 0:
            #        print("D - Non-timeout socket error!")
            #        print("D - Unexpected error:", sys.exc_info()[0])
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
                except:
                    wok = 0
                    if self.loglevel > 3:
                        print("D - exception in non-blocking")
            self.sock.setblocking(True)
        return data

    def sendRcvCmd(self, msg, timeout=0.1, blocking=True):
        '''Sends a command to the server and waits for an immediate reply.
        :param msg: FHEM command (\n is appended)
        :param timeout: waiting time for reply
        :param blocking: on True: use blocking socket communication (bool)'''
        if not self.connected():
            self.connect()
        if self.connection:
            if self.sendCmd(msg):
                time.sleep(timeout)
                data = []
                if blocking is True:
                    try:
                        data = self.sock.recv(32000)
                    except:
                        if self.loglevel > 0:
                            print("E - Failed to recv msg, exception raised.",
                                  data)
                        return {}
                else:
                    data = self.recvNonblocking(timeout)
                self.sock.setblocking(True)

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
            else:
                if self.loglevel > 0:
                    print("E - Failed to send msg, len=", len(msg),
                          "sendcmd failed.")
        else:
            if self.loglevel > 0:
                print("E - Failed to send msg, len=", len(msg),
                      "not connected.")

    def getDevState(self, dev, timeout=0.1):
        '''Get all FHEM device properties as JSON object
        :param dev: FHEM device name
        :param timeout: timeout for reply'''
        if self.connection:
            return self.sendRcvCmd("jsonlist2 " + dev, timeout=timeout)
        else:
            if self.loglevel > 0:
                print("E - Failed to get dev state for", dev,
                      "- not connected.")
            return {}

    def getDevReading(self, dev, reading, timeout=0.1):
        '''Get a specific reading from a FHEM device
        :param dev: FHEM device
        :param reading: name of FHEM reading
        :param timeout: timeout for reply'''
        read = None
        state = self.getDevState(self, dev, timeout)
        if state == {}:
            return None
        try:
            read = state['Results'][0]['Readings'][reading]['Value']
        except:
            if self.loglevel > 0:
                print("E - Reading not defined:", dev, reading)
            return read
        return read

    def getDevReadings(self, dev, readings, timeout=0.1):
        '''Get a list of readings for one FHEM device
        :param dev: FHEM device
        'param readings': array of FHEM reading names
        :param timeout: timeout for reply'''
        reads = {}
        state = self.getDevState(self, dev, timeout)
        if state == {}:
            return reads
        for reading in readings:
            try:
                reads[reading] = state['Results'][
                    0]['Readings'][reading]['Value']
            except:
                if self.loglevel > 0:
                    print("E - Reading not defined:", dev, reading)
        return reads

    def getFhemState(self, timeout=0.1):
        '''Get FHEM state of all devices, returns a large JSON object with
        every single FHEM device and reading state
        :param timeout: timeout for reply'''
        if self.connection:
            return self.sendRcvCmd("jsonlist2", blocking=False,
                                   timeout=timeout)
        else:
            if self.loglevel > 0:
                print("E - Failed to get fhem state - not connected.")
            return {}


class FhemEventQueue:
    '''Creates a thread that listens to FHEM events and dispatches them to
    a Python queue.'''
    def __init__(self, server,  que, port=7072,
                 bSsl=False, password="", filterlist=None, timeout=0.1,
                 eventtimeout=60, serverregex=None, loglevel=1):
        ''':param server: FHEM server address
        :param que: Python Queue object, receives FHEM events as dictionaries
        :param port: FHEM telnet port
        :param port: telnet port of server
        :param bSsl: boolean for SSL (TLS)
        :param passord: (global) telnet password
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
        self.informcmd = "inform timer"
        if serverregex is not None:
            self.informcmd += " " + serverregex
        self.fhem = Fhem(server=server, port=port, bSsl=bSsl,
                         password=password, loglevel=loglevel)
        self.fhem.connect()
        self.EventThread = threading.Thread(target=self._EventWorkerThread,
                                            args=(que, filterlist,
                                                  timeout, eventtimeout))
        self.EventThread.setDaemon(True)
        self.EventThread.start()

    def _EventWorkerThread(self, que, filterlist, timeout=0.1,
                           eventtimeout=120):
        self.fhem.sendCmd(self.informcmd)
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
                self.fhem.sendCmd(self.informcmd)
                if self.fhem.connected() is True:
                    lastreceive = time.time()
            if self.fhem.connected() is True:
                data = self.fhem.recvNonblocking(timeout)
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
