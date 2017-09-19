import time
from queue import Empty
from copy import copy as scopy

from bacpypes.debugging import bacpypes_debugging, ModuleLogger

from bacpypes.service.device import LocalDeviceObject
from bacpypes.constructeddata import ArrayOf
from bacpypes.primitivedata import Real, Integer, CharacterString, Enumerated, Unsigned, Boolean, BitString
from bacpypes.object import register_object_type, Object, ReadableProperty, OptionalProperty
from bacpypes.task import RecurringTask

# from bacpypes.errors import ExecutionError

from bacpypes.basetypes import PropertyIdentifier, Reliability, EngineeringUnits, StatusFlags, EventState
# LimitEnable, EventTransitionBits, NotifyType, TimeStamp, ObjectPropertyReference

_debug = 0
_log = ModuleLogger(globals())

# set module debugger flag
_mb_bcnt_cls_debug = False

PropertyIdentifier.enumerations['modbusFunction'] = 3000000
PropertyIdentifier.enumerations['registerStart'] = 3000001
PropertyIdentifier.enumerations['numberOfRegisters'] = 3000002
PropertyIdentifier.enumerations['registerFormat'] = 3000003
PropertyIdentifier.enumerations['wordOrder'] = 3000004
PropertyIdentifier.enumerations['modbusScaling'] = 3000005
PropertyIdentifier.enumerations['deviceIp'] = 3000006
PropertyIdentifier.enumerations['modbusId'] = 3000007
PropertyIdentifier.enumerations['modbusMapName'] = 3000008
PropertyIdentifier.enumerations['modbusMapRev'] = 3000009
PropertyIdentifier.enumerations['deviceModelName'] = 3000010
PropertyIdentifier.enumerations['modbusPort'] = 3000011
PropertyIdentifier.enumerations['modbusCommErr'] = 3000012
PropertyIdentifier.enumerations['profileLocation'] = 485

# this will be used to ensure all properties have been given values- THIS IS NOT AN EXCUSE TO NOT GIVE VALUES!
modbus_ai_obj_def_vals = \
    {'description': 'modbus register as bacnet point',
     'profileName': '',
     'profileLocation': '',
     'deviceType': 'not listed',
     'statusFlags': [0, 1, 0, 0],
     'eventState': 'normal',
     'reliability': 'communicationFailure',
     'outOfService': False,
     'updateInterval': 3000,
     'units': 'noUnits',
     'minPresValue': 0,  # not sure if this does anything internally
     'maxPresValue': 1,  # not sure if this has an effect, 1.7014118E38 might be better value
     'resolution': 0,
     'covIncrement': 0,
     'modbusFunction': 'readHoldingRegisters',
     'registerStart': 1,
     'numberOfRegisters': 1,
     'registerFormat': 'uint16',
     'wordOrder': 'lsw',
     'modbusScaling': [1, 0],
     'modbusCommErr': 'noTcpConnection'
     }


class ModbusErrors(Enumerated):
    enumerations = \
        {'noFaultDetected': 0,
         'illegalFunction': 1,
         'illegalDataAddress': 2,
         'illegalDataValue': 3,
         'slaveDeviceFailure': 4,
         'acknowledge': 5,
         'slaveDeviceBusy': 6,
         'negAcknowledge': 7,
         'memoryParityError': 8,
         'gatewayPathUnavailable': 10,
         'gatewayTargetFailedToRespond': 11,
         'noTcpConnection': 19,
         'generalError': 87,
         'invalidIpAddr': 101,
         'invalidDataType': 102,
         'invalidRegisterLookup': 103,
         'invalidFileName': 104,
         'unableToAccessFile': 105,
         'slaveClosedSocket': 106,
         'keyboardInterrupt': 107,
         'unexpectedTcpLength': 108,
         'unexpectedMbLength': 109,
         'unexpectedMbFuncRet': 110,
         'unexpectedMbSlvRet': 111
         }
    # should be a part of the Enumerated parent class
    # @classmethod
    # def is_valid(cls, arg):
    #     """Return True if arg is valid value for the class.  If the string
    #     value is wrong for the enumeration, the encoding will fail.
    #     """
    #     if isinstance(arg, int) and arg >= 0:
    #         return arg in cls.enumerations.values()
    #     elif isinstance(arg, str):
    #         return arg in cls.enumerations.keys()
    #     return False


