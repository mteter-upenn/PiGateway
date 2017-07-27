from queue import Empty, Full
import threading
from mbpy.mbpy import mb_poll
import time
from struct import pack, unpack
# from pprint import pprint

# globals
one_register_formats = ('uint16', 'sint16', 'sm1k16', 'sm10k16', 'bin', 'hex', 'ascii')
two_register_formats = ('uint32', 'sint32', 'um1k32', 'sm1k32', 'um10k32', 'sm10k32', 'float')
three_register_formats = ('uint48', 'um1k48', 'sm1k48', 'um10k48', 'sm10k48')
four_register_formats = ('uint64', 'sint64', 'um1k64', 'sm1k64', 'um10k64', 'sm10k64', 'double', 'energy')
register_formats = one_register_formats + two_register_formats + three_register_formats + four_register_formats


# class for bacnet points to use to access the stored values in the bank which runs in a different thread
class RegisterReader:
    def __init__(self, tx_queue):  # , rx_queue):
        # global one_register_formats, two_register_formats, three_register_formats, four_register_formats, \
        #     register_formats
        self.tx_queue = tx_queue
        # self.rx_queue = rx_queue

    def get_register_raw(self, dev_instance, mb_func, register, rx_queue, queue_timeout=100.0):
        self.get_register_format(dev_instance, mb_func, register, 1, 'uint16', 'lsw', rx_queue,
                                 queue_timeout=queue_timeout)

    def get_register_format(self, dev_instance, mb_func, register, num_regs, reg_format, word_order, rx_queue,
                            queue_timeout=100.0):
        reg_bank_req = (0, {'type': 'bacnet', 'bcnt_inst': dev_instance, 'mb_func': mb_func, 'mb_reg': register,
                            'mb_num_regs': num_regs, 'mb_frmt': reg_format, 'mb_wo': word_order}, rx_queue)
        try:
            self.tx_queue.put(TupleSortingOn0(reg_bank_req), timeout=queue_timeout / 1000.0)

            try:
                reg_bank_resp = rx_queue.get(timeout=1.5 * queue_timeout / 1000.0)
            except Empty:
                print('RegisterReader returned empty queue')
                return 0.0, False  # (value, reliability)

            if self._check_dict_equality(reg_bank_req[1], reg_bank_resp[1]):
                print('RegisterReader returned', reg_bank_resp)
                return reg_bank_resp[1]['bcnt_value'], reg_bank_resp[1]['bcnt_valid']
            print('RegisterReader had unequal dicts')
            return 0.0, False  # (value, reliability)
        except Full:
            print('RegisterReader full queue')
            return 0.0, False  # (value, reliability)

    @staticmethod
    def _check_dict_equality(dict1, dict2, check_len=False):
        if check_len:
            if len(dict1) != len(dict2):
                return False

        for key, value in dict1.items():
            if key not in dict2:
                return False

            if dict1[key] != dict2[key]:
                return False

        return True


