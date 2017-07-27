#!/usr/bin/env python

"""
This sample application shows how to extend one of the basic objects, an Analog
Value Object in this case, to provide a present value. This type of code is used
when the application is providing a BACnet interface to a collection of data.
It assumes that almost all of the default behaviour of a BACpypes application is
sufficient.
"""

import os
import json
# import random

from bacpypes.debugging import ModuleLogger  # bacpypes_debugging,
# from bacpypes.consolelogging import ConfigArgumentParser

from bacpypes.core import run

# from bacpypes.primitivedata import Real
# from bacpypes.object import AnalogValueObject, Property, register_object_type
# from bacpypes.errors import ExecutionError

from bacpypes.app import BIPSimpleApplication
# from bacpypes.service.device import LocalDeviceObject

import modbusregisters
# from modbusregisters import RegisterBankThread, RegisterReader
import modbusbacnetclasses
# from modbusbacnetclasses import ModbusLocalDevice, ModbusAnalogInputObject
# from modbusbacnetclasses import *
import queue

# some debugging
_debug = 0
_log = ModuleLogger(globals())


#
#   __main__
#

def main():
    # parse the command line arguments
    # args = ConfigArgumentParser(description=__doc__).parse_args()
    #
    # if _debug: _log.debug("initialization")
    # if _debug: _log.debug("    - args: %r", args)

    # object_name = 'LinuxLaptop'
    # object_id = 2459990
    max_apdu_len = 1024
    segmentation_support = 'segmentedBoth'
    vendor_id = 15
    ip_address = '130.91.139.93/22'

    bank_to_out_queue = queue.Queue()
    out_to_bank_queue = queue.PriorityQueue()

    reg_reader = modbusregisters.RegisterReader(out_to_bank_queue, bank_to_out_queue)
    reg_bank = modbusregisters.RegisterBankThread(bank_to_out_queue, out_to_bank_queue)

    dev_list = []
    app_list = []

    for fn in os.listdir(os.getcwd() + '/DeviceList'):
        if fn.endswith('.json') and fn.startswith('DRL_lar'):
            print(os.getcwd() + '/DeviceList/' + fn)
            json_raw_str = open(os.getcwd() + '/DeviceList/' + fn, 'r')
            map_dict = json.load(json_raw_str)
            good_inst = reg_bank.add_instance(map_dict)
            json_raw_str.close()

            # "deviceName": "DRL small steam",
            # "deviceInstance": 4000001,
            # "deviceDescription": "DRL small steam meter- connected by NC valve to Towne through skirkanich",
            # "deviceIP": "10.166.2.132",
            # "modbusId": 10,
            # "mapName": "KEP Steam",
            # "mapRev": "a",
            # "meterModelName": "KEP Steam",
            # "modbusPort": 502,
            # "holdingRegisters": {
            if good_inst:
                dev_name = map_dict['deviceName']
                dev_inst = map_dict['deviceInstance']
                dev_desc = map_dict['deviceDescription']
                dev_ip = map_dict['deviceIP']
                dev_mb_id = map_dict['modbusId']
                dev_map_name = map_dict['mapName']
                dev_map_rev = map_dict['mapRev']
                dev_meter_model = map_dict['meterModelName']
                dev_mb_port = map_dict['modbusPort']

                dev_list.append(modbusbacnetclasses.ModbusLocalDevice(
                    objectName=dev_name,
                    objectIdentifier=('device', dev_inst),
                    description=dev_desc,
                    maxApduLengthAccepted=max_apdu_len,
                    segmentationSupported=segmentation_support,
                    vendorIdentifier=vendor_id,
                    deviceIp=dev_ip,
                    modbusId=dev_mb_id,
                    modbusMapName=dev_map_name,
                    modbusMapRev=dev_map_rev,
                    deviceModelName=dev_meter_model,
                    modbusPort=dev_mb_port,
                ))

                app_list.append(BIPSimpleApplication(dev_list[-1], ip_address))

                services_supported = app_list[-1].get_services_supported()
                dev_list[-1].protocolServicesSupported = services_supported.value

                val_types = {'holdingRegisters': 3, 'inputRegisters': 4, 'coilBits': 1, 'inputBits': 2}

                # create objects for device
                for val_type, mb_func in val_types.items():
                    if val_type not in map_dict or val_type not in ['holdingRegisters', 'inputRegisters']:
                        continue

                    mb_dev_wo = map_dict[val_type]['wordOrder']

                    for register in map_dict[val_type]['registers']:
                        # "objectName": "heat_flow_steam",
                        # "objectDescription": "Instantaneous heat flow of steam",
                        # "objectInstance": 1,
                        # "start": 1,
                        # "format": "float",
                        # "poll": "yes",
                        # "unitsId": 157,
                        # "pointScale": [0, 1, 0, 1]

                        if register['poll'] == 'no':
                            continue

                        obj_name = register['objectName']
                        obj_description = register['objectDescription']
                        obj_inst = register['objectInstance']
                        obj_reg_start = register['start']
                        obj_reg_format = register['format']
                        if obj_reg_format in modbusregisters.one_register_formats:
                            obj_num_regs = 1
                        elif obj_reg_format in modbusregisters.two_register_formats:
                            obj_num_regs = 2
                        elif obj_reg_format in modbusregisters.three_register_formats:
                            obj_num_regs = 3
                        elif obj_reg_format in modbusregisters.four_register_formats:
                            obj_num_regs = 4
                        else:
                            continue
                        obj_units_id = register['unitsId']
                        obj_pt_scale = register['pointScale']

                        ravo = modbusbacnetclasses.ModbusAnalogInputObject(
                            parent_device_inst=dev_inst,
                            register_reader=reg_reader,
                            objectIdentifier=('analogInput', obj_inst),
                            objectName=obj_name,
                            description=obj_description,
                            modbusFunction=mb_func,
                            registerStart=obj_reg_start,
                            numberOfRegisters=obj_num_regs,
                            registerFormat=obj_reg_format,
                            wordOrder=mb_dev_wo,
                            registerScaling=obj_pt_scale,
                            units=obj_units_id,
                        )
                        # _log.debug("    - ravo: %r", ravo)
                        app_list[-1].add_object(ravo)


    # # this_device = modbusbacnetclasses.ModbusLocalDevice(
    # this_device = modbusbacnetclasses.ModbusLocalDevice(
    #     objectName=object_name,
    #     objectIdentifier=('device', object_id),
    #     maxApduLengthAccepted=max_apdu_len,
    #     segmentationSupported=segmentation_support,
    #     vendorIdentifier=vendor_id,
    #     deviceIp='10.166.2.132',
    #     modbusId=10,
    #     modbusMapName='KEP Steam',
    #     modbusMapRev='a',
    #     deviceModelName='KEP Steam',
    #     modbusPort=502,
    #     # wordOrder='lsw',
    # )
    #
    # # make a sample application
    # this_application = BIPSimpleApplication(this_device, ip_address)
    #
    # # get the services supported
    # services_supported = this_application.get_services_supported()
    # if _debug: _log.debug("    - services_supported: %r", services_supported)
    #
    # # let the device object know
    # this_device.protocolServicesSupported = services_supported.value

    # # make some random input objects
    # for i in range(1, 10+1):
    #     # ravo = RandomAnalogValueObject(
    #     #     objectIdentifier=('analogValue', i),
    #     #     objectName='Random-%d' % (i,),
    #     #     )
    #
    #     # ravo = modbusbacnetclasses.ModbusAnalogInputObject(
    #     ravo = modbusbacnetclasses.ModbusAnalogInputObject(
    #         parent_device_inst=object_id,
    #         register_reader=None,
    #         objectIdentifier=('analogInput', i),
    #         objectName='ModbusRandom-%d' % (i,),
    #         modbusFunction=3,
    #         registerStart=i,
    #         numberOfRegisters=2,
    #         registerFormat='float',
    #         wordOrder='lsw',
    #         registerScaling=[0, 1, 0, 1],
    #     )
    #     _log.debug("    - ravo: %r", ravo)
    #     this_application.add_object(ravo)
    #
    # # make sure they are all there
    # _log.debug("    - object list: %r", this_device.objectList)

    reg_bank.start()

    _log.debug("running")

    run()

    _log.debug("fini")

if __name__ == "__main__":
    main()
