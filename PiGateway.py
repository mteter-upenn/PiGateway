#!/usr/bin/env python

# import random
# import argparse

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
# from bacpypes.consolelogging import ArgumentParser

from bacpypes.core import run
from bacpypes.comm import bind

from bacpypes.pdu import Address, GlobalBroadcast  # , LocalBroadcast
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.bvllservice import BIPForeign, AnnexJCodec, UDPMultiplexer  # , BIPBBMD

from bacpypes.app import Application
from bacpypes.appservice import StateMachineAccessPoint, ApplicationServiceAccessPoint
from bacpypes.service.device import LocalDeviceObject, WhoIsIAmServices
from bacpypes.service.object import ReadWritePropertyServices, ReadWritePropertyMultipleServices

# from bacpypes.constructeddata import ArrayOf
# from bacpypes.primitivedata import Real, Integer, CharacterString
# from bacpypes.object import Property, register_object_type, AnalogInputObject, ReadableProperty  # , AnalogValueObject

from bacpypes.vlan import Network, Node
# from bacpypes.errors import ExecutionError

from modbusregisters import RegisterBankThread, RegisterReader
import modbusbacnetclasses
import queue


# from bacpypes.basetypes import PropertyIdentifier


# some debugging
_debug = 0
_log = ModuleLogger(globals())

# PropertyIdentifier.enumerations['modbusFunction'] = 3000000
# PropertyIdentifier.enumerations['registerStart'] = 3000001
# PropertyIdentifier.enumerations['numberOfRegisters'] = 3000002
# PropertyIdentifier.enumerations['registerFormat'] = 3000003
# PropertyIdentifier.enumerations['wordOrder'] = 3000004
# PropertyIdentifier.enumerations['registerScaling'] = 3000005
# PropertyIdentifier.enumerations['deviceIp'] = 3000006
# PropertyIdentifier.enumerations['modbusId'] = 3000007
# PropertyIdentifier.enumerations['modbusMapName'] = 3000008
# PropertyIdentifier.enumerations['modbusMapRev'] = 3000009
# PropertyIdentifier.enumerations['deviceModelName'] = 3000010
# PropertyIdentifier.enumerations['modbusPort'] = 3000011
#
#
# # @bacpypes_debugging
# # class RegisterScalingProperty(Property):
# #     def __init__(self, identifier):
# #         if _debug: RegisterScalingProperty._debug("__init__ %r", identifier)
# #         Property.__init__(self, identifier, Real, default=None, optional=False, mutable=False)
# #         self._is_scaled()
#
# @bacpypes_debugging
# class ModbusValueProperty(Property):
#
#     def __init__(self, identifier):
#         if _debug: ModbusValueProperty._debug("__init__ %r", identifier)
#         Property.__init__(self, identifier, Real, default=None, optional=True, mutable=False)
#
#     def ReadProperty(self, obj, array_index=None):
#         if _debug: ModbusValueProperty._debug("ReadProperty %r arrayIndex=%r", obj, array_index)
#
#         # access an array
#         if array_index is not None:
#             raise ExecutionError(errorClass='property', errorCode='propertyIsNotAnArray')
#
#         dev_inst = obj._parent_device_inst
#         # mb_func = obj.ReadProperty('modbusFunction')
#         # register_start = obj.ReadProperty('registerStart')
#         # num_regs = obj.ReadProperty('numberOfRegisters')
#         # reg_frmt = obj.ReadProperty('registerFormat')
#         # word_order = obj.ReadProperty('wordOrder')
#         # register_reader = obj._register_reader
#         try:
#             mb_func = obj._values['modbusFunction']
#             register_start = obj._values['registerStart']
#             num_regs = obj._values['numberOfRegisters']
#             reg_frmt = obj._values['registerFormat']
#             word_order = obj._values['wordOrder']
#             register_reader = obj._register_reader
#             is_scaled = obj._is_scaled
#             reg_scaling = obj._values['registerScaling']
#         except KeyError:
#             return 0.0
#
#         # get_register_format(self, dev_instance, mb_func, register, num_regs, reg_format, word_order,
#                             # queue_timeout=100.0)
#
#         value, reliability = register_reader.get_register_format(dev_inst, mb_func, register_start, num_regs, reg_frmt,
#                                                                  word_order)
#         # return a random value
#         # value = random.random() * 100.0
#         if _debug: ModbusValueProperty._debug("    - value: %r", value)
#
#         # print('ReadProperty from property', obj.ReadProperty('objectIdentifier'), dev_inst)
#         # print('obj parent is', self.object_parent)
#         if not reliability:
#             # need to throw flag in reliabilty and statusFlags
#             pass
#         return value
#
#     def WriteProperty(self, obj, value, array_index=None, priority=None, direct=False):
#         if _debug: ModbusValueProperty._debug("WriteProperty %r %r arrayIndex=%r priority=%r direct=%r", obj, value,
#                                               array_index, priority, direct)
#         raise ExecutionError(errorClass='property', errorCode='writeAccessDenied')
#
#     # def set_obj_parent(self, obj_id):
#     #     self.object_parent = obj_id
#     #     print('parent set:', obj_id)
#
# # PropertyIdentifier.enumerations['modbusFunction'] = 3000000
# # PropertyIdentifier.enumerations['registerStart'] = 3000001
# # PropertyIdentifier.enumerations['numberOfRegisters'] = 3000002
# # PropertyIdentifier.enumerations['registerFormat'] = 3000003
# # PropertyIdentifier.enumerations['wordOrder'] = 3000004
# # PropertyIdentifier.enumerations['registerScaling'] = 3000005
# # PropertyIdentifier.enumerations['deviceIp'] = 3000006
# # PropertyIdentifier.enumerations['modbusId'] = 3000007
# # PropertyIdentifier.enumerations['modbusMapName'] = 3000008
# # PropertyIdentifier.enumerations['modbusMapRev'] = 3000009
# # PropertyIdentifier.enumerations['deviceModelName'] = 3000010
# # PropertyIdentifier.enumerations['modbusPort'] = 3000011
# @bacpypes_debugging
# class ModbusAnalogInputObject(AnalogInputObject):
#     properties = [
#         ModbusValueProperty('presentValue'),
#         ReadableProperty('modbusFunction', Integer),
#         ReadableProperty('registerStart', Integer),
#         ReadableProperty('numberOfRegisters', Integer),
#         ReadableProperty('registerFormat', CharacterString),
#         ReadableProperty('wordOrder', CharacterString),
#         ReadableProperty('registerScaling', ArrayOf(Real))
#     ]
#
#     def __init__(self, parent_device_inst, register_reader, **kwargs):
#         if _debug: ModbusAnalogInputObject._debug("__init__ %r", kwargs)
#         AnalogInputObject.__init__(self, **kwargs)
#         self._register_reader = register_reader
#         self._parent_device_inst = parent_device_inst
#         reg_scaling = self.ReadProperty('registerScaling')
#         if reg_scaling == [0, 1, 0, 1]:
#             self._is_scaled = True
#         else:
#             self._is_scaled = False
#
#     # def ReadProperty(self, propid, arrayIndex=None):
#     #     print('object overwrite ReadProperty')
#     #     if propid=='presentValue':
#     #         prop = self._properties.get(propid)
#     #         if not prop:
#     #             raise PropertyError(propid)
#     #
#     #         # defer to the property to get the value
#     #         return prop.ReadProperty(self, arrayIndex)
#     #     else:
#     #         return AnalogInputObject.ReadProperty(self, propid, arrayIndex=arrayIndex)
#
# register_object_type(ModbusAnalogInputObject)


