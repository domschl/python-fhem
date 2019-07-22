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


class FhemSelfTester:
    def __init__(self):
        self.log = logging.getLogger('SelfTester')

    def download(self, filename, urlpath):
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
        fh = fhem.Fhem(fhem_url, protocol=protocol, port=port)
        ver = fh.send_cmd('version')
        if ver is not None:
            fh.close()
            return ver
        return None

    def shutdown(self, fhem_url='localhost', protocol='http', port=8083):
        fh = fhem.Fhem(fhem_url, protocol=protocol, port=port)
        fh.log.level = logging.CRITICAL
        try:
            self.log.warning("Shutting down fhem at {}".format(fhem_url))
            fh.send_cmd("shutdown")
        except:
            pass
        self.log.warning("Fhem shutdown complete.")


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
    fh.send_cmd("define grotzel dummy")
    fh.send_cmd("attr grotzel setList state:on,off")
    fh.send_cmd("set grotzel on")
    fh.send_cmd("attr grotzel readingList temperature humidity")
    fh.send_cmd("setreading grotzel temperature 10.2")
    fh.send_cmd("setreading grotzel humidity 88.9")

    temp = fh.get_dev_reading("grotzel", "temperature")
    if temp == 10.2:
        print("Reading-test ok.")
    else:
        print("Failed to set and read dummy reading!")
        sys.exit(-5)

    fh.close()

    sys.exit(0)
