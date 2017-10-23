#!/usr/bin/env python

# import random
# import argparse
import os, sys
import json

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ConfigArgumentParser
# from bacpypes.consolelogging import ArgumentParser

from bacpypes.core import run
from bacpypes.comm import bind

from bacpypes.pdu import Address  # , GlobalBroadcast  # , LocalBroadcast
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.bvllservice import BIPForeign, AnnexJCodec, UDPMultiplexer  # , BIPBBMD

from bacpypes.app import Application
from bacpypes.appservice import StateMachineAccessPoint, ApplicationServiceAccessPoint
from bacpypes.service.device import WhoIsIAmServices  # LocalDeviceObject,
from bacpypes.service.object import ReadWritePropertyServices, ReadWritePropertyMultipleServices
from bacpypes.service.cov import ChangeOfValueServices

from bacpypes.constructeddata import ArrayOf
from bacpypes.primitivedata import Real  # , Integer, CharacterString
# from bacpypes.object import Property, register_object_type, AnalogInputObject, ReadableProperty  # , AnalogValueObject
# from bacpypes.basetypes import StatusFlags

from bacpypes.vlan import Network, Node
# from bacpypes.errors import ExecutionError

import modbusregisters
import modbusbacnetclasses
import queue


# from bacpypes.basetypes import PropertyIdentifier


# some debugging
_debug = 0
_log = ModuleLogger(globals())


def ip_to_bcnt_address(ipstr, mb_id):
    iparr = [int(ipbyte) for ipbyte in ipstr.split('.')]
    iparr.append(0)
    iparr.append(mb_id)
    return Address(bytearray(iparr))


#
#   VLANApplication
#

@bacpypes_debugging
# ADDED ReadWritePropertyMultipleServices
class ModbusVLANApplication(Application, WhoIsIAmServices, ReadWritePropertyServices,
                            ReadWritePropertyMultipleServices, ChangeOfValueServices):

    def __init__(self, vlan_device, vlan_address, ase_id=None):
        if _debug: ModbusVLANApplication._debug("__init__ %r %r aseID=%r", vlan_device, vlan_address, ase_id)
        Application.__init__(self, vlan_device, vlan_address, ase_id)

        # include a application decoder
        self.asap = ApplicationServiceAccessPoint()

        # pass the device object to the state machine access point so it
        # can know if it should support segmentation
        self.smap = StateMachineAccessPoint(vlan_device)

        # the segmentation state machines need access to the same device
        # information cache as the application
        self.smap.deviceInfoCache = self.deviceInfoCache

        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()

        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        bind(self.nse, self.nsap)

        # bind the top layers
        bind(self, self.asap, self.smap, self.nsap)

        # create a vlan node at the assigned address
        self.vlan_node = Node(vlan_address)

        # bind the stack to the node, no network number
        self.nsap.bind(self.vlan_node)

        # set register reader class that will look into block of registers for all associated slaves
        # self.register_reader = register_reader

    def request(self, apdu, forwarded=False):
        if _debug: ModbusVLANApplication._debug("[%s]request %r", self.vlan_node.address, apdu)
        Application.request(self, apdu, forwarded=forwarded)

    def indication(self, apdu, forwarded=False):
        if _debug: ModbusVLANApplication._debug("[%s]indication %r %r", self.vlan_node.address, apdu, forwarded)
        Application.indication(self, apdu, forwarded=forwarded)

    def response(self, apdu, forwarded=False):
        if _debug: ModbusVLANApplication._debug("[%s]response %r", self.vlan_node.address, apdu)
        Application.response(self, apdu, forwarded=forwarded)

    def confirmation(self, apdu, forwarded=False):
        if _debug: ModbusVLANApplication._debug("[%s]confirmation %r", self.vlan_node.address, apdu)
        Application.confirmation(self, apdu, forwarded=forwarded)

    # ADDED
    # def do_WhoIsRequest(self, apdu):
    #     print('whoisrequest from', apdu.pduSource)
    #     # if apdu.pduSource == Address('0:128.91.135.13'):
    #     #     apdu.pduSource = GlobalBroadcast()
    #
    #     # apdu.pduSource = GlobalBroadcast() # global or local broadcast?
    #     WhoIsIAmServices.do_WhoIsRequest(self, apdu)

    # def add_object(self, obj):
    #     Application.add_object(self, obj)
    #     if obj.__class__.__name__ == 'ModbusAnalogInputObject':
    #         obj.set_present_value_register_reader(self.register_reader)

    # ADDED


