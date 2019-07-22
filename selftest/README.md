## Automatic FHEM installation and self-test for CI.

The selftest tree is only used for continous integration with TravisCI.

The scripts automatically download the latest FHEM release, install  and run it and then use the Python API to 
perform self-tests.

**Note**: Be careful when using this script, e.g. the install-class ***completely erases*** the existing FHEM installation
within the selftest tree (and all configuration files) to allow clean tests.
