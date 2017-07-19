from queue import Queue, Empty, Full
import threading
from mbpy.mbpy import mb_poll
import time

# globals
one_register_formats = ('uint16', 'sint16', 'sm1k16', 'sm10k16', 'bin', 'hex', 'ascii')
two_register_formats = ('uint32', 'sint32', 'um1k32', 'sm1k32', 'um10k32', 'sm10k32', 'float')
three_register_formats = ('uint48', 'um1k48', 'sm1k48', 'um10k48', 'sm10k48')
four_register_formats = ('uint64', 'sint64', 'um1k64', 'sm1k64', 'um10k64', 'sm10k64', 'dbl', 'engy')
register_formats = one_register_formats + two_register_formats + three_register_formats + four_register_formats

class RegisterReader:
    def __init__(self, tx_queue, rx_queue):
        self.tx_queue = tx_queue
        self.rx_queue = rx_queue

    def get_register_raw(self, dev_instance, register, word_order, timeout=100.0):
        self.get_register_format(dev_instance, register, 1, 'uint16', 'lsw', timeout=timeout)

    def get_register_format(self, dev_instance, register, num_regs, reg_format, word_order, timeout=100.0):
        # ADD ERROR CHECKING OF VARIABLES!!!
        reg_bank_req = (0, 'bacnet', dev_instance, register, num_regs, reg_format, word_order)
        try:
            self.tx_queue.put(reg_bank_req, timeout=timeout/1000.0)

            try:
                reg_bank_resp = self.rx_queue.get(timeout=timeout/1000.0)
            except Empty:
                return (0.0, False)  # (value, reliability)
            # reg_bank_resp = ('bacnet', dev_instance, register, num_regs, reg_format, word_order, 0.0, False)
            if reg_bank_req[1:] == reg_bank_resp[:6]:
                return (reg_bank_resp[6], reg_bank_resp[7])
            return (0.0, False)  # (value, reliability)
        except Full:
            return (0.0, False)  # (value, reliability)


class RegisterBankThread(threading.Thread):
    # register_bank = {}
    register_clusters = {}
    # FOR TESTING
    register_bank = {4000031:{1:[0, 0], 2:[0, 0], 3:[0, 0], 4:[0, 0], 9:[21312, 1500491665.951605],
                              10:[17315, 1500491665.951605]}}
    # register_clusters = {(4000031, 0):[ModbusPollThread(), 1500491695.951605, 30000]}

    def __init__(self, tx_queue, rx_queue):
        threading.Thread.__init__(self, daemon=True)
        self.tx_queue = tx_queue  # for bacnet responses
        self.rx_queue = rx_queue  # for bacnet requests and modbus responses
        # NEED MORE STUFF FOR SETTING UP REGISTER BANK

        # FOR TESTING:
        self.register_clusters[(4000031, 0)] = [ModbusPollThread(self.rx_queue, 4000031, '10.166.2.132', 10, 3, 1, 10,
                                                                 1000, 502), 1500491695.951605, 30000]

    def add_instance(self, instance_dict):
        pass

    def run(self):
        while True:
            time_at_loop_start = time.time()

            # make all modbus requests
            for reg_clstr, clstr_val in self.register_clusters.items():
                if clstr_val[1] < time_at_loop_start:
                    clstr_val[1] = time_at_loop_start + clstr_val[2] / 1000.0
                    clstr_val[0].start()

            try:
                rx_resp = self.rx_queue.get_nowait()

                if rx_resp[1] == 'bacnet':
                    resp_regs = []
                    bcnt_req_inst = rx_resp[2]
                    bcnt_req_reg = rx_resp[3]
                    bcnt_req_num_regs = rx_resp[4]
                    bcnt_req_format = rx_resp[5]
                    bcnt_req_wo = rx_resp[6]
                    bcnt_req_min_req_time = time_at_loop_start
                    try:
                        for ii in range(bcnt_req_num_regs):
                            resp_regs.append(self.register_bank[bcnt_req_inst][bcnt_req_reg + ii][0])
                            bcnt_req_min_req_time = min(bcnt_req_min_req_time, self.register_bank[bcnt_req_inst][bcnt_req_reg + ii][1])

                        bcnt_pt_val = self.__format_registers_to_point(resp_regs)

                        if time_at_loop_start - bcnt_req_min_req_time >  * 3:
                            # modbus values from long ago
                            pass
                    except KeyError:
                        # register does not exist in bank
                        pass

                elif rx_resp[1] == 'modbus':
                    pass
                else:
                    # this should not happen
                    pass

            except Empty:
                pass

    def __format_registers_to_point(self, registers):
        pass


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

    def run(self):
        otpt = mb_poll(self.ip, self.mb_id, self.register, self.num_regs, func=self.mb_func, mb_to=self.timeout,
                       port=self.port)
        self.tx_queue.put((1, 'modbus', self.bcnt_instance, otpt, time.time()))