#
#   VLANRouter
#

@bacpypes_debugging
class VLANRouter:

    def __init__(self, local_address, local_network, foreign_address, bbmd_ttl=30):
        if _debug: VLANRouter._debug("__init__ %r %r", local_address, local_network)

        if isinstance(local_address, Address):
            self.local_address = local_address
        else:
            self.local_address = Address(local_address)

        if isinstance(foreign_address, Address):
            self.foreign_address = foreign_address
        else:
            self.foreign_address = Address(foreign_address)
        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()

        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        bind(self.nse, self.nsap)

        # create a BBMD, bound to the Annex J server
        # on the UDP multiplexer
        # self.bip = BIPBBMD(local_address)
        # self.annexj = AnnexJCodec()
        # self.mux = UDPMultiplexer(local_address)

        # ADDED
        # from WhoIsIAmForeign ForeignApplication
        # create a generic BIP stack, bound to the Annex J server
        # on the UDP multiplexer
        self.bip = BIPForeign(self.foreign_address, bbmd_ttl)
        # self.bip = BIPForeign(Address('10.166.1.72'), 30)
        # self.bip = BIPForeign(Address('192.168.1.10'), 30)
        # self.bip = BIPForeign(Address('130.91.139.99'), 30)
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(self.local_address, noBroadcast=True)
        # end
        # self.bip.add_peer(Address('10.166.1.72'))
        # ADDED

        # bind the bottom layers
        bind(self.bip, self.annexj, self.mux.annexJ)

        # bind the BIP stack to the local network
        self.nsap.bind(self.bip, local_network, self.local_address)


#
#   __main__
#

