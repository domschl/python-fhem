#!/bin/bash

if [ ! -f ~/.pypirc ]; then
    echo "Please configure .pypirc for pypi access first"
    exit -2
fi
cd fhem
cp ../README.md .
rm dist/*
export PIP_USER=
python -m build
# twine upload dist/*