class RegisterBankThread(threading.Thread):
    _register_bank = {}
    _register_clusters = {}
    # FOR TESTING
    # register_bank = {4000031: {3: [30000, {1: [0, 0], 2: [0, 0], 3: [0, 0], 4: [0, 0], 9: [21312, 1500491665.951605],
    #                            10: [17315, 1500491665.951605]}]}}

    def __init__(self, rx_queue):  # tx_queue, rx_queue):
        threading.Thread.__init__(self, daemon=True)
        # self.tx_queue = tx_queue  # for bacnet responses
        self.rx_queue = rx_queue  # for bacnet requests and modbus responses

        # FOR TESTING (normally set in self.add_instance:
        # {'type': 'modbus', 'bcnt_inst': self.bcnt_instance, 'mb_func': self.mb_func,
        #  'mb_reg': self.register, 'mb_num_regs': self.num_regs, 'mb_otpt': otpt,
        #  'mb_resp_time': time.time()}
        # self.register_clusters[(4000031, 0)] = [ModbusPollThread(self.rx_queue, 4000031, '10.166.2.132', 10, 3, 1, 10,
        #                                                          1000, 502), 1500491695.951605, 30000]

    def add_instance(self, map_dict):  # , mb_timeout=2000, mb_port=502):
        # mb_func = 3
        # func_key = 'holdingRegisters'
        func_regs = {}
        bcnt_inst = map_dict['deviceInstance']
        if bcnt_inst in self._register_bank:  # bacnet instance already exists!
            return False
        clstr = 0
        mb_ip = map_dict['deviceIP']
        mb_id = map_dict['modbusId']
        mb_port = map_dict['modbusPort']
        val_types = {'holdingRegisters': 3, 'inputRegisters': 4, 'coilBits': 1, 'inputBits': 2}

        for val_type, mb_func in val_types.items():
            if val_type not in map_dict:  # ('holdingRegisters', 'inputRegisters', 'coilBits', 'inputBits'):
                continue
                # if key == 'holdingRegisters':
                #     mb_func = 3
                #     func_key = 'holdingRegisters'
                # elif key == 'inputRegisters':
                #     mb_func = 4
                #     func_key = 'inputRegisters'
                # elif key == 'coilBits':
                #     mb_func = 1
                #     func_key = 'coilBits'
                # elif key == 'inputBits':
                #     mb_func = 2
                #     func_key = 'inputBits'

            mb_polling_time = map_dict[val_type]['pollingTime']
            mb_request_timeout = map_dict[val_type]['requestTimeout']
            mb_grp_cons = True if map_dict[val_type]['groupConsecutive'] == 'yes' else False
            mb_grp_gaps = True if map_dict[val_type]['groupGaps'] == 'yes' else False

            raw_regs = {}
            raw_regs_list = []
            for register in map_dict[val_type]['registers']:
                # don't bother storing points we won't look at
                if register['poll'] == 'no':
                    continue

                start_reg = register['start']
                num_regs = 1

                if register['format'] in one_register_formats:
                    num_regs = 1
                elif register['format'] in two_register_formats:
                    num_regs = 2
                elif register['format'] in three_register_formats:
                    num_regs = 3
                elif register['format'] in four_register_formats:
                    num_regs = 4

                last_reg = start_reg + num_regs - 1
                for ii in range(start_reg, start_reg + num_regs):
                    raw_regs[ii] = [0, 0.0]
                    raw_regs_list.append([ii, start_reg, last_reg])

            # set up dicts for self.register_bank{}
            func_regs[mb_func] = [map_dict[val_type]['pollingTime'], raw_regs]

            raw_regs_list.sort()

            clstr_reg_start = raw_regs_list[0][0]
            num_map_regs = len(raw_regs_list)

            if mb_grp_cons and mb_grp_gaps:  # clusters should span multiple points and registers we won't record
                last_iter_reg = raw_regs_list[0][2]
                for ii in range(num_map_regs):
                    if raw_regs_list[ii][2] - clstr_reg_start > 125 or ii == num_map_regs - 1:
                        # ModbusPollThread(self.rx_queue, 4000031, '10.166.2.132', 10, 3, 1, 10, 1000, 502)
                        mb_poll_thread = ModbusPollThread(self.rx_queue, bcnt_inst, mb_ip, mb_id, mb_func,
                                                          clstr_reg_start, last_iter_reg - clstr_reg_start
                                                          + 1, mb_request_timeout, mb_port)
                        self._register_clusters[(bcnt_inst, clstr)] = [mb_poll_thread, 0.0, mb_polling_time]

                        # print('\nclstr:', clstr)
                        # print('start', clstr_reg_start)
                        # print('regs: ', last_iter_reg - clstr_reg_start + 1)
                        # print('end:', last_iter_reg)

                        clstr += 1
                        # if ii < num_map_regs - 1:
                        clstr_reg_start = raw_regs_list[ii][0]

                    last_iter_reg = raw_regs_list[ii][2]
            elif mb_grp_cons:
                last_iter_reg = raw_regs_list[0][2]
                for ii in range(num_map_regs):
                    if raw_regs_list[ii][0] - raw_regs_list[ii - 1][0] > 1 or ii == num_map_regs - 1 \
                            or raw_regs_list[ii][2] - clstr_reg_start > 124:
                        mb_poll_thread = ModbusPollThread(self.rx_queue, bcnt_inst, mb_ip, mb_id, mb_func,
                                                          clstr_reg_start, last_iter_reg - clstr_reg_start
                                                          + 1, mb_request_timeout, mb_port)
                        self._register_clusters[(bcnt_inst, clstr)] = [mb_poll_thread, 0.0, mb_polling_time]

                        # print('\nclstr:', clstr)
                        # print('start', clstr_reg_start)
                        # print('regs: ', last_iter_reg - clstr_reg_start + 1)
                        # print('end:', last_iter_reg)

                        clstr += 1
                        # if ii < num_map_regs - 1:
                        clstr_reg_start = raw_regs_list[ii][0]

                    last_iter_reg = raw_regs_list[ii][2]
            else:
                clstr_reg_start = raw_regs_list[-1][1]
                for ii in range(num_map_regs):
                    if raw_regs_list[ii][1] != clstr_reg_start:
                        mb_poll_thread = ModbusPollThread(self.rx_queue, bcnt_inst, mb_ip, mb_id, mb_func,
                                                          raw_regs_list[ii][1], raw_regs_list[ii][2] -
                                                          raw_regs_list[ii][1] + 1, mb_request_timeout, mb_port)
                        self._register_clusters[(bcnt_inst, clstr)] = [mb_poll_thread, 0.0, mb_polling_time]

                        clstr += 1
                        clstr_reg_start = raw_regs_list[ii][1]

        self._register_bank[bcnt_inst] = func_regs
        return True

    def run(self):
        for reg_clstr, clstr_val in self._register_clusters.items():
            # if clstr_val[1] < time_at_loop_start:
            #     clstr_val[1] = time_at_loop_start + clstr_val[2] / 1000.0
            clstr_val[0].start()
        while True:
            # time.sleep(5)
            time_at_loop_start = time.time()

            # make all modbus requests
            for reg_clstr, clstr_val in self._register_clusters.items():
                if clstr_val[1] < time_at_loop_start:
                    clstr_val[1] = time_at_loop_start + clstr_val[2] / 1000.0
                    clstr_val[0].run()

            try:
                rx_resp = self.rx_queue.get_nowait()  # no reason to hang here, just wait until next loop

                if rx_resp[1]['type'] == 'bacnet':
                    self._handle_bacnet_request(rx_resp, time_at_loop_start)
                elif rx_resp[1]['type'] == 'modbus':
                    self._handle_modbus_response(rx_resp)
                    # pprint(self.register_bank)
                else:
                    # this should not happen
                    pass

            except Empty:
                pass

    def _handle_bacnet_request(self, rx_resp, time_at_loop_start):
        # {'type': 'bacnet', 'bcnt_inst': dev_instance, 'mb_func': mb_func, 'mb_reg': register,
        #  'mb_num_regs': num_regs, 'mb_frmt': reg_format, 'mb_wo': word_order}
        resp_regs = []
        bcnt_req_inst = rx_resp[1]['bcnt_inst']
        bcnt_req_mb_func = rx_resp[1]['mb_func']
        bcnt_req_reg = rx_resp[1]['mb_reg']
        bcnt_req_num_regs = rx_resp[1]['mb_num_regs']
        bcnt_req_format = rx_resp[1]['mb_frmt']
        bcnt_req_wo = rx_resp[1]['mb_wo']
        earliest_collec_time = time_at_loop_start
        tx_queue = rx_resp[2]
        # rx_resp.pop(2)
        try:
            for ii in range(bcnt_req_num_regs):
                resp_regs.append(self._register_bank[bcnt_req_inst][bcnt_req_mb_func][1][bcnt_req_reg + ii][0])
                earliest_collec_time = min(earliest_collec_time,
                                           self._register_bank[bcnt_req_inst][bcnt_req_mb_func][1][bcnt_req_reg +
                                                                                                   ii][1])

            bcnt_pt_val = self._format_registers_to_point(resp_regs, bcnt_req_format, bcnt_req_wo)
            rx_resp[1]['bcnt_value'] = bcnt_pt_val
            rx_resp[1]['bcnt_valid'] = True

            # check if a long period of time has passed between now and the earliest bit of data found
            if (time_at_loop_start - earliest_collec_time) > \
                    (self._register_bank[bcnt_req_inst][bcnt_req_mb_func][0] * 3 / 1000.0):
                # modbus values from long ago
                rx_resp[1]['bcnt_valid'] = False
        except KeyError:
            # register does not exist in bank
            rx_resp[1]['bcnt_value'] = 0.0
            rx_resp[1]['bcnt_valid'] = False
        finally:
            # don't need TupleSortingOn0 here since rx_resp is already of this type
            tx_queue.put(rx_resp, timeout=0.1)  # not sure about time here

    def _handle_modbus_response(self, rx_resp):
        # {'type': 'modbus', 'bcnt_inst': self.bcnt_instance, 'mb_func': self.mb_func,
        #  'mb_reg': self.register, 'mb_num_regs': self.num_regs, 'mb_otpt': otpt,
        #  'mb_resp_time': time.time()}
        bcnt_inst = rx_resp[1]['bcnt_inst']
        mb_func = rx_resp[1]['mb_func']

        if bcnt_inst not in self._register_bank or mb_func not in self._register_bank[bcnt_inst]:
            # modbus response does not coordinate with any devices in the bank
            return

        mb_reg = rx_resp[1]['mb_reg']
        mb_num_regs = rx_resp[1]['mb_num_regs']
        mb_resp = rx_resp[1]['mb_otpt']
        mb_resp_time = rx_resp[1]['mb_resp_time']

        if mb_resp[0] == 'Err':
            # if there is an error, don't update registers
            pass
        else:
            inst_reg_bank = self._register_bank[bcnt_inst][mb_func][1]
            for reg in range(mb_reg, mb_reg + mb_num_regs):
                if reg in inst_reg_bank:  # only add to reg bank where necessary
                    inst_reg_bank[reg][0] = mb_resp[reg - mb_reg]
                    inst_reg_bank[reg][1] = mb_resp_time
                    # self.register_bank[bcnt_inst][mb_func][1][reg][0] = mb_resp[reg - mb_reg]
                    # self.register_bank[bcnt_inst][mb_func][1][reg][1] = mb_resp_time

        return

    @staticmethod
    def _format_registers_to_point(registers, reg_frmt, reg_wo):
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
                pt_val = bin(reg_0)
            elif reg_frmt == 'hex':
                pt_val = hex(reg_0)
            elif reg_frmt == 'ascii':
                byte_1 = bytes([reg_0 >> 8])
                byte_0 = bytes([reg_0 & 0xff])
                # b1 = bytes([56])
                # b0 = bytes([70])
                pt_val = byte_1.decode('ascii', 'ignore') + byte_0.decode('ascii', 'ignore')
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
        return pt_val