def main():
    # parse the command line arguments
    args = ConfigArgumentParser(description=__doc__).parse_args()

    # modbusregisters._debug_modbus_registers = (args.ini.debugprint == 'True')
    # modbusbacnetclasses._mb_bcnt_cls_debug = (args.ini.debugprint == 'True')

    # local_address = Address('130.91.139.93/22')
    # local_network = 0
    # vlan_network = 9997

    local_address = Address(args.ini.localip)
    local_network = int(args.ini.localnetwork)
    vlan_network = int(args.ini.vlannetwork)
    foreign_address = Address(args.ini.bbmdip)
    max_apdu_len = 1024
    segmentation_support = 'noSegmentation'
    vendor_id = 15

    # create the VLAN router, bind it to the local network
    router = VLANRouter(local_address, local_network, foreign_address)

    # create a VLAN
    vlan = Network()

    # create a node for the router, address 1 on the VLAN
    router_node = Node(Address(1))
    vlan.add_node(router_node)

    # bind the router stack to the vlan network through this node
    router.nsap.bind(router_node, vlan_network)

    mb_to_bank_queue = queue.Queue()
    bank_to_bcnt_queue = queue.Queue()

    object_val_dict = {}
    mb_req_dict = {}
    unq_ip_last_resp_dict = {}
    dev_dict = {}
    app_dict = {}

    # bank_to_out_queue = queue.Queue()
    # out_to_bank_queue = queue.PriorityQueue()

    # reg_reader = modbusregisters.RegisterReader(out_to_bank_queue)  # , bank_to_out_queue)
    # reg_bank = modbusregisters.RegisterBankThread(out_to_bank_queue)
    #
    # dev_list = []
    # app_list = []

    for fn in os.listdir(sys.path[0] + '/DeviceList'):
        if fn.endswith('.json'):  # and fn.startswith('DRL'):
            print(sys.path[0] + '/DeviceList/' + fn)
            json_raw_str = open(sys.path[0] + '/DeviceList/' + fn, 'r')
            map_dict = json.load(json_raw_str)
            # good_inst = reg_bank.add_instance(map_dict)
            good_inst = modbusregisters.add_meter_instance_to_dicts(map_dict, mb_to_bank_queue, object_val_dict,
                                                                    mb_req_dict, unq_ip_last_resp_dict)
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

                # dev_list.append(modbusbacnetclasses.ModbusLocalDevice(
                #     objectName=dev_name,
                #     objectIdentifier=('device', dev_inst),
                #     description=dev_desc,
                #     maxApduLengthAccepted=max_apdu_len,
                #     segmentationSupported=segmentation_support,
                #     vendorIdentifier=vendor_id,
                #     deviceIp=dev_ip,
                #     modbusId=dev_mb_id,
                #     modbusMapName=dev_map_name,
                #     modbusMapRev=dev_map_rev,
                #     deviceModelName=dev_meter_model,
                #     modbusPort=dev_mb_port,
                # ))
                dev_dict[dev_inst] = modbusbacnetclasses.ModbusLocalDevice(
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
                )

                # app_list.append(ModbusVLANApplication(dev_list[-1], ip_to_bcnt_address(dev_ip, dev_mb_id)))
                # vlan.add_node(app_list[-1].vlan_node)
                #
                # services_supported = app_list[-1].get_services_supported()
                # dev_list[-1].protocolServicesSupported = services_supported.value

                app_dict[dev_inst] = ModbusVLANApplication(dev_dict[dev_inst], ip_to_bcnt_address(dev_ip, dev_mb_id))
                vlan.add_node(app_dict[dev_inst].vlan_node)

                services_supported = app_dict[dev_inst].get_services_supported()
                dev_dict[dev_inst].protocolServicesSupported = services_supported.value

                val_types = {'holdingRegisters': 3, 'inputRegisters': 4, 'coilBits': 1, 'inputBits': 2}

                # create objects for device
                for val_type, mb_func in val_types.items():
                    if val_type not in map_dict or val_type not in ['holdingRegisters', 'inputRegisters']:
                        continue

                    mb_dev_wo = map_dict[val_type]['wordOrder']
                    mb_dev_poll_time = map_dict[val_type]['pollingTime']

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
                        obj_eq_m = (obj_pt_scale[3] - obj_pt_scale[2]) / (obj_pt_scale[1] - obj_pt_scale[0])
                        obj_eq_b = obj_pt_scale[2] - obj_eq_m * obj_pt_scale[0]
                        # print('m', obj_eq_m, 'b', obj_eq_b)

                        maio = modbusbacnetclasses.ModbusAnalogInputObject(
                            # parent_device_inst=dev_inst,
                            # register_reader=reg_reader,
                            # rx_queue=queue.Queue(),
                            # objectIdentifier=('analogInput', obj_inst),
                            # objectName=obj_name,
                            # description=obj_description,
                            # modbusFunction=mb_func,
                            # registerStart=obj_reg_start,
                            # numberOfRegisters=obj_num_regs,
                            # registerFormat=obj_reg_format,
                            # wordOrder=mb_dev_wo,
                            # modbusScaling=modbusbacnetclasses.ModbusScaling([obj_eq_m, obj_eq_b]),
                            # units=obj_units_id,
                            # statusFlags=StatusFlags([0, 1, 0, 0]),
                            objectIdentifier=('analogInput', obj_inst),
                            objectName=obj_name,
                            description=obj_description,
                            modbusFunction=mb_func,
                            registerStart=obj_reg_start,
                            numberOfRegisters=obj_num_regs,
                            registerFormat=obj_reg_format,
                            wordOrder=mb_dev_wo,
                            # modbusScaling=[obj_eq_m, obj_eq_b],
                            modbusScaling=ArrayOf(Real)([obj_eq_m, obj_eq_b]),
                            units=obj_units_id,
                            covIncrement=0.0,
                            updateInterval=int(mb_dev_poll_time / 10.0),
                            resolution=0.0,
                            reliability='communicationFailure',
                            statusFlags=[0, 1, 0, 0],
                            modbusCommErr='noTcpConnection',
                            eventState='normal',
                            outOfService=False,
                        )
                        # _log.debug("    - maio: %r", maio)
                        # app_list[-1].add_object(maio)
                        app_dict[dev_inst].add_object(maio)

    # # device identifier is assigned from the address
    # # device_instance = vlan_network * 100 + int(args.addr2)
    # device_instance = vlan_network * 100 + 5  # vlan_address
    # device_instance2 = vlan_network * 100 + 6
    # _log.debug("    - device_instance: %r", device_instance)
    #
    # # make a vlan device object
    # # vlan_device = \
    # #     LocalDeviceObject(
    # #         objectName="VLAN Node %d" % (device_instance,),
    # #         objectIdentifier=('device', device_instance),
    # #         maxApduLengthAccepted=1024,
    # #         segmentationSupported='noSegmentation',
    # #         vendorIdentifier=15,
    # #         )
    # # ADDED
    # vlan_device = \
    #     LocalDeviceObject(
    #         objectName='laptopBehindNetwork',
    #         objectIdentifier=device_instance,
    #         maxApduLengthAccepted=1024,
    #         segmentationSupported='noSegmentation',
    #         vendorIdentifier=15,
    #         )
    # vlan_device2 = \
    #     LocalDeviceObject(
    #         objectName='laptopBehindNetwork2',
    #         objectIdentifier=device_instance2,
    #         maxApduLengthAccepted=1024,
    #         segmentationSupported='noSegmentation',
    #         vendorIdentifier=15,
    #     )
    # # ADDED
    # _log.debug("    - vlan_device: %r", vlan_device)
    #
    # # make the application, add it to the network
    # vlan_app = ModbusVLANApplication(vlan_device, vlan_address)
    # vlan.add_node(vlan_app.vlan_node)
    #
    # vlan_app2 = ModbusVLANApplication(vlan_device2, Address(6))
    # vlan.add_node(vlan_app2.vlan_node)
    # _log.debug("    - vlan_app: %r", vlan_app)
    #
    # # ADDED
    # services_supported = vlan_app.get_services_supported()
    #
    # # let the device object know
    # vlan_device.protocolServicesSupported = services_supported.value
    #
    # services_supported = vlan_app2.get_services_supported()
    #
    # # let the device object know
    # vlan_device2.protocolServicesSupported = services_supported.value
    # # ADDED
    #
    # # make a random value object
    # # maio = RandomAnalogValueObject(
    # #     objectIdentifier=('analogValue', 1),
    # #     objectName='Device%d/Random1' % (device_instance,),
    # #     )
    # maio = modbusbacnetclasses.ModbusAnalogInputObject(device_instance, reg_reader,
    #     objectIdentifier=('analogInput', 1),
    #     objectName='Device%d/Modbus1' % (device_instance,),
    # )
    # _log.debug("    - ravo1: %r", maio)
    #
    # # add it to the device
    # vlan_app.add_object(maio)
    #
    # # make a random value object
    # maio = modbusbacnetclasses.ModbusAnalogInputObject(device_instance2, reg_reader,
    #     objectIdentifier=('analogInput', 1),
    #     objectName='Device%d/Modbus1' % (device_instance2,),
    # )
    #
    # # add it to the device
    # vlan_app2.add_object(maio)

    print('init modbus bank')
    obj_val_bank = modbusregisters.ModbusFormatAndStorage(mb_to_bank_queue, bank_to_bcnt_queue, object_val_dict)

    print('init modbus req launcher')
    mb_req_launcher = modbusregisters.ModbusRequestLauncher(mb_req_dict, unq_ip_last_resp_dict)

    print('init update objects task')
    update_objects = modbusbacnetclasses.UpdateObjectsFromModbus(bank_to_bcnt_queue, app_dict, 1000)

    print('start bank and launcher')
    obj_val_bank.start()
    mb_req_launcher.start()

    _log.debug("running")
    print('bacnet start')
    run()

    _log.debug("fini")


if __name__ == "__main__":
    main()
