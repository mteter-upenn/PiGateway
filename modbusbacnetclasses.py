import time
from queue import Empty

from bacpypes.debugging import bacpypes_debugging, ModuleLogger

from bacpypes.service.device import LocalDeviceObject
from bacpypes.constructeddata import ArrayOf
from bacpypes.primitivedata import Real, Integer, CharacterString, Enumerated
from bacpypes.object import register_object_type, AnalogInputObject, ReadableProperty  # , AnalogValueObject, Property
from bacpypes.task import RecurringTask

# from bacpypes.errors import ExecutionError

from bacpypes.basetypes import PropertyIdentifier

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


ModbusScaling = ArrayOf(Real)


class ModbusErrors(Enumerated):
    enumerations = \
        {'noFaultDetected': 0
        , 'noSensor': 1
        }

    @classmethod
    def is_valid(cls, arg):
        """Return True if arg is valid value for the class.  If the string
        value is wrong for the enumeration, the encoding will fail.
        """
        if isinstance(arg, int) and arg >= 0:
            return arg in cls.enumerations.values()
        elif isinstance(arg, str):
            return arg in cls.enumerations.keys()
        return False


# @bacpypes_debugging
# class RegisterScalingProperty(Property):
#     def __init__(self, identifier):
#         if _debug: RegisterScalingProperty._debug("__init__ %r", identifier)
#         Property.__init__(self, identifier, Real, default=None, optional=False, mutable=False)
#         self._is_scaled()

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
#             rx_queue = obj._rx_queue
#             # is_scaled = obj._is_scaled
#             reg_scaling = obj._values['modbusScaling']  # ArrayOf[lenArr, m, b]
#             # status_flags = obj._values['statusFlags']
#             # print(status_flags)
#         except KeyError:
#             return 0.0
#
#         if _mb_bcnt_cls_debug:
#             # return test value
#             value = register_start
#             reliability = True
#         else:
#             # clear queue of any old data or this will be read
#             while not rx_queue.empty():
#                 rx_queue.get(block=False)
#             # return value from modbus register bank
#             value, reliability = register_reader.get_register_format(dev_inst, mb_func, register_start, num_regs,
#                                                                      reg_frmt, word_order, rx_queue)
#
#         if _debug: ModbusValueProperty._debug("    - value: %r", value)
#
#         # print('ReadProperty from property', obj.ReadProperty('objectIdentifier'), dev_inst)
#         # print('obj parent is', self.object_parent)
#         if reliability != 'noFaultDetected':
#             obj._values['reliability'] = reliability
#             obj._values['statusFlags']['fault'] = 1
#             if reliability == 'communicationFailure':
#                 obj._values['modbusCommErr'] = value
#             else:
#                 obj._values['modbusCommErr'] = 0
#             value = obj._values[self.identifier]  # set value to return to the current value stored
#         else:
#             obj._values['reliability'] = reliability
#             obj._values['statusFlags']['fault'] = 0
#             obj._values['modbusCommErr'] = 0
#             value = value * reg_scaling[1] + reg_scaling[2]  # scale modbus value to bacnet value
#
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


