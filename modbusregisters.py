from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from queue import Empty  # , Full
import threading
from mbpy.mb_poll import modbus_poller
import time
from struct import pack, unpack
# from pprint import pprint
_debug = 0
_log = ModuleLogger(globals())
# _debug_modbus_registers = False

# globals
one_register_formats = ('uint16', 'sint16', 'sm1k16', 'sm10k16', 'bin', 'hex', 'ascii')
two_register_formats = ('uint32', 'sint32', 'um1k32', 'sm1k32', 'um10k32', 'sm10k32', 'float')
three_register_formats = ('uint48', 'um1k48', 'sm1k48', 'um10k48', 'sm10k48')
four_register_formats = ('uint64', 'sint64', 'um1k64', 'sm1k64', 'um10k64', 'sm10k64', 'double', 'energy')
register_formats = one_register_formats + two_register_formats + three_register_formats + four_register_formats


class ModbusCommError(Exception):
    pass


class ModbusRequestLauncher(threading.Thread):
    # This class takes a dictionary of modbus requests and routinely triggers them to run
    _register_clusters = {}
    _unq_ip_last_req = {}

    def __init__(self, modbus_requests, unq_ip_last_req):
        threading.Thread.__init__(self, daemon=True)
        self._register_clusters = modbus_requests
        self._unq_ip_last_req = unq_ip_last_req

    def run(self):
        # time_at_loop_start = time.time()
        for reg_clstr, clstr_val in self._register_clusters.items():
            # if clstr_val[1] < time_at_loop_start:
            time.sleep(0.3)
            cur_time = time.time()
            new_expected_run_time = max(cur_time, self._unq_ip_last_req[clstr_val[3]] + 0.5)
            self._unq_ip_last_req[clstr_val[3]] = new_expected_run_time
            clstr_val[1] = new_expected_run_time + clstr_val[2] / 1000.0
            clstr_val[0].start()
        while True:
            # time.sleep(5)
            # time_at_loop_start = time.time()

            # make all modbus requests
            for reg_clstr, clstr_val in self._register_clusters.items():
                cur_time = time.time()
                if clstr_val[1] < cur_time:
                    new_expected_run_time = max(cur_time, self._unq_ip_last_req[clstr_val[3]] + 0.5)
                    self._unq_ip_last_req[clstr_val[3]] = new_expected_run_time
                    clstr_val[1] = new_expected_run_time + clstr_val[2] / 1000.0
                    clstr_val[0].run(delay=max(new_expected_run_time - cur_time, 0))


