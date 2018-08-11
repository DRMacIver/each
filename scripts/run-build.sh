#!/usr/bin/env bash

set -e -u -x

black --check src tests setup.py
isort -rc --check src tests setup.py
flake8 src tests setup.py
coverage run --branch -m pytest tests/
pipenv run coverage report --show-missing --fail-under=100
