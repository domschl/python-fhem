#!/bin/bash

if [ ! -f ~/.pypirc ]; then
    echo "Please configure .pypirc for pypi access first"
    exit -2
fi
if [[ ! -d fhem/dist ]]; then
    mkdir fhem/dist
fi
cd fhem
cp ../README.md .
rm dist/*
export PIP_USER=
python -m build
if [[ $1 == "upload" ]]; then
  twine upload dist/*
fi