def add_meter_instance_to_dicts(meter_map_dict, mb_to_bank_queue, object_bank, modbus_requests, unq_ip_last_req):
    """
    Parses meter object/register data into dictionaries of modbus requests and their values

    :param meter_map_dict: Meter mapping of modbus registers to BACnet objects, typically taken from a json file.
    :param mb_to_bank_queue: Queue to be given to Modbus requests to push data to a storage/format thread
    :param object_bank: Dictionary of devices, Modbus function, objects and their values.
    {device instance:
        {Modbus function:
            [Modbus function polling time,
            {object instance: {value, time of request, error, time of error request},
            object instance: [value, time of request, error, time of error request],
            ...}
            ],
        ...},
    ...}
    :param modbus_requests: Dictionary of Modbus requests
    {(device instance, cluster id): [Modbus request thread, expected start time, polling time, device ip],
    ...}
    :param unq_ip_last_req: Dictionary of ips and the last time a Modbus request was made to that unit.  If more than
    one request is made very quickly the Modbus gateways typically do not handle it well.  It is best to therefore delay
    requests made to the same ip and this stores the last time one was made.
    :return: True or False based on success
    """

    func_regs = {}
    bcnt_inst = meter_map_dict['deviceInstance']
    if bcnt_inst in object_bank:  # bacnet instance already exists!
        return False
    clstr = 0
    mb_ip = meter_map_dict['deviceIP']
    if mb_ip == '0.0.0.0':
        mb_ip = '/dev/serial0'
    mb_id = meter_map_dict['modbusId']
    mb_port = meter_map_dict['modbusPort']
    val_types = {'holdingRegisters': 3, 'inputRegisters': 4, 'coilBits': 1, 'inputBits': 2}

    trigger_time = time.time()
    if mb_ip not in unq_ip_last_req:
        unq_ip_last_req[mb_ip] = trigger_time

    for val_type, mb_func in val_types.items():
        if val_type not in meter_map_dict:  # ('holdingRegisters', 'inputRegisters', 'coilBits', 'inputBits'):
            continue

        mb_polling_time = meter_map_dict[val_type]['pollingTime']
        mb_request_timeout = meter_map_dict[val_type]['requestTimeout']
        mb_grp_cons = True if meter_map_dict[val_type]['groupConsecutive'] == 'yes' else False
        mb_grp_gaps = True if meter_map_dict[val_type]['groupGaps'] == 'yes' else False
        mb_word_order = meter_map_dict[val_type]['wordOrder']

        raw_objs = {}
        raw_regs_list = []
        for register in meter_map_dict[val_type]['registers']:
            # don't bother storing points we won't look at
            if register['poll'] == 'no':
                continue

            start_reg = register['start']
            obj_inst = register['objectInstance']
            num_regs = format_to_num_regs(register['format'])
            obj_pt_scale = register['pointScale']
            obj_eq_m = (obj_pt_scale[3] - obj_pt_scale[2]) / (obj_pt_scale[1] - obj_pt_scale[0])
            obj_eq_b = obj_pt_scale[2] - obj_eq_m * obj_pt_scale[0]

            # data, time of data retrieval, comm err, time of comm err, start reg, format, slope, intercept
            # raw_objs[obj_inst] = [0, 0.0, 19, 0.0, start_reg, register['format'], mb_word_order, obj_eq_m, obj_eq_b]
            raw_objs[obj_inst] = {'value': 0, 'val_time': 0.0, 'error': 19, 'err_time': 0.0, 'register': start_reg,
                                  'format': register['format'], 'word_order': mb_word_order, 'scale_slope': obj_eq_m,
                                  'scale_int': obj_eq_b, 'obj_type': 'analogInput'}
            last_reg = start_reg + num_regs - 1
            # for ii in range(start_reg, start_reg + num_regs):
            #     raw_regs_list.append([ii, start_reg, last_reg, obj_inst])
            raw_regs_list.append([start_reg, last_reg, obj_inst])

        # set up dicts for self.register_bank{}
        func_regs[mb_func] = [meter_map_dict[val_type]['pollingTime'], raw_objs]

        raw_regs_list.sort()

        clstr_reg_start = raw_regs_list[0][0]
        # num_map_regs = len(raw_regs_list)
        object_inst_list = []

        if mb_grp_cons and mb_grp_gaps:  # clusters should span multiple points and registers we won't record
            last_iter_reg = raw_regs_list[0][1]
            # print('GROUP CONSECUTIVE AND GAPPED REGISTERS')
            for mb_obj in raw_regs_list:
                object_inst_list.append(mb_obj[2])

                if mb_obj[1] - clstr_reg_start > 125:  # if current object pushes over modbus register limit
                    object_inst_list.pop()  # remove from list
                    mb_poll_thread = ModbusPollThread(mb_to_bank_queue, bcnt_inst, mb_ip, mb_id, mb_func,
                                                      clstr_reg_start, last_iter_reg - clstr_reg_start
                                                      + 1, mb_request_timeout, mb_port, object_inst_list)
                    modbus_requests[(bcnt_inst, clstr)] = [mb_poll_thread, trigger_time, mb_polling_time, mb_ip]
                    # print(bcnt_inst, clstr, 'mb_id:', mb_id, 'mb_func:', mb_func, 'start:', clstr_reg_start, 'len:',
                    #       last_iter_reg - clstr_reg_start + 1, 'obj list:', object_inst_list)
                    object_inst_list = [mb_obj[2]]  # start next object list with the instance that doesn't fit here

                    clstr += 1  # tick clstr counter
                    clstr_reg_start = mb_obj[0]  # set new start to current object
                elif mb_obj[2] == raw_regs_list[-1][2]:  # last object
                    last_iter_reg = mb_obj[1]
                    mb_poll_thread = ModbusPollThread(mb_to_bank_queue, bcnt_inst, mb_ip, mb_id, mb_func,
                                                      clstr_reg_start, last_iter_reg - clstr_reg_start
                                                      + 1, mb_request_timeout, mb_port, object_inst_list)
                    modbus_requests[(bcnt_inst, clstr)] = [mb_poll_thread, trigger_time, mb_polling_time, mb_ip]
                    # print(bcnt_inst, clstr, 'mb_id:', mb_id, 'mb_func:', mb_func, 'start:', clstr_reg_start, 'len:',
                    #       last_iter_reg - clstr_reg_start + 1, 'obj list:', object_inst_list)
                last_iter_reg = mb_obj[1]
        elif mb_grp_cons:
            last_iter_reg = raw_regs_list[0][1]
            # print('GROUP CONSECUTIVE REGISTERS')
            for mb_obj in raw_regs_list:
                object_inst_list.append(mb_obj[2])

                if mb_obj[0] - last_iter_reg > 1 or mb_obj[1] - clstr_reg_start > 125:  # if there is a gap between
                    # objects or if current object pushes over modbus register limit
                    object_inst_list.pop()  # remove from list
                    mb_poll_thread = ModbusPollThread(mb_to_bank_queue, bcnt_inst, mb_ip, mb_id, mb_func,
                                                      clstr_reg_start, last_iter_reg - clstr_reg_start
                                                      + 1, mb_request_timeout, mb_port, object_inst_list)
                    modbus_requests[(bcnt_inst, clstr)] = [mb_poll_thread, trigger_time, mb_polling_time, mb_ip]
                    # print(bcnt_inst, clstr, 'mb_id:', mb_id, 'mb_func:', mb_func, 'start:', clstr_reg_start, 'len:',
                    #       last_iter_reg - clstr_reg_start + 1, 'obj list:', object_inst_list)
                    object_inst_list = [mb_obj[2]]  # start next object list with the instance that doesn't fit here

                    clstr += 1  # tick clstr counter
                    clstr_reg_start = mb_obj[0]  # set new start to current object
                elif mb_obj[2] == raw_regs_list[-1][2]:  # last object
                    last_iter_reg = mb_obj[1]
                    mb_poll_thread = ModbusPollThread(mb_to_bank_queue, bcnt_inst, mb_ip, mb_id, mb_func,
                                                      clstr_reg_start, last_iter_reg - clstr_reg_start
                                                      + 1, mb_request_timeout, mb_port, object_inst_list)
                    modbus_requests[(bcnt_inst, clstr)] = [mb_poll_thread, trigger_time, mb_polling_time, mb_ip]
                    # print(bcnt_inst, clstr, 'mb_id:', mb_id, 'mb_func:', mb_func, 'start:', clstr_reg_start, 'len:',
                    #       last_iter_reg - clstr_reg_start + 1, 'obj list:', object_inst_list)
                last_iter_reg = mb_obj[1]
        else:
            # print('NO REGISTER GROUPING')
            for mb_obj in raw_regs_list:
                mb_poll_thread = ModbusPollThread(mb_to_bank_queue, bcnt_inst, mb_ip, mb_id, mb_func,
                                                  mb_obj[0], mb_obj[1] - mb_obj[0] + 1, mb_request_timeout, mb_port,
                                                  [mb_obj[2]])
                modbus_requests[(bcnt_inst, clstr)] = [mb_poll_thread, trigger_time, mb_polling_time, mb_ip]
                # print(bcnt_inst, clstr, 'mb_id:', mb_id, 'mb_func:', mb_func, 'start:', mb_obj[0], 'len:',
                #       mb_obj[1] - mb_obj[0] + 1, 'obj list:', [mb_obj[2]])
                clstr += 1

        object_bank[bcnt_inst] = func_regs
    return True


