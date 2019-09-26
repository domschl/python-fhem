## Automatic FHEM installation and python-fhem API self-test for CI.

The selftest tree is only used for continous integration with TravisCI.

The scripts automatically download the latest FHEM release, install, configure and run it and then use the Python API to 
perform self-tests.

Tests performed:
* All tests are run with both python 2.7 and python 3.x
* FHEM connections via sockets, secure sockets, HTTP and HTTPS with password.
* Automatic creation of devices on Fhem (using all connection variants)
* Aquiring readings from Fhem using all different connection types and python versions

**WARNING**: Be careful when using this script, e.g. the install-class ***completely erases*** the existing FHEM installation
within the selftest tree (and all configuration files) to allow clean tests.

### Environment notes

Fhem requires the perl module IO::Socket::SSL for secure socket and HTTPS protocotls.

It needs to be installed with either:

* `cpan -i IO::Socket::SSL` 
* or `apt-get install libio-socket-ssl-perl`
* or `pacman -S perl-io-socket-ssl`

If selftests fails on the first SSL connection, it is usually a sign, that the fhem-perl requirements for SSL are not installed.