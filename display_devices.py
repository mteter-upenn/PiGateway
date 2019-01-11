import os
import json
from beautifultable import BeautifulTable


table1 = BeautifulTable()
table2 = BeautifulTable()
table3 = BeautifulTable()
table4 = BeautifulTable()
hold_table1 = BeautifulTable()
inpt_table1 = BeautifulTable()

table1.column_headers = ['BACnet Id', 'Name', 'IP', 'Modbus Id']
table2.column_headers = ['BACnet Id', 'Description']
table3.column_headers = ['BACnet Id', 'Map Name', 'Map Rev', 'Meter Name']
table4.column_headers = ['BACnet Id', 'Modbus TO', 'COV Subscribe']
hold_table1.column_headers = ['BACnet Id', 'Num Regs', 'WO', 'Polling', 'MB TO', 'Group Cons','Group gap']
inpt_table1.column_headers = ['BACnet Id', 'Num Regs', 'WO', 'Polling', 'MB TO', 'Group Cons','Group gap']

dev_list = []
hold_reg_list = []
inpt_reg_list = []

for dev_filename in os.listdir(os.getcwd() + '/DeviceList'):
    if dev_filename.endswith('.json'):  # and fn.startswith('DRL'):
        json_raw_str = open(os.getcwd() + '/DeviceList/' + dev_filename, 'r')
        map_dict = json.load(json_raw_str)

        dev_list.append([map_dict['deviceInstance'], map_dict['deviceName'], map_dict['deviceIP'], map_dict['modbusId'],
                         map_dict['deviceDescription'], map_dict['mapName'], map_dict['mapRev'],
                         map_dict['meterModelName'], map_dict['modbusPort'], map_dict['covSubscribe']])

        if 'holdingRegisters' in map_dict:
            hold_map_dict = map_dict['holdingRegisters']
            hold_reg_list.append([map_dict['deviceInstance'], len(hold_map_dict['registers']),
                                  hold_map_dict['wordOrder'], hold_map_dict['pollingTime'],
                                  hold_map_dict['requestTimeout'], hold_map_dict['groupConsecutive'],
                                  hold_map_dict['groupGaps']])
        else:
            hold_reg_list.append([map_dict['deviceInstance'], 0, '', '', '', '', ''])

        if 'inputRegisters' in map_dict:
            inpt_map_dict = map_dict['holdingRegisters']
            inpt_reg_list.append([map_dict['deviceInstance'], len(inpt_map_dict['registers']),
                                  inpt_map_dict['wordOrder'], inpt_map_dict['pollingTime'],
                                  inpt_map_dict['requestTimeout'], inpt_map_dict['groupConsecutive'],
                                  inpt_map_dict['groupGaps']])
        else:
            inpt_reg_list.append([map_dict['deviceInstance'], 0, '', '', '', '', ''])

        json_raw_str.close()

dev_list.sort()
hold_reg_list.sort()
inpt_reg_list.sort()

for ii in range(len(dev_list)):
    table1.append_row([dev_list[ii][0], dev_list[ii][1], dev_list[ii][2], dev_list[ii][3]])
    table2.append_row([dev_list[ii][0], dev_list[ii][4]])
    table3.append_row([dev_list[ii][0], dev_list[ii][5], dev_list[ii][6], dev_list[ii][7]])
    table4.append_row([dev_list[ii][0], dev_list[ii][8], dev_list[ii][9]])
    # hold_table1.append_row([hold_reg_list[ii][0], hold_reg_list[ii][0], hold_reg_list[ii][0], hold_reg_list[ii][0], hold_reg_list[ii][0], hold_reg_list[ii][0], hold_reg_list[ii][0]])
    hold_table1.append_row(hold_reg_list[ii])
    inpt_table1.append_row(inpt_reg_list[ii])

print(table1, '\n')
print(table2, '\n')
print(table3, '\n')
print(table4, '\n')
print('HOLDING REGISTERS')
print(hold_table1, '\n')
print('INPUT REGISTERS')
print(inpt_table1, '\n')
