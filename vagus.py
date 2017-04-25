#!/usr/bin/env python
import Config
import argparse
import logging
import logging.config
import UDPHandler
import UDPMulticastHandler
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

logger.debug("Initializing UDP")
if not UDPHandler.initialize():
	sys.exit(2)

logger.debug("Initializing UDP multicast")
if not UDPMulticastHandler.initialize():
	sys.exit(2)

logger.debug("Initializing client handler")
ci = ClientInterface(Config.client_port)
if not ci.start():
	sys.exit(2)

logger.debug("starting announcement generator")
if not AnnouncementGenerator.initialize():
	sys.exit(2)

logger.info("vagus initialized")