class ModbusFormatAndStorage(threading.Thread):
    _object_bank = {}

    def __init__(self, mb_to_bank_queue, bank_to_bcnt_queue, object_bank):
        threading.Thread.__init__(self, daemon=True)

        self.mb_to_bank_queue = mb_to_bank_queue
        self.bank_to_bcnt_queue = bank_to_bcnt_queue
        self._object_bank = object_bank

    def run(self):
        while True:
            try:
                rx_resp = self.mb_to_bank_queue.get_nowait()  # no reason to hang here, just wait until next loop

                self._mb_resp_to_bcnt(rx_resp)

            except Empty:
                pass

    def _mb_resp_to_bcnt(self, rx_resp):
        # {'type': 'modbus', 'bcnt_inst': self.bcnt_instance, 'mb_func': self.mb_func,
        #  'mb_reg': self.register, 'mb_num_regs': self.num_regs, 'mb_otpt': otpt,
        #  'mb_resp_time': time.time()}
        dev_inst = rx_resp['bcnt_inst']
        mb_func = rx_resp['mb_func']

        if dev_inst not in self._object_bank or mb_func not in self._object_bank[dev_inst]:
            # modbus response does not coordinate with any devices in the bank
            return

        bcnt_q_dict = {dev_inst: {}}
        mb_start_reg = rx_resp['mb_reg']
        # mb_num_regs = rx_resp['mb_num_regs']
        mb_resp = rx_resp['mb_otpt']
        mb_resp_time = rx_resp['mb_resp_time']

        inst_reg_bank = self._object_bank[dev_inst][mb_func][1]
        if mb_resp[0] == 'Err':
            # if there is an error, don't update registers
            for obj in rx_resp['obj_list']:
                if obj in inst_reg_bank:
                    inst_reg_bank[obj]['error'] = mb_resp[1]
                    inst_reg_bank[obj]['err_time'] = mb_resp_time

                    bcnt_q_dict[dev_inst][(inst_reg_bank[obj]['obj_type'], obj)] = {'value':
                                                                                    inst_reg_bank[obj]['value'],
                                                                                    'error': mb_resp[1]}
                    # if _debug_modbus_registers: print(obj, mb_resp)
        else:
            for obj in rx_resp['obj_list']:
                if obj in inst_reg_bank:  # only add to reg bank where necessary
                    obj_frmt = inst_reg_bank[obj]['format']
                    obj_regs = mb_resp[inst_reg_bank[obj]['register'] - mb_start_reg:
                                       inst_reg_bank[obj]['register'] - mb_start_reg + format_to_num_regs(obj_frmt)]
                    obj_val = format_registers_to_point(obj_regs, obj_frmt, inst_reg_bank[obj]['word_order'],
                                                        inst_reg_bank[obj]['scale_slope'],
                                                        inst_reg_bank[obj]['scale_int'])

                    inst_reg_bank[obj]['value'] = obj_val
                    inst_reg_bank[obj]['val_time'] = mb_resp_time
                    inst_reg_bank[obj]['error'] = 0
                    inst_reg_bank[obj]['err_time'] = mb_resp_time

                    bcnt_q_dict[dev_inst][(inst_reg_bank[obj]['obj_type'], obj)] = {'value': obj_val, 'error': 0}

                    # if _debug_modbus_registers: print(obj, obj_val)

        self.bank_to_bcnt_queue.put(bcnt_q_dict, timeout=0.1)
        return


