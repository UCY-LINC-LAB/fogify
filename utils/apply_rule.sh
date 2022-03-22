#!/usr/bin/env bash
INTERFACE=${1}
RULE=${2}
RULE_OUT=${3}
ext_ingress=ifb${4}
RATE_IN=${5}
RATE_OUT=${6}

modprobe ifb

tc qdisc del dev "$INTERFACE" root
tc qdisc del dev "$INTERFACE" ingress
tc qdisc del dev "$ext_ingress" root
ip link set dev "$ext_ingress" down
ip link delete "$ext_ingress" type ifb


ip link add "$ext_ingress" type ifb
ip link set dev "$ext_ingress" up
# ifconfig "$ext_ingress" up # begin the virtual interface
# Create ingress on external interface
tc qdisc add dev "$INTERFACE" ingress
#redirect traffic to ext_ingress
tc filter add dev "$INTERFACE" parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev "$ext_ingress"

#########
# INGRESS
#########

tc qdisc add dev "$INTERFACE" root handle 2: htb default 11
tc class add dev "$INTERFACE" parent 2: classid 2:1 htb rate $RATE_IN ceil 0.0Kbit burst 0.0KB cburst 0.0KB
tc class add dev "$INTERFACE" parent 2:1 classid 2:11 htb rate $RATE_IN ceil 0.0Kbit burst 0.0KB cburst 0.0KB
tc qdisc add dev "$INTERFACE" parent 2:11 handle 24ea: netem $RULE
tc filter add dev "$INTERFACE" protocol ip parent 2: prio 5 u32 match ip dst 0.0.0.0/0 match ip src 0.0.0.0/0 flowid 2:11

#########
# EGRESS
#########

tc qdisc add dev "$ext_ingress" root handle 1: htb default 11
tc class add dev "$ext_ingress" parent 1: classid 1:1 htb rate $RATE_OUT ceil 0.0Kbit burst 0.0KB cburst 0.0KB
tc class add dev "$ext_ingress" parent 1: classid 1:11 htb rate $RATE_OUT ceil 0.0Kbit burst 0.0KB cburst 0.0KB
tc qdisc add dev "$ext_ingress" parent 1:11 handle 14ea: netem $RULE_OUT
tc filter add dev "$ext_ingress" protocol ip parent 1: prio 5 u32 match ip dst 0.0.0.0/0 match ip src 0.0.0.0/0 flowid 1:11

