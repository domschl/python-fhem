#!/bin/bash

pip uninstall fhem
./publish.sh
pip install fhem/dist/fhem-0.7.0.tar.gz
cd selftest
python selftest.py