def format_to_num_regs(frmt):
    if frmt in one_register_formats:
        return 1
    # elif frmt in two_register_formats:
    #     return 2
    elif frmt in three_register_formats:
        return 3
    elif frmt in four_register_formats:
        return 4
    else:
        return 2


def format_registers_to_point(registers, reg_frmt, reg_wo, slope=1, intercept=0):
    num_regs = len(registers)
    if num_regs < 1 or num_regs > 4:
        return 0.0

    if num_regs == 1 and reg_frmt not in one_register_formats:
        return 0.0
    if num_regs == 2 and reg_frmt not in two_register_formats:
        return 0.0
    if num_regs == 3 and reg_frmt not in three_register_formats:
        return 0.0
    if num_regs == 4 and reg_frmt not in four_register_formats:
        return 0.0

    pt_val = 0.0

    if reg_frmt in one_register_formats:      # ('bin', 'hex', 'ascii', 'uint16', 'sint16', 'sm1k16', 'sm10k16'):
        reg_0 = registers[0]
        # for reg_0 in registers:  # , self.pckt[2::4], self.pckt[3::4]):
        if reg_frmt == 'bin':
            return bin(reg_0 * slope + intercept)
        elif reg_frmt == 'hex':
            return hex(reg_0 * slope + intercept)
        elif reg_frmt == 'ascii':
            byte_1 = bytes([reg_0 >> 8])
            byte_0 = bytes([reg_0 & 0xff])
            # b1 = bytes([56])
            # b0 = bytes([70])
            return byte_1.decode('ascii', 'ignore') + byte_0.decode('ascii', 'ignore')
        elif reg_frmt == 'uint16':
            pt_val = reg_0
        elif reg_frmt == 'sint16':
            pt_val = unpack('h', pack('H', reg_0))[0]
        elif reg_frmt in ('sm1k16', 'sm10k16'):
            mplr = 1
            if reg_0 >> 15 == 1:
                mplr = -1

            pt_val = (reg_0 & 0x7fff) * mplr
    elif reg_frmt in two_register_formats:
        # ('float', 'uint32', 'sint32', 'um1k32', 'sm1k32', 'um10k32','sm10k32'):
        if reg_wo == 'msw':
            registers[::2], registers[1::2] = registers[1::2], registers[::2]

        reg_0 = registers[0]
        reg_1 = registers[1]
        # for reg_0, reg_1 in zip(registers[::2], registers[1::2]):  # , self.pckt[2::4], self.pckt[3::4]):
        if reg_frmt == 'uint32':
            pt_val = (reg_1 << 16) | reg_0
        elif reg_frmt == 'sint32':
            pt_val = unpack('i', pack('I', (reg_1 << 16) | reg_0))[0]
        elif reg_frmt == 'float':
            pt_val = unpack('f', pack('I', (reg_1 << 16) | reg_0))[0]
        elif reg_frmt == 'um1k32':
            pt_val = reg_1 * 1000 + reg_0
        elif reg_frmt == 'sm1k32':
            if (reg_1 >> 15) == 1:
                reg_1 = (reg_1 & 0x7fff)
                pt_val = (-1) * (reg_1 * 1000 + reg_0)
            else:
                pt_val = reg_1 * 1000 + reg_0
        elif reg_frmt == 'um10k32':
            pt_val = reg_1 * 10000 + reg_0
        elif reg_frmt == 'sm10k32':
            if (reg_1 >> 15) == 1:
                reg_1 = (reg_1 & 0x7fff)
                pt_val = (-1) * (reg_1 * 10000 + reg_0)
            else:
                pt_val = reg_1 * 10000 + reg_0
    elif reg_frmt in three_register_formats:  # ('uint48', 'sint48', 'um1k48', 'sm1k48', 'um10k48', 'sm10k48'):
        if reg_wo == 'msw':
            registers[::3], registers[2::3] = registers[2:3], registers[::3]

        reg_0 = registers[0]
        reg_1 = registers[1]
        reg_2 = registers[2]
        # for r0, r1, r2 in zip(regs[::3], regs[1::3], regs[2::3]):
        if reg_frmt == 'uint48':
            pt_val = (reg_2 << 32) | (reg_1 << 16) | reg_0
        elif reg_frmt == 'sint48':
            pt_val = 0.0
        elif reg_frmt == 'um1k48':
            pt_val = (reg_2 * (10 ** 6)) + (reg_1 * 1000) + reg_0
        elif reg_frmt == 'sm1k48':
            if (reg_2 >> 15) == 1:
                reg_2 = (reg_2 & 0x7fff)
                pt_val = (-1) * ((reg_2 * (10**6)) + (reg_1 * 1000) + reg_0)
            else:
                pt_val = (reg_2 * (10**6)) + (reg_1 * 1000) + reg_0
        elif reg_frmt == 'um10k48':
            pt_val = (reg_2 * (10**8)) + (reg_1 * 10000) + reg_0
        elif reg_frmt == 'sm10k48':
            if (reg_2 >> 15) == 1:
                reg_2 = (reg_2 & 0x7fff)
                pt_val = (-1) * ((reg_2 * (10**8)) + (reg_1 * 10000) + reg_0)
            else:
                pt_val = (reg_2 * (10**8)) + (reg_1 * 10000) + reg_0
    elif reg_frmt in four_register_formats:
        # ('uint64', 'sint64', 'um1k64', 'sm1k64', 'um10k64', 'sm10k64', 'engy', 'dbl')
        if reg_wo == 'msw':
            registers[::4], registers[1::4], registers[2::4], registers[3::4] = registers[3::4], registers[2::4], \
                                                                                registers[1::4], registers[::4]

        reg_0 = registers[0]
        reg_1 = registers[1]
        reg_2 = registers[2]
        reg_3 = registers[3]
        # for r0, r1, r2, r3 in zip(regs[::4], regs[1::4], regs[2::4], regs[3::4]):
        if reg_frmt == 'uint64':
            pt_val = (reg_3 << 48) | (reg_2 << 32) | (reg_1 << 16) | reg_0
        elif reg_frmt == 'sint64':
            pt_val = unpack('q', pack('Q', (reg_3 << 48) | (reg_2 << 32) | (reg_1 << 16) | reg_0))[0]
        elif reg_frmt == 'um1k64':
            pt_val = reg_3 * (10 ** 9) + reg_2 * (10 ** 6) + reg_1 * 1000 + reg_0
        elif reg_frmt == 'sm1k64':
            if (reg_3 >> 15) == 1:
                reg_3 = (reg_3 & 0x7fff)
                pt_val = (-1) * (reg_3 * (10 ** 9) + reg_2 * (10 ** 6) + reg_1 * 1000 + reg_0)
            else:
                pt_val = reg_3 * (10 ** 9) + reg_2 * (10 ** 6) + reg_1 * 1000 + reg_0
        elif reg_frmt == 'um10k64':
            pt_val = reg_3 * (10 ** 12) + reg_2 * (10 ** 8) + reg_1 * 10000 + reg_0
        elif reg_frmt == 'sm10k64':
            if (reg_3 >> 15) == 1:
                reg_3 = (reg_3 & 0x7fff)
                pt_val = (-1) * (reg_3 * (10 ** 12) + reg_2 * (10 ** 8) + reg_1 * 10000 + reg_0)
            else:
                pt_val = reg_3 * (10 ** 12) + reg_2 * (10 ** 8) + reg_1 * 10000 + reg_0
        elif reg_frmt == 'engy':
            # split r3 into engineering and mantissa bytes THIS WILL NOT HANDLE MANTISSA - DOCUMENTATION DOES
            # NOT EXIST ON HOW TO HANDLE IT WITH THEIR UNITS

            engr = unpack('b', pack('B', (reg_3 >> 8)))[0]
            pt_val = ((reg_2 << 32) | (reg_1 << 16) | reg_0) * (10 ** engr)
        elif reg_frmt == 'dbl':
            pt_val = unpack('d', pack('Q', (reg_3 << 48) | (reg_2 << 32) | (reg_1 << 16) | reg_0))[0]
    else:
        pt_val = 0.0
    return pt_val * slope + intercept


