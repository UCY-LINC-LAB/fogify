#!/usr/bin/env bash
INTERFACE=${1}
RULE=${2}
RULE_OUT=${3}
ext_ingress=ifb${4}
CREATE=${5}

if [ "$CREATE" = "true" ]
then
    #create virtual interface
    modprobe ifb
    ip link add "$ext_ingress" type ifb
    ifconfig "$ext_ingress" up # begin the virtual interface
    # Create ingress on external interface
    tc qdisc add dev "$INTERFACE" handle ffff: ingress
    #redirect traffic to ext_ingress
    tc filter add dev "$INTERFACE" parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev "$ext_ingress"
    # nsenter -t $PID -n tc qdisc add dev $ext_ingress root handle 1: htb default 11

fi

tc qdisc del dev "$INTERFACE" root
tc qdisc del dev "$ext_ingress" root

#########
# INGRESS
#########
tc qdisc add dev $INTERFACE root netem $RULE

#########
# EGRESS
#########

tc qdisc add dev "$ext_ingress" handle 1: root htb direct_qlen 100000

tc class add dev "$ext_ingress" parent 1: classid 1:1 htb rate 10000mbit

tc class add dev "$ext_ingress" parent 1:1 classid 1:11 htb rate 10000mbit

tc qdisc add dev "$ext_ingress" parent 1:11 handle 10: netem $RULE_OUT

