## Automatic FHEM installation and python-fhem API self-test for CI.

The selftest can be used manually, but are targeted for use with github action CI.

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

## Manual test run

- Install `python-fhem`, e.g. by `pip install -e .` in the fhem source directory.
- Make sure that Perl's `socke::ssl` is installed (s.a.)
- Run `python selftest.py`

## History

- 2023-08-17: Updated for FHEM 6.0, python 2.x support removed. Prepared move from Travis CI to github actions.