class ModbusFunctions(Enumerated):
    enumerations = \
        {'readCoilBits': 1,
         'readInputBits': 2,
         'readHoldingRegisters': 3,
         'readInputRegisters': 4,
         'forceSingleBit': 5,
         'presetSingleRegister': 6,
         'readExceptionStatus': 7,
         'fetchCommEventCounter': 11,
         'fetchCommEventLog': 12,
         'forceMultipleCoils': 15,
         'presetMultipleRegisters': 16,
         'reportSlaveId': 17,
         'readGeneralReference': 20,
         'writeGenerealReference': 21,
         'maskWriteRegister': 22,
         'readWriteRegister': 23,
         'readFifoQueue': 24
         }


class ModbusRegisterFormat(Enumerated):
    enumerations = \
        {'uint16': 0,
         'sint16': 1,
         'sm1k16': 2,
         'sm10k16': 3,
         'bin': 4,
         'hex': 5,
         'ascii': 6,
         'uint32': 7,
         'sint32': 8,
         'um1k32': 9,
         'sm1k32': 10,
         'um10k32': 11,
         'sm10k32': 12,
         'float': 13,
         'uint48': 14,
         'um1k48': 15,
         'sm1k48': 16,
         'um10k48': 17,
         'sm10k48': 18,
         'uint64': 19,
         'sint64': 20,
         'um1k64': 21,
         'sm1k64': 22,
         'um10k64': 23,
         'sm10k64': 24,
         'double': 25,
         'energy': 26
         }


class ModbusRegisterWordOrder(Enumerated):
    enumerations = \
        {'lsw': 0,
         'msw': 1
         }


@bacpypes_debugging
class ModbusAnalogInputObject(Object):
    objectType = 'analogInput'
    properties = \
        [ReadableProperty('presentValue', Real),
         OptionalProperty('deviceType', CharacterString),
         OptionalProperty('profileLocation', CharacterString),
         ReadableProperty('statusFlags', StatusFlags),
         ReadableProperty('eventState', EventState),
         OptionalProperty('reliability', Reliability),
         ReadableProperty('outOfService', Boolean),
         OptionalProperty('updateInterval', Unsigned),
         ReadableProperty('units', EngineeringUnits),
         OptionalProperty('minPresValue', Real, mutable=True),
         OptionalProperty('maxPresValue', Real, mutable=True),
         OptionalProperty('resolution', Real),
         OptionalProperty('covIncrement', Real),
         # OptionalProperty('timeDelay', Unsigned),
         # OptionalProperty('notificationClass', Unsigned),
         # OptionalProperty('highLimit', Real),
         # OptionalProperty('lowLimit', Real),
         # OptionalProperty('deadband', Real),
         # OptionalProperty('limitEnable', LimitEnable),
         # OptionalProperty('eventEnable', EventTransitionBits),
         # OptionalProperty('ackedTransitions', EventTransitionBits),
         # OptionalProperty('notifyType', NotifyType),
         # OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp)),
         # OptionalProperty('eventMessageTexts', ArrayOf(CharacterString)),
         # OptionalProperty('eventMessageTextsConfig', ArrayOf(CharacterString)),
         # OptionalProperty('eventDetectionEnable', Boolean),
         # OptionalProperty('eventAlgorithmInhibitRef', ObjectPropertyReference),
         # OptionalProperty('eventAlgorithmInhibit', Boolean),
         # OptionalProperty('timeDelayNormal', Unsigned),
         # OptionalProperty('reliabilityEvaluationInhibit', Boolean)
         ReadableProperty('modbusFunction', ModbusFunctions),
         ReadableProperty('registerStart', Unsigned),
         ReadableProperty('numberOfRegisters', Unsigned),
         ReadableProperty('registerFormat', CharacterString),
         ReadableProperty('wordOrder', CharacterString),
         ReadableProperty('modbusScaling', ArrayOf(Real)),
         ReadableProperty('modbusCommErr', ModbusErrors)
         ]
