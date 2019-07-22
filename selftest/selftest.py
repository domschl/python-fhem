import os
import sys
import shutil
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

import tarfile


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

    def install(self, archivename, destination):
        if not archivename.endswith("tar.gz"):
            self.log.error(
                "Archive needs to be of type *.tar.gz: {}".format(archivename))
            return False
        if not os.path.exists(archivename):
            self.log.error("Archive {} not found.".format(archivename))
            return False
        if "fhem" not in destination:
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


if __name__ == '__main__':
    st = FhemSelfTester()
    config = {
        'archivename': "./fhem-5.9.tar.gz",
        'urlpath': "https://fhem.de/fhem-5.9.tar.gz",
        'destination': "./fhem"
    }
    if not st.download(config['archivename'], config['urlpath']):
        print("Download failed.")
        sys.exit(-1)

    if not st.install(config['archivename'], config['destination']):
        print("Install failed")
        sys.exit(-2)

    print("Install should be ok.")
    sys.exit(0)
