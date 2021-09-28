# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
# 
# SPDX-License-Identifier: GPL-3.0-or-later

sudo modprobe vcan
sudo modprobe can-gw
sudo apt-get install can-utils
sudo ip link add dev vcan0 type vcan
sudo ip link add dev vcan1 type vcan
sudo ip link add dev vcan2 type vcan
sudo ip link set up vcan0
sudo ip link set up vcan1
sudo ip link set up vcan2
sudo cangw -A -s vcan0 -d vcan1 -e
sudo cangw -A -s vcan1 -d vcan2 -e
