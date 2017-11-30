#!/bin/bash

function check_online
{
# netcat
#    -z: zero-I/O mode used for scanning
#    -w 5: timeout in seconds
#    DNS_IP: ip of DNS server (8.8.8.8 is google, use local dns server for gateways on lans)
#    DNS_PORT: should be 53
    netcat -z -w 5 DNS_IP 53 && echo 1 || echo 0
#    netcat -z -w 5 8.8.8.8 53 && echo 1 || echo 0
}


FLAGFILE=/var/run/pigw-already-started

if [[ -e $FLAGFILE ]]; then
    exit 0
#else
#    touch $FLAGFILE
fi

# Initial check to see if we're online
IS_ONLINE=$( check_online )
# How many times we should check if we're online - prevents infinite looping
MAX_CHECKS=5
# Initial starting value for checks
CHECKS=0

# Loop while we're not online.
while (( $IS_ONLINE == 0 ));do
    # We're offline. Sleep for a bit, then check again

    sleep 10;
    IS_ONLINE=$( check_online )

    CHECKS=$(( $CHECKS + 1 ))
    if [ $CHECKS -gt $MAX_CHECKS ]; then
        break
    fi
done

if (( $IS_ONLINE == 0 )); then
    # We never were able to get online. Kill script.
    exit 1
fi

# Now we enter our normal code here. The above was just for online checking
touch $FLAGFILE

# BE SURE TO CHANGE DIRECTORIES IF NEEDED!!!!!
#echo 'start python3 env'
sudo -u fresep screen -dmS first-screen bash -c 'cd /home/fresep/bacpypes; exec bash'
#sudo -u fresep screen -ls
#echo 'start bacnet modbus script'
sudo -u fresep screen -dmS bacnet-modbus bash -c 'sudo /home/fresep/PiGateway/PiGateway.py --ini /home/fresep/PATH/TO/.ini --debug bacpypes.core.run; exec bash'
#modbusbacnetclasses.UpdateObjectsFromModbus
#sudo -u fresep screen -ls
