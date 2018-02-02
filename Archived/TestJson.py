
import os
import json
import modbusregisters
import queue
import pprint

mb_to_bank_queue = queue.Queue()
bank_to_bcnt_queue = queue.Queue()

object_val_dict = {}
mb_req_dict = {}
unq_ip_last_resp_dict = {}
dev_dict = {}
app_dict = {}

for fn in os.listdir(os.getcwd() + '/DeviceList'):
    if fn.endswith('.json'):  # and fn.startswith('DRL'):
        print(os.getcwd() + '/DeviceList/' + fn)
        json_raw_str = open(os.getcwd() + '/DeviceList/' + fn, 'r')
        map_dict = json.load(json_raw_str)
        # good_inst = reg_bank.add_instance(map_dict)
        good_inst = modbusregisters.add_meter_instance_to_dicts(map_dict, mb_to_bank_queue, object_val_dict,
                                                                mb_req_dict, unq_ip_last_resp_dict)
        # pprint.pprint(object_val_dict)
        json_raw_str.close()