# class ModbusAnalogInputObject(AnalogInputObject):
    # properties = [
    #     # ModbusValueProperty('presentValue'),
    #     ReadableProperty('modbusFunction', Integer),
    #     ReadableProperty('registerStart', Integer),
    #     ReadableProperty('numberOfRegisters', Integer),
    #     ReadableProperty('registerFormat', CharacterString),
    #     ReadableProperty('wordOrder', CharacterString),
    #     ReadableProperty('modbusScaling', ArrayOf(Real)),
    #     # ReadableProperty('modbusCommErr', Integer)
    #     ReadableProperty('modbusCommErr', ModbusErrors)
    # ]

    # def __init__(self, parent_device_inst, register_reader, rx_queue, **kwargs):
    def __init__(self, **kwargs):
        if _debug: ModbusAnalogInputObject._debug("__init__ %r", kwargs)
        Object.__init__(self, **kwargs)

        # self.reliability = 'communicationFailure'
        # # self.statusFlags['fault'] = 1
        # # self.modbusCommErr = 19
        # self.modbusCommErr = 'noTcpConnection'
        # self.outOfService = False
        # self.eventState = 'normal'

        # set unassigned properties to default values
        for propid, prop in self._properties.items():
            if prop.ReadProperty(self) is None and propid in modbus_ai_obj_def_vals:
                if _mb_bcnt_cls_debug: print(self.objectName, propid, 'was not set, default is',
                                             modbus_ai_obj_def_vals[propid])

                prop.WriteProperty(self, modbus_ai_obj_def_vals[propid], direct=True)

    def ReadProperty(self, propid, arrayIndex=None):
        if _mb_bcnt_cls_debug: print(propid, getattr(self, propid), end=', ')  # might need self._values[propid]
        value = Object.ReadProperty(self, propid, arrayIndex=arrayIndex)
        if _mb_bcnt_cls_debug: print('value:', value)
        return value


register_object_type(ModbusAnalogInputObject)


@bacpypes_debugging
class ModbusLocalDevice(LocalDeviceObject):
    properties = [
        ReadableProperty('deviceIp', CharacterString),
        ReadableProperty('modbusId', Integer),
        ReadableProperty('modbusMapName', CharacterString),
        ReadableProperty('modbusMapRev', CharacterString),
        ReadableProperty('deviceModelName', CharacterString),
        ReadableProperty('modbusPort', Integer),
        # ReadableProperty('wordOrder', CharacterString)
    ]


register_object_type(ModbusLocalDevice)


