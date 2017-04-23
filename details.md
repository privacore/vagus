# Overview
Vagus is a building block for keeping track of which services/instances/servers/things are alive. It does not actively probe instances, so the instances have to tell it that it is alive. Vagus supports multiple clusters/namespaces and the easiest installation is to just install one on every host.
As well as distributing alike-information it also supports piggy-backing small pieces for information per instance.
```
    +-------------------+                          +-------------------+
    | host A            |                          | host B            |
    |                   |   inter-vagus protocol   |                   |
    | vagus A...........|..........................|.vagus B           |
    |   ^               |                          |   ^               |
    |   +--- instance 1 |                          |   +--- instance 4 |
    |   +----instance 2 |                          |   +----instance 5 |
    |   +----instance 3 |                          |   +----instance 6 |
    |                   |                          |                   |
    +-------------------+                          +-------------------+
```

# Goals
1. Rapidly stabilize efter power loss
2. Rapidly distrbute alive-information to the whole system
3. Scale to at least 50 hosts
4. Scale to at least 1000 instances in total
5. Be able to cross networks
6. Use UDP multicast and broadcast to lower the load on the network

# Non-goals
1. Detect "split brain"
2. Keeping history of what has once been alive
3. Knowing what should be alive
4. HA, quorums, vector clocks, etc.

# Assumptions
* Secure network
  It is assumed that the network is secure. Vagus is not designed to operate over an insecure network.
* Trusted clients
  It is assummed that the clients are non-malicious.
* Synchronized clocks
  it is assumed that the host clocks are synchronized to a tolerance well below any timeouts used in the messages. NTP is sufficient. Cron-driven 'rdate' is not recommended.


# Protocols
Vagus uses two protocols:
1. client protocol
2. inter-vagus protocol

## Client -> Vagus protocol
The client protocol is text-based. Vagus acts as a TCP server. The client sends a single line with a command terminated by NL (or CR+NL). The server responds with a multi-line response terminated by an empty line. If a connection is lost to a client it is not interpreted as the instances reported by that client is dead. If a command is malformatted the server simply cuts the connection.

The clients are normally instances. The main operation on the protocol is clients issuing `keepalive` or `keepalivepoll` commands repeatedly in an interval of their of choice.

### Parameters used in the commands:
* cluster-identifier
  Vagus supports multiple clusters/namespaces. The cluster identifier is chosen by the clients and is typically the service name. Eg. if a client is a WebWaffle service then "webwaffle" would be an obvious cluster name. The identifier cannot contain a colon.
* instance-identifier
  The id of the instance. It must be unique within a cluster. The identifier cannot contain a colon.
* keepalive lifetime
  The valid lifetime of a keepalive expressed in milliseconds.
* optional: extra information
  If present, this extra information is distributed and is available via the `keepalivepoll` and `poll` commands.
* vagus-identifier
  A unique identifier of a vagus. It must be gloablly unique across all clusters. It is typically the hostname.

### getversion command
This commands asks the server about the supported protocol version

Example:
```
Client:
  getversion <NL>
Server:
  1 <NL>
  <NL>
```

### keepalive command
This commands servers as an instance registration and as a keepalive.

Command parameters (colon-separated)
* cluster-identifier
* instance-identifier
* keepalive lifetime
* optional: extra information

If a client specifies eg. 2500ms as the valid lifetime of the keepalive then if a new keepalive has not been received within 2500ms the registration times out and is deleted.

Example 1 (plain):
```
Client:
  keepalive giraffes:1:2500
Server:
  <NL>
```

Example 2 (with piggy-backed information):
```
Client:
  keepalive giraffes:1:2500:durian+icecream
Server:
  <NL>
```

### poll command
This commands retrieves a list of instances in a cluster

Command parameter:
* cluster-identifier

Command response:
* List of instances in the cluster and optionally extra-information

Example:
```
Client:
  poll giraffes <NL>
Server:
  3 <NL>
  1:durian+icecream <NL>
  2 <NL>
  5 <NL>
  289 <NL>
  <NL>
```

### keepalivepoll command
This commands functions as both an instance registration/keepalive and a poll. It is more efficient to issue this command than two separate `keepalive` and `poll` commands.

Command parameters (colon-separated)
* cluster-identifier
* instance-identifier
* keepalive lifetime
* optional: extra information

Command response:
* List of instances in the cluster and optionally extra-information

Example:
```
Client:
  keepalivepoll giraffes:1:2500
Server:
  3 <NL>
  1:durian+icecream <NL>
  2 <NL>
  5 <NL>
  289 <NL>
  <NL>
```

### getclusters command
This commands retrieves a list of clusters Vagus knows about. It is unspecified if a cluster without any live instances will be listed.

Example:
```
Client:
  getclusters <NL>
Server:
  giraffes <NL>
  penguins <NL>
  armadillos <NL>
  <NL>
```

### getvaguslist command
This commands retrieves a list of vagus processes Vagus knows about.

Example:
```
Client:
  getvaguslist <NL>
Server:
  hosta <NL>
  hostb <NL>
  hostd <NL>
  <NL>
```

