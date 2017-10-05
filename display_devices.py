import os
import json
from beautifultable import BeautifulTable


table1 = BeautifulTable()
table2 = BeautifulTable()
table3 = BeautifulTable()

table1.column_headers = ['BACnet Id', 'Name', 'IP', 'Modbus Id']
table2.column_headers = ['BACnet Id', 'Description']
table3.column_headers = ['BACnet Id', 'Map Name', 'Map Rev', 'Meter Name']

dev_list = []

for dev_filename in os.listdir(os.getcwd() + '/DeviceList'):
    if dev_filename.endswith('.json'):  # and fn.startswith('DRL'):
        json_raw_str = open(os.getcwd() + '/DeviceList/' + dev_filename, 'r')
        map_dict = json.load(json_raw_str)

        dev_list.append([map_dict['deviceInstance'], map_dict['deviceName'], map_dict['deviceIP'], map_dict['modbusId'],
                         map_dict['deviceDescription'], map_dict['mapName'], map_dict['mapRev'],
                         map_dict['meterModelName']])

        json_raw_str.close()

dev_list.sort()

for ii in range(len(dev_list)):
    table1.append_row([dev_list[ii][0], dev_list[ii][1], dev_list[ii][2], dev_list[ii][3]])
    table2.append_row([dev_list[ii][0], dev_list[ii][4]])
    table3.append_row([dev_list[ii][0], dev_list[ii][5], dev_list[ii][6], dev_list[ii][7]])

print(table1, '\n')
print(table2, '\n')
print(table3, '\n')
