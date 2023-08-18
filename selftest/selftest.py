import os
import sys
import shutil
import logging
import time
import queue
import subprocess
import argparse

from urllib.parse import quote
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError
from urllib.request import HTTPSHandler
from urllib.request import HTTPPasswordMgrWithDefaultRealm
from urllib.request import HTTPBasicAuthHandler
from urllib.request import build_opener
from urllib.request import install_opener
import tarfile

import fhem

"""
FhemSelfTester implements necessary functionality for automatic testing of FHEM
with the Python API.
This module can automatically download, install and run a clean FHEM server.
"""


class FhemSelfTester:
    def __init__(self):
        self.log = logging.getLogger("SelfTester")

    def download(self, filename, urlpath):
        """
        Download an FHEM tar.gz file, if not yet available locally.
        """
        if os.path.exists(filename):
            return True
        try:
            dat = urlopen(urlpath).read()
        except Exception as e:
            self.log.error("Failed to download {}, {}".format(urlpath, e))
            return False
        try:
            with open(filename, "wb") as f:
                f.write(dat)
        except Exception as e:
            self.log.error("Failed to write {}, {}".format(filename, e))
            return False
        self.log.debug("Downloaded {} to {}".format(urlpath, filename))
        return True

    def install(self, archivename, destination, sanity_check_file):
        """
        Install a NEW, DEFAULT FHEM server.
        WARNING: the directory tree in destination is ERASED! In order to prevent
        accidental erasures, the destination direction must contain 'fhem' and the fhem.pl
        file at sanity_check_file must exist.
        OLD INSTALLATIONS ARE DELETE!
        """
        if not archivename.endswith("tar.gz"):
            self.log.error(
                "Archive needs to be of type *.tar.gz: {}".format(archivename)
            )
            return False
        if not os.path.exists(archivename):
            self.log.error("Archive {} not found.".format(archivename))
            return False
        if "fhem" not in destination or (
            os.path.exists(destination) and not os.path.exists(sanity_check_file)
        ):
            self.log.error(
                "Dangerous or inconsistent fhem install-path: {}, need destination with 'fhem' in name.".format(
                    destination
                )
            )
            self.log.error(
                "Or {} exists and sanity-check-file {} doesn't exist.".format(
                    destination, sanity_check_file
                )
            )
            return False
        if os.path.exists(destination):
            try:
                shutil.rmtree(destination)
            except Exception as e:
                self.log.error(
                    "Failed to remove existing installation at {}".format(destination)
                )
                return False
        try:
            tar = tarfile.open(archivename, "r:gz")
            tar.extractall(destination)
            tar.close()
        except Exception as e:
            self.log.error("Failed to extract {}, {}".format(archivename, e))
            return False
        self.log.debug("Extracted {} to {}".format(archivename, destination))
        return True

    def is_running(self, fhem_url="localhost", protocol="http", port=8083):
        """
        Check if an fhem server is already running.
        """
        try:
            fh = fhem.Fhem(fhem_url, protocol=protocol, port=port)
            ver = fh.send_cmd("version")
        except Exception as e:
            ver = None
        if ver is not None:
            fh.close()
            self.log.warning("Fhem already running at {}".format(fhem_url))
            return ver
        fh.close()
        self.log.debug("Fhem not running at {}".format(fhem_url))
        return None

    def shutdown(self, fhem_url="localhost", protocol="http", port=8083):
        """
        Shutdown a running FHEM server
        """
        fh = fhem.Fhem(fhem_url, protocol=protocol, port=port)
        fh.log.level = logging.CRITICAL
        try:
            self.log.warning("Shutting down fhem at {}".format(fhem_url))
            fh.send_cmd("shutdown")
        except:
            pass
        self.log.warning("Fhem shutdown complete.")


def set_reading(fhi, name, reading, value):
    fhi.send_cmd("setreading {} {} {}".format(name, reading, value))


def create_device(fhi, name, readings):
    fhi.send_cmd("define {} dummy".format(name))
    fhi.send_cmd("attr {} setList state:on,off".format(name))
    fhi.send_cmd("set {} on".format(name))
    readingList = ""
    for rd in readings:
        if readingList != "":
            readingList += " "
        readingList += rd
    fhi.send_cmd("attr {} readingList {}".format(name, readingList))
    for rd in readings:
        set_reading(fhi, name, rd, readings[rd])