### vagushint command
This command tells Vagus where another vagus may exist. This can be useful if the client has knowledge of networkse wher broadcast/multicast may not reach and are not specified in the Vagus's configuration. Only UDP unicast and TCP can be specified. UDP broadcast and multicast can only be specified in the Vagus configuration file.

Example 1 (UDP on IPv4):
```
Client:
  vagushint udp4:192.0.2.7:12345 <NL>
Server:
  <NL>
```

Example 2 (TCP on IPv6):
```
Client:
  vagushint tcp6:[2001:0db8:1::7]:12345 <NL>
Server:
  <NL>
```

## Vagus <-> Vagus protocol
The vagus processes exchange information about the alive instances they know about. A Vagus sends its alive-instance information at regular interval to all specified destinations.

The inter-Vagus protocol is binary for compactness. It has a single message type.

```
message ::= "vagus"
          | <length>
          | <message_type>
          | <payload>
length ::= 32bit integer
message_type ::= 8bit enumeration
```
The signature "vagus" is for easily identifying packets. All integers are in network order.
The only message type currently defined is 1 (announcement).

Announcement message (type 0x01) payload:
```
announcement ::= end_of_life
               | vagus_id_length | vagus_id
               | cluster_id_length | cluster
               | {instance_information}
instance_information ::= instance_id_length | instance_id
                       | end_of_life
                       | extra_information
end_of_life ::= 64bit integer
vagus_id_length ::= 8bit integer
vagus_id ::= string
cluster_id_length ::= 8bit integer
cluster_id ::= string
extra_information ::= extra_information_len | info
extra_information_len ::= 8bit integer
info ::= string
```

# Vagus configuration
Vagus can be configured, but provides built-in defaults that will work in most simple setups.

## main section
This section contains the general configuration of Vagus.

### identity
Default value: the same as the hostname.
This is the identity of the vagus. The hostname is usually a good choice.

### instance-timeout-min
Default value: 500
The minimum timeout for an instance, in milliseconds. If a client specifies an instance lifetime short than this the the actual value is raised to this minimum.

### instance-timeout-max
Default value: 600000
The minimum timeout for an instance, in milliseconds. If a client specifies an instance lifetime longer than this the the actual value is lowered to this minimum.

### announcement-interval-min
Default value: 500
The minimum interval between sending a batch of announcements to other vagus processes, in milliseconds.

### announcement-interval-max
Default value: 10000
The maximuminterval between sending a batch of announcements to other vagus processes, in milliseconds.

### client-port
Default value: 8720
Which TCP port to listen for client commands.

## udp section
This section contains configuration for how to use UDP unicast and broadcast.
If no `peer` nor any `broacast` items are specified then the default is `broacast: *`

### port
Default value: 8721
The UDP port to listen on and send to/from.

### peer
Default value: none
This item can be specified multiple times.
It specifies where to send unicasts. The value can be either an IPv4 address or an IPv6 address.
Examples:
```
peer: 192.0.2.7
peer: 2001:0db8:1::7
```

### broadcast
Default value: nono (but see comment on whole section above)
This item can be specified multiple times.
It specifies where to send broadcasts. The value comes in three forms:
  * `*` (asterisk)
    Specifies to send broadcast on all network interface on all subnets.
  * interface name (must start with a letter)
    Specifies to send broadcast on this network interface on all subnets.
  * interface name `:` broadcast-address
    Specifies to send broadcast using that specific destination on that network interface
Only IPv4 addresses (dotted-quad) is supported.

Examples:
```
broadcast: *
broadcast: eth0
broadcast: 192.0.2.255
broadcast: eth0:192.0.2.255
```
## udp-multicast section
This section specifies how to use UDP multicasts.

### port
Default value: 8721
Specifies which port listen and send to.

### multicast
Default value: none
This item can be specified multiple times.
The value takes the form of <interface-name> `:` <multicast-ip>. The interface name can be `*` in which case Vagus uses all interfaces and all networks (except loopback).

Examples:
```
multicast eth0:224.1.1.1
multicast *:224.1.1.1
multicast eth0:ff02::1
```

## tcp section

### port
Default value: 8721
Specifies which port listen on and connect to.

### peer
Default value: none
Specifies the IP-address of a peer.

Examples:
```
peer: 192.0.2.7
peer: 2001:0db8:1::7
```
```

## Example configuration:
```
[main]
identity: box-in-the-broom-cupboard
instance-timeout-min: 500
instance-timeout-max: 600000
announcement-interval-min: 500
announcement-interval-max: 10000
client-port: 12345

[udp]
port: 8721
peer: 192.0.2.7
peer: 2001:0db8:1::7
broadcast: *
broadcast: eth0
broadcast: 192.0.2.255
broadcast: eth0:192.0.2.255

[udp-multicast]
port: 8721
multicast eth0:224.1.1.1
multicast *:224.1.1.1
multicast eth0:ff02::1

[tcp]
port: 8721
peer: 192.0.2.7
peer: 2001:0db8:1::7
```