@bacpypes_debugging
class ModbusAnalogInputObject(AnalogInputObject):
    properties = [
        # ModbusValueProperty('presentValue'),
        ReadableProperty('modbusFunction', Integer),
        ReadableProperty('registerStart', Integer),
        ReadableProperty('numberOfRegisters', Integer),
        ReadableProperty('registerFormat', CharacterString),
        ReadableProperty('wordOrder', CharacterString),
        ReadableProperty('modbusScaling', ModbusScaling),
        ReadableProperty('modbusCommErr', Integer)
    ]

    # def __init__(self, parent_device_inst, register_reader, rx_queue, **kwargs):
    def __init__(self, **kwargs):
        if _debug: ModbusAnalogInputObject._debug("__init__ %r", kwargs)
        AnalogInputObject.__init__(self, **kwargs)
        # self._register_reader = register_reader
        # self._parent_device_inst = parent_device_inst
        # self._rx_queue = rx_queue
        self.reliability = 'communicationFailure'
        # self.statusFlags['fault'] = 1
        self.modbusCommErr = 19
        self.outOfService = False
        self.eventState = 'normal'

        # print(self._values['objectName'])
        # self._values['reliability'] = 'communicationFailure'
        # print(self._values['reliability'], self._values['statusFlags'], self._values['statusFlags']['fault'], '\n')

    # def ReadProperty(self, propid, arrayIndex=None):
    #     print('object overwrite ReadProperty')
    #     if propid=='presentValue':
    #         prop = self._properties.get(propid)
    #         if not prop:
    #             raise PropertyError(propid)
    #
    #         # defer to the property to get the value
    #         return prop.ReadProperty(self, arrayIndex)
    #     else:
    #         return AnalogInputObject.ReadProperty(self, propid, arrayIndex=arrayIndex)

    def ReadProperty(self, propid, arrayIndex=None):
        if _mb_bcnt_cls_debug: print(propid, self.propid, end=', ')  # might need self._values[propid]
        value = AnalogInputObject.ReadProperty(self, propid, arrayIndex=arrayIndex)
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
    def __init__(self, bank_to_bcnt_queue, app_dict, interval, max_run_time=10):
        RecurringTask.__init__(self, interval)

        self.bank_to_bcnt_queue = bank_to_bcnt_queue
        self.app_dict = app_dict
        self.max_run_time = max_run_time / 1000  # set in ms to coincide with interval

        # install it
        self.install_task()

    def process_task(self):
        start_time = time.time()
        if _mb_bcnt_cls_debug: print('start recurring task')

        # while (not self.bank_to_bcnt_queue.empty()) and (time.time() - start_time < self.max_run_time):
        if not self.bank_to_bcnt_queue.empty():
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

                for obj_inst, obj_values in val_dict[dev_inst].items():
                    if _mb_bcnt_cls_debug: print('\tobject instance', obj_inst)

                    if obj_inst not in self.app_dict[dev_inst].objectIdentifier:
                        # print('\t\tobject instance not in application dict')
                        continue

                    # print('\t\tobject instance in application dict')
                    if _mb_bcnt_cls_debug: print('\t\tobject value', obj_values)

                    bcnt_obj = self.app_dict[dev_inst].objectIdentifier[obj_inst]

                    if obj_values['error'] != 0:
                        change_object_prop_if_new(bcnt_obj, 'reliability', 'communicationFailure')
                        # change_object_prop_if_new(bcnt_obj, 'statusFlags', 1, arr_val='fault')
                        change_object_prop_if_new(bcnt_obj, 'modbusCommErr', obj_values['error'])
                        # bcnt_obj._values['presentValue'] = obj_values['value']
                    else:
                        change_object_prop_if_new(bcnt_obj, 'reliability', 'noFaultDetected')
                        # change_object_prop_if_new(bcnt_obj, 'statusFlags', 0, arr_val='fault')
                        change_object_prop_if_new(bcnt_obj, 'modbusCommErr', 0)
                        bcnt_obj._values['presentValue'] = obj_values['value']
            if _mb_bcnt_cls_debug: print('end of recurring')
                # if reliability != 'noFaultDetected':
                #             obj._values['reliability'] = reliability
                #             obj._values['statusFlags']['fault'] = 1
                #             if reliability == 'communicationFailure':
                #                 obj._values['modbusCommErr'] = value
                #             else:
                #                 obj._values['modbusCommErr'] = 0
                #             value = obj._values[self.identifier]  # set value to return to the current value stored
                #         else:
                #             obj._values['reliability'] = reliability
                #             obj._values['statusFlags']['fault'] = 0
                #             obj._values['modbusCommErr'] = 0
                #             value = value * reg_scaling[1] + reg_scaling[2]  # scale modbus value to bacnet value


def change_object_prop_if_new(bcnt_obj, property, obj_val, arr_val=None):

    if arr_val is None:
        if bcnt_obj._values[property] != obj_val:
            bcnt_obj._values[property] = obj_val
    else:
        print('property', bcnt_obj._values[property])
        print(bcnt_obj.statusFlags)
        if bcnt_obj._values[property][arr_val] != obj_val:
            bcnt_obj._values[property][arr_val] = obj_val
