import json
import os
from pprint import pprint
from modbusregisters import RegisterBankThread
import queue


bank_to_out_queue = queue.Queue()
out_to_bank_queue = queue.PriorityQueue()

reg_bank = RegisterBankThread(bank_to_out_queue, out_to_bank_queue)

for fn in os.listdir(os.getcwd() + '/DeviceList'):
    print(os.getcwd() + '/DeviceList/' + fn)

    json_raw_str = open(os.getcwd() + '/DeviceList/' + fn, 'r')

    if fn.endswith('.json') and fn.startswith('DGL'):
        json_dict = json.load(json_raw_str)
        reg_bank.add_instance(json_dict)

    json_raw_str.close()

reg_bank.run()

while True:
    pass

# pprint(reg_bank.register_bank)
# pprint(reg_bank.register_clusters)