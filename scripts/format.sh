#!/usr/bin/env bash

set -e -u -x

cd "$(dirname $0)"/..

pipenv run black src tests setup.py
pipenv run isort -rc src tests setup.py