#
#   VLANApplication
#

@bacpypes_debugging
# ADDED ReadWritePropertyMultipleServices
class ModbusVLANApplication(Application, WhoIsIAmServices, ReadWritePropertyServices,
                            ReadWritePropertyMultipleServices):

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

    def request(self, apdu):
        if _debug: ModbusVLANApplication._debug("[%s]request %r", self.vlan_node.address, apdu)
        Application.request(self, apdu)

    def indication(self, apdu):
        if _debug: ModbusVLANApplication._debug("[%s]indication %r", self.vlan_node.address, apdu)
        Application.indication(self, apdu)

    def response(self, apdu):
        if _debug: ModbusVLANApplication._debug("[%s]response %r", self.vlan_node.address, apdu)
        Application.response(self, apdu)

    def confirmation(self, apdu):
        if _debug: ModbusVLANApplication._debug("[%s]confirmation %r", self.vlan_node.address, apdu)
        Application.confirmation(self, apdu)

    # ADDED
    def do_WhoIsRequest(self, apdu):
        print('whoisrequest from', apdu.pduSource)
        if apdu.pduSource == Address('0:130.91.137.90'):
            apdu.pduSource = GlobalBroadcast()

        # apdu.pduSource = GlobalBroadcast() # global or local broadcast?
        WhoIsIAmServices.do_WhoIsRequest(self, apdu)

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

    def __init__(self, local_address, local_network):
        if _debug: VLANRouter._debug("__init__ %r %r", local_address, local_network)

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
        self.bip = BIPForeign(Address('10.166.1.72'), 30)
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(local_address, noBroadcast=True)
        # end
        # self.bip.add_peer(Address('10.166.1.72'))
        # ADDED

        # bind the bottom layers
        bind(self.bip, self.annexj, self.mux.annexJ)

        # bind the BIP stack to the local network
        self.nsap.bind(self.bip, local_network, local_address)


