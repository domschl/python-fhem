import os
import sys
import shutil
import logging
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

import tarfile

import fhem

"""
FhemSelfTester implements necessary functionality for automatic testing of FHEM
with the Python API.
This module can automatically download, install and run a clean FHEM server.
"""


class FhemSelfTester:
    def __init__(self):
        self.log = logging.getLogger('SelfTester')

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
            with open(filename, 'wb') as f:
                f.write(dat)
        except Exception as e:
            self.log.error("Failed to write {}, {}".format(filename, e))
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
                "Archive needs to be of type *.tar.gz: {}".format(archivename))
            return False
        if not os.path.exists(archivename):
            self.log.error("Archive {} not found.".format(archivename))
            return False
        if "fhem" not in destination or not os.path.exists(sanity_check_file):
            self.log.error(
                "Dangerous or inconsistent fhem install-path: {}, need destination with 'fhem' in name.".format(destination))
            return False
        if os.path.exists(destination):
            try:
                shutil.rmtree(destination)
            except Exception as e:
                self.log.error(
                    "Failed to remove existing installation at {}".format(destination))
                return False
        try:
            tar = tarfile.open(archivename, "r:gz")
            tar.extractall(destination)
            tar.close()
        except Exception as e:
            self.log.error("Failed to extract {}, {}".format(archivename, e))
        return True

    def is_running(self, fhem_url='localhost', protocol='http', port=8083):
        """
        Check if an fhem server is already running.
        """
        fh = fhem.Fhem(fhem_url, protocol=protocol, port=port)
        ver = fh.send_cmd('version')
        if ver is not None:
            fh.close()
            return ver
        return None

    def shutdown(self, fhem_url='localhost', protocol='http', port=8083):
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


def create_device(fhem, name, readings):
    fhem.send_cmd("define {} dummy".format(name))
    fh.send_cmd("attr {} setList state:on,off".format(name))
    fh.send_cmd("set {} on".format(name))
    readingList = ""
    for rd in readings:
        if readingList != "":
            readingList += " "
        readingList += rd
    fh.send_cmd("attr {} readingList {}".format(name, readingList))
    for rd in readings:
        fh.send_cmd("setreading {} {} {}".format(name, rd, readings[rd]))


if __name__ == '__main__':
    st = FhemSelfTester()
    config = {
        'archivename': "./fhem-5.9.tar.gz",
        'urlpath': "https://fhem.de/fhem-5.9.tar.gz",
        'destination': "./fhem",
        'fhem_file': "./fhem/fhem-5.9/fhem.pl",
        'exec': "cd fhem/fhem-5.9/ && perl fhem.pl fhem.cfg",
        'testhost': 'localhost',
        'protocol': 'http',
        'port': 8083
    }

    if st.is_running(fhem_url=config['testhost'], protocol='http', port=8083) is not None:
        print("Fhem is already running!")
        st.shutdown(fhem_url=config['testhost'], protocol='http', port=8083)
        time.sleep(1)
        if st.is_running(fhem_url=config['testhost'], protocol='http', port=8083) is not None:
            print("Shutdown failed!")
            sys.exit(-3)
        print("--------------------")
        print("Reinstalling FHEM...")

    if not st.download(config['archivename'], config['urlpath']):
        print("Download failed.")
        sys.exit(-1)

# WARNING! THIS DELETES ANY EXISTING FHEM SERVER at 'destination'!
# All configuration files, databases, logs etc. are DELETED to allow a fresh test install!
    if not st.install(config['archivename'], config['destination'], config['fhem_file']):
        print("Install failed")
        sys.exit(-2)

    os.system(config['exec'])
    time.sleep(1)

    if st.is_running(fhem_url=config['testhost'], protocol='http', port=8083) is None:
        print("Fhem is NOT running after install and start!")
        sys.exit(-4)

    print("Install should be ok, Fhem running.")

    fh = fhem.Fhem(config['testhost'], protocol='http', port=8083)

    devs = [
        {'name': 'clima_sensor1',
         'readings': {'temperature': 18.2,
                      'humidity': 88.2}},
        {'name': 'clima_sensor2',
         'readings': {'temperature': 19.1,
                      'humidity': 85.7}}
    ]

    for dev in devs:
        create_device(fh, dev['name'], dev['readings'])

    for dev in devs:
        for rd in dev['readings']:
            value = fh.get_dev_reading(dev['name'], rd)
            if value == dev['readings'][rd]:
                print(
                    "Reading-test {},{}={} ok.".format(dev['name'], rd, dev['readings'][rd]))
            else:
                print("Failed to set and read reading! {},{} != {}".format(
                    dev['name'], rd, dev['readings'][rd]))
                sys.exit(-5)

    fh.close()

    sys.exit(0)
