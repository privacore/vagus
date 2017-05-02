# Vagus - A heartbeat/keepalive daemon
Vagus is daemon that can exchange alive-information from instances so clients can get an overview of what is alive. It is meant to scale to at least 50 hosts.

It supports:
  * IPv4 and IPv6
  * UDP unicast
  * UDP broadcast
  * UDP multicast
  * Multiple namespaces/clusters

It is not a full-fledged HA system. It merely provices a mechanism for building a HA system.

# Platforms
Tested on:
  * Python 2.7.6
  * Linux 3+

It will not work on Windows because it needs to discover network interfaces and addresses using the getifdaddrs() system call.

# Background
It was built for use in https://github.com/privacore/open-source-search-engine

The name Vagus comes from the vagus nerve which partially controls the human heart.
