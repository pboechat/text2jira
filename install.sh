#!/bin/bash

if [ -d venv ]; then
    echo venv directory already exist.
    exit 0
fi

if ! which python3 >/dev/null; then
    echo python3 is not installed.
    exit 0
fi

if ! which pip3 >/dev/null; then
    echo pip3 is not installed.
    exit 0
fi

python3 -m venv venv

source venv/bin/activate

# update pip to the latest version
python3 -m pip install -U pip

pip3 install -e .
