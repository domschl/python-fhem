## Automatic FHEM installation and python-fhem API self-test for CI.

The selftest can be used manually, but are targeted for use with github action CI.

The scripts automatically download the latest FHEM release, install, configure and run it and then use the Python API to 
perform self-tests.

Tests performed:
* FHEM connections via sockets, secure sockets, HTTP and HTTPS with password.
* Automatic creation of devices on Fhem (using all connection variants)
* Aquiring readings from Fhem using all different connection types and python versions
* Automatic testing of the FhemEventQueue

**WARNING**: Be careful when using this script, e.g. the install-class ***completely erases*** the existing FHEM installation
within the selftest tree (and all configuration files) to allow clean tests.

### Environment notes

Fhem requires the perl module IO::Socket::SSL for secure socket and HTTPS protocotls.

It needs to be installed with either:

* `cpan -i IO::Socket::SSL` 
* or `apt-get install libio-socket-ssl-perl`
* or `pacman -S perl-io-socket-ssl`

If selftests fails on the first SSL connection, it is usually a sign that the fhem-perl requirements for SSL are not installed.

## Manual test run

- Make sure `python-fhem` is installed (e.g. `pip install fhem`)
- Make sure that Perl's `socket::ssl` is installed (s.a.)
- Run `python selftest.py`

You can run the selftest with option `--reuse` to reuse an existing and running FHEM installation. The selftest requires a number of 
ports and passwords to be configured. Check out `fhem-config-addon.cfg` for details.

## CI notes

The selftest can be used for CI testing. It is currently used with github actions. Be aware that port `8084` is not available on github actions.
See `.github/workflows/python-fhem-test.yaml` for details.

## History

- 2023-08-17: Updated for FHEM 6.0, python 2.x support removed. Prepared move from Travis CI to github actions.
