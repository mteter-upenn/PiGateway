#!/usr/bin/env python

"""
Based on BBMD2VLANRouter.py from bacpypes library.  Works reasonably well, though there
seems to be a problem when messages are routed through the BBMD- some devices like to 
have the responses directly back (LGRs), others prefer if the response is rebroadcast
throught the BBMD (server).  No idea why, though likely a problem with WebCtrl more
than the library.

This sample application presents itself as a BBMD sitting on an IP network
that is also a router to a VLAN.  The VLAN has a device on it with an analog
value object that returns a random value for the present value.

Note that the device instance number of the virtual device will be 100 times
the network number plus the address (net2 * 100 + addr2).
"""

import random
import argparse

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ArgumentParser

from bacpypes.core import run
from bacpypes.comm import bind

from bacpypes.pdu import Address, GlobalBroadcast, LocalBroadcast
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.bvllservice import BIPForeign, BIPBBMD, AnnexJCodec, UDPMultiplexer

from bacpypes.app import Application
from bacpypes.appservice import StateMachineAccessPoint, ApplicationServiceAccessPoint
from bacpypes.service.device import LocalDeviceObject, WhoIsIAmServices
from bacpypes.service.object import ReadWritePropertyServices, ReadWritePropertyMultipleServices

from bacpypes.primitivedata import Real
from bacpypes.object import AnalogValueObject, Property, register_object_type, AnalogInputObject

from bacpypes.vlan import Network, Node
from bacpypes.errors import ExecutionError

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   RandomValueProperty
#

@bacpypes_debugging
class RandomValueProperty(Property):

    def __init__(self, identifier):
        if _debug: RandomValueProperty._debug("__init__ %r", identifier)
        Property.__init__(self, identifier, Real, default=None, optional=True, mutable=False)

    def ReadProperty(self, obj, arrayIndex=None):
        if _debug: RandomValueProperty._debug("ReadProperty %r arrayIndex=%r", obj, arrayIndex)

        # access an array
        if arrayIndex is not None:
            raise ExecutionError(errorClass='property', errorCode='propertyIsNotAnArray')

        # return a random value
        value = random.random() * 100.0
        if _debug: RandomValueProperty._debug("    - value: %r", value)

        return value

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None, direct=False):
        if _debug: RandomValueProperty._debug("WriteProperty %r %r arrayIndex=%r priority=%r direct=%r", obj, value,
                                              arrayIndex, priority, direct)
        raise ExecutionError(errorClass='property', errorCode='writeAccessDenied')

#
#   Random Value Object Type
#

@bacpypes_debugging
class RandomAnalogValueObject(AnalogValueObject):

    properties = [
        RandomValueProperty('presentValue'),
        ]

    def __init__(self, **kwargs):
        if _debug: RandomAnalogValueObject._debug("__init__ %r", kwargs)
        AnalogValueObject.__init__(self, **kwargs)


register_object_type(RandomAnalogValueObject)


@bacpypes_debugging
class ModbusValueProperty(Property):

    def __init__(self, identifier):
        if _debug: ModbusValueProperty._debug("__init__ %r", identifier)
        self.register_reader = None
        Property.__init__(self, identifier, Real, default=None, optional=True, mutable=False)

    def ReadProperty(self, obj, arrayIndex=None):
        if _debug: ModbusValueProperty._debug("ReadProperty %r arrayIndex=%r", obj, arrayIndex)

        # access an array
        if arrayIndex is not None:
            raise ExecutionError(errorClass='property', errorCode='propertyIsNotAnArray')

        # check if register_reader was set, if not there will be no way to read the stored register values
        if self.register_reader is None:
            return float('NaN')

        # return a random value
        value = random.random() * 100.0
        if _debug: ModbusValueProperty._debug("    - value: %r", value)

        return value

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None, direct=False):
        if _debug: ModbusValueProperty._debug("WriteProperty %r %r arrayIndex=%r priority=%r direct=%r", obj, value,
                                              arrayIndex, priority, direct)
        raise ExecutionError(errorClass='property', errorCode='writeAccessDenied')

    def set_RegisterReader(self, register_reader):
        self.register_reader = register_reader
        print('set_RegisterReader')


@bacpypes_debugging
class ModbusAnalogInputObject(AnalogInputObject):
    properties = [
        ModbusValueProperty('presentValue'),
    ]

    def __init__(self, **kwargs):
        if _debug: ModbusAnalogInputObject._debug("__init__ %r", kwargs)
        AnalogInputObject.__init__(self, **kwargs)

    def set_present_value_RegisterReader(self, register_reader):
        self._properties.get('presentValue').set_register_reader(register_reader)


