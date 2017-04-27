#!/bin/bash

cd __BIN_DIRECTORY__ || exit

python vagus_webserver.py --loggingconf __CONF_DIRECTORY__/logging_webserver.conf
