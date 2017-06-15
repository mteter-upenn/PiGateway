import json
import os
from pprint import pprint

json_raw_str = open(os.getcwd() + '/DeviceMappings/EmonDmon3400Json.json', 'r')

json_dict = json.load(json_raw_str)

json_raw_str.close()

json_dict['mapName'] = 'my choice here'
print(json_dict['mapName'])

# pprint(json_dict)