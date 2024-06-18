#!/bin/bash

ip rule add fwmark 1 table 100
ip route add local default dev lo table 100

# PREROUTING
iptables -t mangle -N XRAY

iptables -t mangle -A XRAY -p tcp -m socket --transparent -j MARK --set-mark 1
iptables -t mangle -A XRAY -p udp -m socket --transparent -j MARK --set-mark 1
iptables -t mangle -A XRAY -m socket -j RETURN

iptables -t mangle -A XRAY -d 0.0.0.0/8 -j RETURN
iptables -t mangle -A XRAY -d 10.0.0.0/8 -j RETURN
iptables -t mangle -A XRAY -d 127.0.0.0/8 -j RETURN
iptables -t mangle -A XRAY -d 169.254.0.0/16 -j RETURN
iptables -t mangle -A XRAY -d 172.16.0.0/12 -j RETURN
iptables -t mangle -A XRAY -d 192.168.0.0/16 -j RETURN
iptables -t mangle -A XRAY -d 224.0.0.0/4 -j RETURN
iptables -t mangle -A XRAY -d 240.0.0.0/4 -j RETURN

iptables -t mangle -A XRAY -p tcp -j TPROXY --on-port 12345 --tproxy-mark 1

iptables -t mangle -A PREROUTING -j XRAY

# OUTPUT
iptables -t mangle -N XRAY_MASK

iptables -t mangle -A XRAY_MASK -m owner --gid-owner proxy -j RETURN

iptables -t mangle -A XRAY_MASK -d 0.0.0.0/8 -j RETURN
iptables -t mangle -A XRAY_MASK -d 10.0.0.0/8 -j RETURN
iptables -t mangle -A XRAY_MASK -d 127.0.0.0/8 -j RETURN
iptables -t mangle -A XRAY_MASK -d 169.254.0.0/16 -j RETURN
iptables -t mangle -A XRAY_MASK -d 172.16.0.0/12 -j RETURN
iptables -t mangle -A XRAY_MASK -d 192.168.0.0/16 -j RETURN
iptables -t mangle -A XRAY_MASK -d 224.0.0.0/4 -j RETURN
iptables -t mangle -A XRAY_MASK -d 240.0.0.0/4 -j RETURN

iptables -t mangle -A XRAY_MASK -j MARK --set-mark 1

iptables -t mangle -A OUTPUT -p tcp -j XRAY_MASK

python3 /usr/local/bin/client.py