if __name__ == "__main__":
    # check args for reuse (-r)
    parser = argparse.ArgumentParser(description="Fhem self-tester")
    parser.add_argument(
        "-r",
        "--reuse",
        action="store_true",
        help="Reuse existing FHEM installation",
    )
    args = parser.parse_args()
    reuse = args.reuse

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log = logging.getLogger("SelfTesterMainApp")
    log.info("Start FhemSelfTest")
    st = FhemSelfTester()
    log.info("State 1: Object created.")
    config = {
        "archivename": "./fhem-6.0.tar.gz",
        "urlpath": "https://fhem.de/fhem-6.0.tar.gz",
        "destination": "./fhem",
        "fhem_file": "./fhem/fhem-6.0/fhem.pl",
        "config_file": "./fhem/fhem-6.0/fhem.cfg",
        "fhem_dir": "./fhem/fhem-6.0/",
        "exec": "cd fhem/fhem-6.0/ && perl fhem.pl fhem.cfg",
        "cmds": ["perl", "fhem.pl", "fhem.cfg"],
        "testhost": "localhost",
    }

    installed = False
    if (
        st.is_running(fhem_url=config["testhost"], protocol="http", port=8083)
        is not None
    ):
        log.info("Fhem is already running!")
        if reuse is True:
            installed = True
        else:
            st.shutdown(fhem_url=config["testhost"], protocol="http", port=8083)
            time.sleep(1)
            if (
                st.is_running(fhem_url=config["testhost"], protocol="http", port=8083)
                is not None
            ):
                log.error("Shutdown failed!")
                sys.exit(-3)
            log.info("--------------------")
            log.info("Reinstalling FHEM...")

    if installed is False:
        if not st.download(config["archivename"], config["urlpath"]):
            log.error("Download failed.")
            sys.exit(-1)

        log.info("Starting fhem installation")

        # WARNING! THIS DELETES ANY EXISTING FHEM SERVER at 'destination'!
        # All configuration files, databases, logs etc. are DELETED to allow a fresh test install!
        if not st.install(
            config["archivename"], config["destination"], config["fhem_file"]
        ):
            log.info("Install failed")
            sys.exit(-2)

        os.system("cat fhem-config-addon.cfg >> {}".format(config["config_file"]))

        if not os.path.exists(config["config_file"]):
            log.error("Failed to create config file!")
            sys.exit(-2)

        certs_dir = os.path.join(config["fhem_dir"], "certs")
        os.system("mkdir {}".format(certs_dir))
        os.system(
            'cd {} && openssl req -newkey rsa:2048 -nodes -keyout server-key.pem -x509 -days 36500 -out server-cert.pem -subj "/C=DE/ST=NRW/L=Earth/O=CompanyName/OU=IT/CN=www.example.com/emailAddress=email@example.com"'.format(
                certs_dir
            )
        )

        cert_file = os.path.join(certs_dir, "server-cert.pem")
        key_file = os.path.join(certs_dir, "server-key.pem")
        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            log.error("Failed to create certificate files!")
            sys.exit(-2)

        # os.system(config["exec"])
        process = subprocess.Popen(config["cmds"], cwd=config['fhem_dir'],stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True)
        output, error = process.communicate()
        if process.returncode != 0:
            raise Exception("Process fhem failed %d %s %s" % (process.returncode, output, error))
        log.info("Fhem startup at {}: {}".format(config['cmds'], output.decode('utf-8')))

        retry_cnt = 2
        for i in range(retry_cnt):
            time.sleep(1)

            if st.is_running(fhem_url=config["testhost"], protocol="http", port=8083) is None:
                log.warning("Fhem is NOT (yet) running after install and start!")
                if i == retry_cnt - 1:
                    log.error("Giving up.")
                    sys.exit(-4)
            else:
                break

        log.info("Install should be ok, Fhem running.")

    connections = [
        {"protocol": "http", "port": 8083},
        {
            "protocol": "telnet",
            "port": 7073,
            "use_ssl": True,
            "password": "secretsauce",
        },
        {"protocol": "telnet", "port": 7072},
        {"protocol": "https", "port": 8086},
        {
            "protocol": "https",
            "port": 8085,
            "username": "test",
            "password": "secretsauce",
        },
    ]

    first = True
    log.info("")
    log.info("----------------- Fhem ------------")
    log.info("Testing python-fhem Fhem():")
    for connection in connections:
        log.info("Testing connection to {} via {}".format(config["testhost"], connection))
        fh = fhem.Fhem(config["testhost"], **connection)

        devs = [
            {
                "name": "clima_sensor1",
                "readings": {"temperature": 18.2, "humidity": 88.2},
            },
            {
                "name": "clima_sensor2",
                "readings": {"temperature": 19.1, "humidity": 85.7},
            },
        ]

        if first is True:
            for dev in devs:
                create_device(fh, dev["name"], dev["readings"])
            first = False

        for dev in devs:
            for i in range(10):
                log.debug("Repetion: {}, connection: {}".format(i + 1, fh.connection))
                if fh.connected() is False:
                    log.info("Connecting...")
                    fh.connect()
                for rd in dev["readings"]:
                    dict_value = fh.get_device_reading(dev["name"], rd, blocking=False)
                    try:
                        value = dict_value["Value"]
                    except:
                        log.error(
                            "Bad reply reading {} {} -> {}".format(
                                dev["name"], rd, dict_value
                            )
                        )
                        sys.exit(-7)

                    if value == dev["readings"][rd]:
                        log.debug(
                            "Reading-test {},{}={} ok.".format(
                                dev["name"], rd, dev["readings"][rd]
                            )
                        )
                    else:
                        log.error(
                            "Failed to set and read reading! {},{} {} != {}".format(
                                dev["name"], rd, value, dev["readings"][rd]
                            )
                        )
                        sys.exit(-5)

        num_temps = 0
        for dev in devs:
            if "temperature" in dev["readings"]:
                num_temps += 1
        temps = fh.get_readings("temperature", timeout=0.1, blocking=False)
        if len(temps) != num_temps:
            log.error(
                "There should have been {} devices with temperature reading, but we got {}. Ans: {}".format(
                    num_temps, len(temps), temps
                )
            )
            sys.exit(-6)
        else:
            log.info("Multiread of all devices with 'temperature' reading:   ok.")

        states = fh.get_states()
        if len(states) < 5:
            log.error("Iconsistent number of states: {}".format(len(states)))
            sys.exit(-7)
        else:
            log.info("states received: {}, ok.".format(len(states)))
        fh.close()

    log.info("---------------Queues--------------------------")
    log.info("Testing python-fhem telnet FhemEventQueues():")
    for connection in connections:
        if connection["protocol"] != "telnet":
            continue
        log.info("Testing connection to {} via {}".format(config["testhost"], connection))
        fh = fhem.Fhem(config["testhost"], **connections[0])

        que = queue.Queue()
        que_events = 0
        fq = fhem.FhemEventQueue(config["testhost"], que, **connection)

        devs = [
            {
                "name": "clima_sensor1",
                "readings": {"temperature": 18.2, "humidity": 88.2},
            },
            {
                "name": "clima_sensor2",
                "readings": {"temperature": 19.1, "humidity": 85.7},
            },
        ]
        time.sleep(1.0)
        for dev in devs:
            for i in range(10):
                log.debug("Repetion: {}".format(i + 1))
                for rd in dev["readings"]:
                    set_reading(fh, dev["name"], rd, 18.0 + i / 0.2)
                    que_events += 1
                    time.sleep(0.05)

        time.sleep(3)  # This is crucial due to python's "thread"-handling.
        ql = 0
        has_data = True
        while has_data:
            try:
                que.get(False)
            except:
                has_data = False
                break
            que.task_done()
            ql += 1

        log.debug("Queue length: {}".format(ql))
        if ql != que_events:
            log.error(
                "FhemEventQueue contains {} entries, expected {} entries, failure.".format(
                    ql, que_events
                )
            )
            sys.exit(-8)
        else:
            log.info("Queue test success, Ok.")
        fh.close()
        fq.close()
        time.sleep(0.5)

    log.info("All tests successfull.")
    sys.exit(0)