@bacpypes_debugging
class UpdateObjectsFromModbus(RecurringTask):
    def __init__(self, bank_to_bcnt_queue, app_dict, interval, max_run_time=1000):
        RecurringTask.__init__(self, interval)

        self.bank_to_bcnt_queue = bank_to_bcnt_queue
        self.app_dict = app_dict
        self.max_run_time = max_run_time / 1000  # set in ms to coincide with interval

        # install it
        self.install_task()

    def process_task(self):
        start_time = time.time()
        if _mb_bcnt_cls_debug: print('start recurring task')

        while (not self.bank_to_bcnt_queue.empty()) and (time.time() - start_time < self.max_run_time):
        # if not self.bank_to_bcnt_queue.empty():
            if _mb_bcnt_cls_debug: print('\tqueue not empty')

            try:
                val_dict = self.bank_to_bcnt_queue.get_nowait()
                if _mb_bcnt_cls_debug: print('\tgot bacnet update')
            except Empty:
                if _mb_bcnt_cls_debug: print('\tno bacnet update')
                # continue
                return

            if _mb_bcnt_cls_debug: print('\tpost try')

            for dev_inst in val_dict.keys():
                if dev_inst not in self.app_dict:
                    continue

                if _mb_bcnt_cls_debug: print('\tdev inst:', dev_inst, '-',
                                             self.app_dict[dev_inst].localDevice.objectName)

                for obj_inst, obj_values in val_dict[dev_inst].items():
                    if _mb_bcnt_cls_debug: print('\t\t', obj_inst, end=' - ')

                    if obj_inst not in self.app_dict[dev_inst].objectIdentifier:
                        if _mb_bcnt_cls_debug: print('OBJECT INSTANCE NOT IN APPLICATION DICT')
                        continue

                    bcnt_obj = self.app_dict[dev_inst].objectIdentifier[obj_inst]

                    if _mb_bcnt_cls_debug: print(bcnt_obj.objectName)

                    if _mb_bcnt_cls_debug: print('\t\t\t', obj_values)

                    if obj_values['error'] != 0:
                        # change_object_prop_if_new(bcnt_obj, 'reliability', 'communicationFailure')
                        # change_object_prop_if_new(bcnt_obj, 'statusFlags', 1, arr_idx='fault')
                        # change_object_prop_if_new(bcnt_obj, 'modbusCommErr', obj_values['error'])
                        bcnt_obj.WriteProperty('reliability', 'communicationFailure', direct=True)
                        change_object_prop_if_new(bcnt_obj, 'statusFlags', 0, arr_idx='fault')
                        bcnt_obj.WriteProperty('modbusCommErr', obj_values['error'], direct=True)
                    else:
                        # change_object_prop_if_new(bcnt_obj, 'reliability', 'noFaultDetected')
                        # change_object_prop_if_new(bcnt_obj, 'statusFlags', 0, arr_idx='fault')
                        # change_object_prop_if_new(bcnt_obj, 'modbusCommErr', 'noFaultDetected')
                        # bcnt_obj._values['presentValue'] = obj_values['value']
                        bcnt_obj.WriteProperty('reliability', 'noFaultDetected', direct=True)
                        # print('reliability done')
                        change_object_prop_if_new(bcnt_obj, 'statusFlags', 0, arr_idx='fault')
                        # print('status flags done')
                        bcnt_obj.WriteProperty('modbusCommErr', 'noFaultDetected', direct=True)
                        # print('modbus comm err done')
                        bcnt_obj.WriteProperty('presentValue', obj_values['value'], direct=True)
                        # print('pv done')
            if _mb_bcnt_cls_debug: print('end of loop')
        if _mb_bcnt_cls_debug: print('end of recurring')


def change_object_prop_if_new(bcnt_obj, propid, obj_val, arr_idx=None):
    if arr_idx is None:
        if bcnt_obj.ReadProperty(propid) != obj_val:
            bcnt_obj.WriteProperty(propid, obj_val, direct=True)
    else:
        # print(bcnt_obj._properties[propid].datatype)
        # print(issubclass(bcnt_obj._properties[propid].datatype, BitString))
        if issubclass(bcnt_obj._properties[propid].datatype, BitString):  # need to split bitstring in if because
            # library will only use arrayIndex for objects with the Array() class as a parent
            # values are not always stored as their datatype, merely as an acceptable input.  Ex: StatusFlags are
            # stored as a list [0, 1, 0, 1] rather than the class StatusFlags([0, 1, 0, 1])
            if isinstance(arr_idx, str):
                if arr_idx in bcnt_obj._properties[propid].datatype.bitNames:
                    bs_idx = bcnt_obj._properties[propid].datatype.bitNames[arr_idx]
                else:
                    return  # silent failure
            else:
                bs_idx = arr_idx

            if bcnt_obj._values[propid][bs_idx] != obj_val:
                arry = scopy(bcnt_obj._values[propid])
                arry[bs_idx] = obj_val
                bcnt_obj.WriteProperty(propid, arry, direct=True)
        elif bcnt_obj.ReadProperty(propid, arrayIndex=arr_idx) != obj_val:
            bcnt_obj.WriteProperty(propid, obj_val, arrayIndex=arr_idx, direct=True)
