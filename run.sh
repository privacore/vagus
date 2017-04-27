#!/bin/bash

cd __BIN_DIRECTORY__ || exit

python vagus.py --loggingconf __CONF_DIRECTORY__/logging.conf --config_file __CONF_DIRECTORY__/vagus.ini