register_object_type(ModbusAnalogInputObject)


class RegisterReader:
    def __init__(self, tx_queue, rx_queue):
        self.tx_queue = tx_queue
        self.rx_queue = rx_queue

    def get_register_raw(self, dev_instance, mb_function, register):
        self.tx_queue.put(('bacnet', dev_instance, mb_function, register, 1, 'uint16'))

    def get_register_format(self, dev_instance, mb_function, register, num_regs, reg_format):
        self.tx_queue.put(('bacnet', dev_instance, mb_function, register, num_regs, reg_format))






#
#   VLANApplication
#

@bacpypes_debugging
#ADDED ReadWritePropertyMultipleServices
class VLANApplication(Application, WhoIsIAmServices, ReadWritePropertyServices, ReadWritePropertyMultipleServices):

    def __init__(self, vlan_device, vlan_address, aseID=None, register_reader=None):
        if _debug: VLANApplication._debug("__init__ %r %r aseID=%r", vlan_device, vlan_address, aseID)
        Application.__init__(self, vlan_device, vlan_address, aseID)

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
        self.register_reader = register_reader

    def request(self, apdu):
        if _debug: VLANApplication._debug("[%s]request %r", self.vlan_node.address, apdu)
        Application.request(self, apdu)

    def indication(self, apdu):
        if _debug: VLANApplication._debug("[%s]indication %r", self.vlan_node.address, apdu)
        Application.indication(self, apdu)

    def response(self, apdu):
        if _debug: VLANApplication._debug("[%s]response %r", self.vlan_node.address, apdu)
        Application.response(self, apdu)

    def confirmation(self, apdu):
        if _debug: VLANApplication._debug("[%s]confirmation %r", self.vlan_node.address, apdu)
        Application.confirmation(self, apdu)

    #ADDED
    def do_WhoIsRequest(self, apdu):
        print('whoisrequest from', apdu.pduSource)
        if apdu.pduSource == Address('0:130.91.137.90'):
            apdu.pduSource = GlobalBroadcast()

        # apdu.pduSource = GlobalBroadcast() # global or local broadcast?
        WhoIsIAmServices.do_WhoIsRequest(self, apdu)

    def add_object(self, obj):
        Application.add_object(self, obj)
        if obj.__class__.__name__ == 'ModbusAnalogInputObject':
            obj.set_present_value_register_reader(self.register_reader)

    #ADDED



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

        #ADDED
        #from WhoIsIAmForeign ForeignApplication
        # create a generic BIP stack, bound to the Annex J server
        # on the UDP multiplexer
        self.bip = BIPForeign(Address('10.166.1.72'), 30)
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(local_address, noBroadcast=True)
        #end
        # self.bip.add_peer(Address('10.166.1.72'))
        #ADDED

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
    #ADDED
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
    #ADDED
    _log.debug("    - vlan_device: %r", vlan_device)

    # make the application, add it to the network
    vlan_app = VLANApplication(vlan_device, vlan_address)
    vlan.add_node(vlan_app.vlan_node)

    vlan_app2 = VLANApplication(vlan_device2, Address(6))
    vlan.add_node(vlan_app2.vlan_node)
    _log.debug("    - vlan_app: %r", vlan_app)

    #ADDED
    services_supported = vlan_app.get_services_supported()

    # let the device object know
    vlan_device.protocolServicesSupported = services_supported.value

    services_supported = vlan_app2.get_services_supported()

    # let the device object know
    vlan_device2.protocolServicesSupported = services_supported.value
    #ADDED

    # make a random value object
    # ravo = RandomAnalogValueObject(
    #     objectIdentifier=('analogValue', 1),
    #     objectName='Device%d/Random1' % (device_instance,),
    #     )
    ravo = ModbusAnalogInputObject(
        objectIdentifier=('analogInput', 1),
        objectName='Device%d/Modbus1' % (device_instance,),
    )
    _log.debug("    - ravo1: %r", ravo)

    # add it to the device
    vlan_app.add_object(ravo)

    # make a random value object
    ravo = RandomAnalogValueObject(
        objectIdentifier=('analogValue', 1),
        objectName='Device%d/Random1' % (device_instance2,),
    )

    # add it to the device
    vlan_app2.add_object(ravo)


    _log.debug("running")

    print('run')
    run()

    _log.debug("fini")


if __name__ == "__main__":
    main()