#
#   __main__
#

def main():
    # parse the command line arguments
    # parser = ArgumentParser(
    #     description=__doc__,
    #     formatter_class=argparse.RawDescriptionHelpFormatter,
    #     )
    #
    # # add an argument for interval
    # parser.add_argument('addr1', type=str,
    #       help='address of first network',
    #       )
    #
    # # add an argument for interval
    # parser.add_argument('net1', type=int,
    #       help='network number of first network',
    #       )
    #
    # # add an argument for interval
    # parser.add_argument('addr2', type=str,
    #       help='address of second network',
    #       )
    #
    # # add an argument for interval
    # parser.add_argument('net2', type=int,
    #       help='network number of second network',
    #       )
    #
    # # now parse the arguments
    # args = parser.parse_args()
    #
    # if _debug: _log.debug("initialization")
    # if _debug: _log.debug("    - args: %r", args)

    # local_address = Address(args.addr1)
    # local_network = args.net1
    # vlan_address = Address(args.addr2)
    # vlan_network = args.net2

    bank_to_out_queue = queue.Queue()
    out_to_bank_queue = queue.PriorityQueue()

    reg_reader = RegisterReader(out_to_bank_queue, bank_to_out_queue)

    local_address = Address('130.91.139.93')
    local_network = 0
    vlan_address = Address(5)
    vlan_network = 9997

    # create the VLAN router, bind it to the local network
    router = VLANRouter(local_address, local_network)

    # create a VLAN
    vlan = Network()

    # create a node for the router, address 1 on the VLAN
    router_node = Node(Address(1))
    vlan.add_node(router_node)

    # bind the router stack to the vlan network through this node
    router.nsap.bind(router_node, vlan_network)

    # device identifier is assigned from the address
    # device_instance = vlan_network * 100 + int(args.addr2)
    device_instance = vlan_network * 100 + 5  # vlan_address
    device_instance2 = vlan_network * 100 + 6
    _log.debug("    - device_instance: %r", device_instance)

    # make a vlan device object
    # vlan_device = \
    #     LocalDeviceObject(
    #         objectName="VLAN Node %d" % (device_instance,),
    #         objectIdentifier=('device', device_instance),
    #         maxApduLengthAccepted=1024,
    #         segmentationSupported='noSegmentation',
    #         vendorIdentifier=15,
    #         )
    # ADDED
    vlan_device = \
        LocalDeviceObject(
            objectName='laptopBehindNetwork',
            objectIdentifier=device_instance,
            maxApduLengthAccepted=1024,
            segmentationSupported='noSegmentation',
            vendorIdentifier=15,
            )
    vlan_device2 = \
        LocalDeviceObject(
            objectName='laptopBehindNetwork2',
            objectIdentifier=device_instance2,
            maxApduLengthAccepted=1024,
            segmentationSupported='noSegmentation',
            vendorIdentifier=15,
        )
    # ADDED
    _log.debug("    - vlan_device: %r", vlan_device)

    # make the application, add it to the network
    vlan_app = ModbusVLANApplication(vlan_device, vlan_address)
    vlan.add_node(vlan_app.vlan_node)

    vlan_app2 = ModbusVLANApplication(vlan_device2, Address(6))
    vlan.add_node(vlan_app2.vlan_node)
    _log.debug("    - vlan_app: %r", vlan_app)

    # ADDED
    services_supported = vlan_app.get_services_supported()

    # let the device object know
    vlan_device.protocolServicesSupported = services_supported.value

    services_supported = vlan_app2.get_services_supported()

    # let the device object know
    vlan_device2.protocolServicesSupported = services_supported.value
    # ADDED

    # make a random value object
    # ravo = RandomAnalogValueObject(
    #     objectIdentifier=('analogValue', 1),
    #     objectName='Device%d/Random1' % (device_instance,),
    #     )
    ravo = modbusbacnetclasses.ModbusAnalogInputObject(device_instance, reg_reader,
        objectIdentifier=('analogInput', 1),
        objectName='Device%d/Modbus1' % (device_instance,),
    )
    _log.debug("    - ravo1: %r", ravo)

    # add it to the device
    vlan_app.add_object(ravo)

    # make a random value object
    ravo = modbusbacnetclasses.ModbusAnalogInputObject(device_instance2, reg_reader,
        objectIdentifier=('analogInput', 1),
        objectName='Device%d/Modbus1' % (device_instance2,),
    )

    # add it to the device
    vlan_app2.add_object(ravo)

    _log.debug("running")

    print('run')
    run()

    _log.debug("fini")


if __name__ == "__main__":
    main()