@bacpypes_debugging
class ModbusPollThread(threading.Thread):
    def __init__(self, tx_queue, bcnt_instance, ip, mb_id, mb_func, register, num_regs, timeout, port, object_list):
        threading.Thread.__init__(self, daemon=False)  # should finish with comms first
        self.tx_queue = tx_queue

        self.ip = ip
        self.mb_id = mb_id
        self.mb_func = mb_func
        self.register = register
        self.num_regs = num_regs
        self.timeout = timeout  # timeout in milliseconds
        self.port = port
        self.bcnt_instance = bcnt_instance
        self.currently_running = False
        self.object_list = object_list

    def run(self, delay=0.0):
        if not self.currently_running:
            self.currently_running = True
            time.sleep(delay)

            if _debug:
                ModbusPollThread._debug('making modbus request for %s %s at %s', self.ip, self.mb_id, time.time())
            # print('ip:   ', self.ip)
            # print('id:   ', self.mb_id)
            # print('func: ', self.mb_func)
            # print('start:', self.register)
            # print('regs: ', self.num_regs)
            otpt = modbus_poller(self.ip, self.mb_id, self.register, self.num_regs, mb_func=self.mb_func,
                                 mb_timeout=self.timeout, port=self.port, data_type='uint16')  # , pi_pin_cntl=15)
            tx_resp = {'type': 'modbus', 'bcnt_inst': self.bcnt_instance, 'mb_func': self.mb_func,
                       'mb_reg': self.register, 'mb_num_regs': self.num_regs, 'mb_otpt': otpt,
                       'mb_resp_time': time.time(), 'obj_list': self.object_list}
            self.tx_queue.put(tx_resp, 0.1)
            if otpt[0] == 'Err':
                if _debug: ModbusPollThread._debug('got modbus error %s', otpt)
            else:
                if _debug: ModbusPollThread._debug('got modbus response')
            self.currently_running = False
        else:
            if _debug: ModbusPollThread._debug('currently running')


# class TupleSortingOn0(tuple):
#     def __lt__(self, rhs):
#         return self[0] < rhs[0]
#
#     def __gt__(self, rhs):
#         return self[0] > rhs[0]
#
#     def __le__(self, rhs):
#         return self[0] <= rhs[0]
#
#     def __ge__(self, rhs):
#         return self[0] >= rhs[0]
