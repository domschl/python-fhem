#!/bin/bash
if [ -f /etc/os-release ]; then
    # freedesktop.org and systemd
    . /etc/os-release 2>/dev/null
    OS=$NAME
    VER=$VERSION_ID
    if uname -a | grep -Fq "WSL" 2> /dev/null; then
        SUB_SYSTEM="WSL"
    fi
elif type lsb_release >/dev/null 2>&1; then
    # linuxbase.org
    OS=$(lsb_release -si)
    VER=$(lsb_release -sr)
elif [ -f /etc/lsb-release ]; then
    # For some versions of Debian/Ubuntu without lsb_release command
    . /etc/lsb-release
    OS=$DISTRIB_ID
    VER=$DISTRIB_RELEASE
fi

if [[ "$OS" == "Arch Linux" ]]; then
  echo "Arch Linux"
  pip uninstall fhem --break-system-packages
else
  echo "OS: $OS"
  pip uninstall fhem
fi
./publish.sh
if [[ "$OS" == "Arch Linux" ]]; then
  pip install fhem/dist/fhem-0.7.0.tar.gz --break-system-packages
else
  pip install fhem/dist/fhem-0.7.0.tar.gz
fi
cd selftest
python selftest.py

