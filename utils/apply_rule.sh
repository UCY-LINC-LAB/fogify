#!/usr/bin/env bash
PID=${1}
INTERFACE=${2}
RULE=${3}
RULE_OUT=${4}
ext_ingress=ifb${5}
CREATE=${6}
#IPS_FILTERS=${7}
#fogify_edge-node-bronx.1.wkxorku5pi2l52z78d4tfwdx9 internet  delay 15ms  rate 10Mbps  loss 0.0001   delay 15ms  rate 10Mbps  loss 0.0001  wkxorku5pi TRUE

if [ $CREATE = 'TRUE' ]
then
    #create virtual interface
    nsenter -t $PID -n modprobe ifb
    echo 1
    nsenter -t $PID -n ip link add $ext_ingress type ifb
    echo 2
    nsenter -t $PID -n ifconfig $ext_ingress up # begin the virtual interface
    echo 3
    # Create ingress on external interface
    nsenter -t $PID -n tc qdisc add dev $INTERFACE handle ffff: ingress
    echo 4
    #redirect traffic to ext_ingress
    nsenter -t $PID -n tc filter add dev $INTERFACE parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev $ext_ingress
    echo 5
    # nsenter -t $PID -n tc qdisc add dev $ext_ingress root handle 1: htb default 11

fi
echo 6
nsenter -t $PID -n tc qdisc del dev $INTERFACE root  #fogify_edge-node-bronx.1.fkmb32v61bzkeutddjhr7ujpl region_bronx  'delay 5ms  rate 100Mbps  loss 0.0001'   'delay 5ms  rate 100Mbps' loss 0.0001'  fkmb32v61b TRUE
echo 7
nsenter -t $PID -n tc qdisc del dev $ext_ingress root

#########
# INGRESS
#########
echo 8
nsenter -t $PID -n tc qdisc add dev $INTERFACE root netem $RULE
echo 9
#########
# EGRESS
#########

#nsenter -t $PID -n tc qdisc add dev $ext_ingress root

nsenter -t $PID -n tc qdisc add dev $ext_ingress handle 1: root htb direct_qlen 100000
echo 10

nsenter -t $PID -n tc class add dev $ext_ingress parent 1: classid 1:1 htb rate 10000mbit
echo 11
nsenter -t $PID -n tc class add dev $ext_ingress parent 1:1 classid 1:11 htb rate 10000mbit
echo 12
nsenter -t $PID -n tc qdisc add dev $ext_ingress parent 1:11 handle 10: netem $RULE_OUT
echo 13


#nsenter -t $PID -n tc class add dev $ext_ingress parent 1:1 classid 1:12 htb rate 1000Mbps
#nsenter -t $PID -n tc qdisc add dev $ext_ingress parent 1:12 handle 12: netem delay 2500ms
#nsenter -t $PID -n tc filter add dev $ext_ingress protocol ip prio 1 u32 match ip src 10.0.13.5 flowid 1:12
#nsenter -t $PID -n tc filter add dev $ext_ingress protocol ip prio 1 u32 match ip src 10.0.13.7 flowid 1:12

#nsenter -t $PID -n tc class add dev $ext_ingress parent 1:1 classid 1:13 htb rate 1000Mbps
#nsenter -t $PID -n tc qdisc add dev $ext_ingress parent 1:13 handle 13: netem delay 800ms
#nsenter -t $PID -n tc filter add dev $ext_ingress protocol ip prio 1 u32 match ip src 10.0.13.7 flowid 1:13
#
#
#nsenter -t $PID -n tc class add dev $ext_ingress parent 1:1 classid 1:14 htb rate 1000Mbps
#nsenter -t $PID -n tc qdisc add dev $ext_ingress parent 1:14 handle 14: netem delay 100ms
#nsenter -t $PID -n tc filter add dev $ext_ingress protocol ip prio 1 u32 match ip src 10.0.13.10 flowid 1:14

##echo 1
#nsenter -t $PID -n tc class add dev $ext_ingress parent 1: classid 1:1  htb rate 1000Mbps
#
#nsenter -t $PID -n tc qdisc add dev $ext_ingress root handle 1: netem $RULE_OUT
#
##echo 1
#nsenter -t $PID -n tc class add dev $ext_ingress parent 1:1 classid 1:11 htb rate 1000Mbps
##echo 1
#nsenter -t $PID -n tc class add dev $ext_ingress parent 1:1 classid 1:12 htb rate 1000Mbps
##echo 1
#nsenter -t $PID -n tc qdisc add dev $ext_ingress parent 1:11 handle 10: netem delay 0ms
##echo 1
#nsenter -t $PID -n tc qdisc add dev $ext_ingress parent 1:12 handle 20: netem delay 2500ms
##echo 1
#nsenter -t $PID -n tc filter add dev $ext_ingress protocol ip prio 1 u32 match ip dst 172.19.0.3 flowid 1:11
#nsenter -t $PID -n tc filter add dev $ext_ingress protocol ip prio 1 u32 match ip dst 10.0.13.5 flowid 1:12


#rm -f "/var/run/netns"