class ModbusPollThread(threading.Thread):
    def __init__(self, tx_queue, bcnt_instance, ip, mb_id, mb_func, register, num_regs, timeout, port):
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

    def run(self):
        if not self.currently_running:
            self.currently_running = True
            print('making modbus request at', time.time())
            # print('ip:   ', self.ip)
            # print('id:   ', self.mb_id)
            # print('func: ', self.mb_func)
            # print('start:', self.register)
            # print('regs: ', self.num_regs)
            otpt = mb_poll(self.ip, self.mb_id, self.register, self.num_regs, func=self.mb_func, mb_to=self.timeout,
                           port=self.port, t='uint16')
            tx_resp = (1, {'type': 'modbus', 'bcnt_inst': self.bcnt_instance, 'mb_func': self.mb_func,
                           'mb_reg': self.register, 'mb_num_regs': self.num_regs, 'mb_otpt': otpt,
                           'mb_resp_time': time.time()})
            self.tx_queue.put(TupleSortingOn0(tx_resp), 0.1)
            if otpt[0] == 'Err':
                print('got modbus error', otpt)
            else:
                print('got modbus response')
            self.currently_running = False
        else:
            print('currently running')


class TupleSortingOn0(tuple):
    def __lt__(self, rhs):
        return self[0] < rhs[0]

    def __gt__(self, rhs):
        return self[0] > rhs[0]

    def __le__(self, rhs):
        return self[0] <= rhs[0]

    def __ge__(self, rhs):
        return self[0] >= rhs[0]
