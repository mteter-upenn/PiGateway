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

function turn_on_led
{
    if [ "$OSTYPE" == "linux-gnueabihf" ]; then
        gpio -g mode 17 out
        gpio -g write 17 1
    fi
}


FLAGFILE=/var/run/pigw-already-started
ignore_flagfile=0

# get arguments
while [ "$1" != "" ]; do
    case $1 in
        -i | --ignore-flagfile )    ignore_flagfile=1
                                    ;;
        * )                         ;;
    esac
    shift
done

# test for flagfile, exit if it exists, otherwise create to make hold
if [[ -e $FLAGFILE && $ignore_flagfile != 1 ]]; then
    exit 0
else
    touch $FLAGFILE
fi

turn_on_led

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

# We never were able to get online. Kill script and relase flagfile.
if (( $IS_ONLINE == 0 )); then
    if [[ -e $FLAGFILE ]]; then
        rm $FLAGFILE
    fi
    exit 1
fi

# Now we enter our normal code here. The above was just for online checking
#touch $FLAGFILE

# BE SURE TO CHANGE DIRECTORIES IF NEEDED!!!!!
sudo -u fresep screen -dmS first-screen bash -c 'cd /home/fresep/pckt_caps; exec bash'

sudo -u fresep screen -dmS bacnet-modbus bash -c 'sudo /home/fresep/PiGateway/PiGateway.py --ini /home/fresep/PATH/TO/.ini --debug modbusregisters.ModbusPollThread modbusbacnetclasses.ModbusAnalogInputObject; cd /home/fresep/PiGateway; exec bash'
# useful debugs
# modbusbacnetclasses.ModbusAnalogInputObject - bacnet point, will show when requests are made
# modbusbacnetclasses.UpdateObjectsFromModbus - shows values transferred from modbus cache to bacnet points
# modbusregisters.ModbusPollThread - will show more condensed modbus requests and receipts
# modbusserver - will show more raw modbus requests and receipts
# bacpypes.core.run -
