#!/usr/bin/env python
import Config
import argparse
import logging
import logging.config
import UDPHandler
from ClientInterface import ClientInterface
import AnnouncementGenerator
import sys

parser = argparse.ArgumentParser(description="Vagus")
parser.add_argument("--loggingconf",type=str,default="logging.dev.conf")
parser.add_argument("--config_file",type=str,default="vagus.ini")
parser.add_argument("command",type=str,default="run",nargs='?',choices=["run","checkconfig"])

args=parser.parse_args()

if not Config.initialize(args.config_file):
	sys.exit(1)
if args.command=="checkconfig":
	print "Configuration appears ok"
	sys.exit(0)

logging.config.fileConfig(args.loggingconf)

logger = logging.getLogger(__name__)
logger.info("vagus initializing")

logger.debug("Reading configuration")
UDPHandler.initialize()
logger.debug("Initializing client handler")
ci = ClientInterface(Config.client_port)
ci.start()
logger.debug("starting announcement generator")
AnnouncementGenerator.initialize()

logger.info("vagus initialized")
