import socketserver
import multiprocessing
import mbpy.mb_poll as mb_poll
import select
import socket

from queue import Empty
from time import time as _time

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.task import RecurringTask

_debug = 0
_log = ModuleLogger(globals())


def parse_modbus_request(message):
    mb_error = 0
    transaction_id = [0, 0]
    exp_tcp_length = 0
    virt_id = 1
    # slave_id = 1
    mb_func = 3
    mb_register = 0
    mb_num_regs = 1

    try:
        transaction_id = [message[0], message[1]]
        exp_tcp_length = message[5]
        virt_id = message[6]
        mb_func = message[7]
        mb_register = (message[8] << 8) | message[9]
        mb_num_regs = (message[10] << 8) | message[11]
        # print('tcp_length: ', exp_tcp_length, ', slave_id: ', slave_id, ', mb_func: ', mb_func, ', mb_register: ',
        #       mb_register, ', mb_num_regs: ', mb_num_regs, sep='')
    except IndexError:
        mb_error = mb_poll.MB_ERR_DICT[108]

    tcp_length = len(message)
    if tcp_length < 6:
        mb_error = mb_poll.MB_ERR_DICT[108]
    elif exp_tcp_length != tcp_length - 6:
        mb_error = mb_poll.MB_ERR_DICT[109]

    return mb_error, transaction_id, virt_id, mb_func, mb_register, mb_num_regs



def make_modbus_request_handler(app_dict, mb_timeout=1000, tcp_timeout=5000,
                                mb_translation=True, mb_wo='lsw'):
    # @bacpypes_debugging
    class KlassModbusRequestHandler(socketserver.BaseRequestHandler):  # , object):
        def __init__(self, *args, **kwargs):
            if _debug: KlassModbusRequestHandler._debug('__init__ mb timeout: %r, tcp timeout: %r', mb_timeout,
                                                        tcp_timeout)

            self.app_dict = app_dict  # don't think this works the way I want since this is a class constructor
            # self.mbtcp_to_bcnt_queue = mbtcp_to_bcnt_queue
            # self.bcnt_to_mbtcp_queue = bcnt_to_mbtcp_queue
            self.mb_timeout = mb_timeout
            self.tcp_timeout = tcp_timeout / 1000.0
            self.mb_translation = mb_translation
            self.mb_wo = mb_wo
            # print('init', hex(id(app_dict)))
            # print('init', hex(id(self.app_dict)))
            super(KlassModbusRequestHandler, self).__init__(*args, **kwargs)

        def handle(self):
            # available class variables
            #     self.request -
            #     self.client_address -
            #     self.server -

            # cur_process = multiprocessing.current_process()
            while True:
                if self.tcp_timeout == 0:  # if tcp_timeout is 0, then run until client closes
                    select_inputs = select.select([self.request], [], [])[0]
                else:
                    select_inputs = select.select([self.request], [], [], self.tcp_timeout)[0]

                if select_inputs:
                    # data = None
                    try:
                        data = self.request.recv(1024)
                    except socket.timeout:
                        if _debug: KlassModbusRequestHandler._debug('    - modbus socket timeout')
                        break
                    except socket.error:
                        if _debug: KlassModbusRequestHandler._debug('    - modbus socket error')
                        break

                    # if _debug: KlassModbusRequestHandler._debug('incoming modbus request in process %s: %s',
                    #                                             cur_process, data)
                    if not data:  # if socket closes, recv() returns ''
                        if _debug: KlassModbusRequestHandler._debug('    - modbus socket closed by other')
                        break

                    mb_error, transaction_id, virt_id, mb_func, mb_register, mb_num_regs = parse_modbus_request(data)
                    dev_inst, mb_ip, slave_id = self.find_slave_id(virt_id)

                    if mb_error != 0:
                        # if error found in request
                        if _debug: KlassModbusRequestHandler._debug('    - modbus request error: %r', mb_error)
                        response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id, mb_func + 128,
                                          mb_error[1]])
                    elif dev_inst != 0 and self.mb_translation and 39999 < mb_register < 50000:
                        # TBD
                        # search for device info, then use that to make direct query of modbus device, modifying for
                        # datatype
                        mb_error = mb_poll.MB_ERR_DICT[2]
                        response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id, mb_func + 128,
                                          mb_error[1]])
                    elif dev_inst != 0 and self.mb_translation and 49999 < mb_register < 60000:
                        # TBD
                        # search for device info and grab values direct from bacnet objects (limit to one?)
                        if mb_num_regs == 2:
                            for pt_id in self.app_dict[dev_inst].objectIdentifier:
                                strd_pt = self.app_dict[dev_inst].objectIdentifier[pt_id]

                                if strd_pt.objectIdentifier[0] == 'device':
                                    continue
                                if strd_pt.registerStart == (mb_register - 49999):
                                    bn_req = {'dev_inst': dev_inst, 'obj_inst': pt_id}
                                    self.server.mbtcp_to_bcnt_queue.put(bn_req, timeout=0.1)

                                    print('added to queue', dev_inst, pt_id)
                                    start_time = _time()
                                    bn_resp = None
                                    while (_time() - start_time) < (self.mb_timeout / 1000):
                                        try:
                                            bn_resp = self.server.bcnt_to_mbtcp_queue.get_nowait()
                                        except Empty:
                                            continue

                                        if (bn_resp['dev_inst'], bn_resp['obj_inst']) == \
                                                (bn_req['dev_inst'], bn_req['obj_inst']):
                                            print('bn_resp', bn_resp)
                                            break
                                        else:
                                            self.server.bcnt_to_mbtcp_queue.put(bn_resp, timeout=0.1)
                                            bn_resp = None
                                            print('wrong BACnet response found!')

                                    if bn_resp is None:
                                        print('no bacnet response found', self.server.mbtcp_to_bcnt_queue.empty())
                                        mb_error = mb_poll.MB_ERR_DICT[11]
                                        response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id,
                                                          mb_func + 128, mb_error[1]])
                                    elif bn_resp['reliability'] == 'noFaultDetected':
                                        print('good find')
                                        mb_error = mb_poll.MB_ERR_DICT[3]
                                        response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id,
                                                          mb_func + 128, mb_error[1]])
                                    else:
                                        print('reliability problem', hex(id(strd_pt.reliability)),
                                              hex(id(strd_pt._values)),
                                              bn_resp['reliability'],
                                              strd_pt._values['reliability'],
                                              hex(id(strd_pt._values['reliability'])),
                                              hex(id(strd_pt._properties['reliability'])))
                                        mb_error = mb_poll.MB_ERR_DICT[2]
                                        response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id,
                                                          mb_func + 128, mb_error[1]])
                                    break
                            else:
                                print('no such register found', mb_register - 49999)
                                mb_error = mb_poll.MB_ERR_DICT[2]
                                response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id,
                                                  mb_func + 128, mb_error[1]])
                        else:
                            print('wrong number of regs requested')
                            mb_error = mb_poll.MB_ERR_DICT[2]
                            response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id, mb_func + 128,
                                              mb_error[1]])
                    else:
                        # assume serial for now!
                        if _debug: KlassModbusRequestHandler._debug('    - modbus request id: %r, slave: %r, func: %r, '
                                                                    'register: %r, num_regs: %r', transaction_id,
                                                                    slave_id, mb_func, mb_register, mb_num_regs)
                        raw_byte_return = mb_poll.modbus_poller(mb_ip, slave_id, mb_register, mb_num_regs,
                                                                data_type='uint16', zero_based=True, mb_func=mb_func,
                                                                b_raw_bytes=True, mb_timeout=self.mb_timeout)
                        if raw_byte_return[0] == 'Err':
                            mb_error = raw_byte_return
                            response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id, mb_func + 128,
                                              mb_error[1]])
                            if _debug: KlassModbusRequestHandler._debug('        - modbus return error trans id %r: %r',
                                                                        transaction_id, mb_error)
                        else:
                            len_return = len(raw_byte_return) + 3
                            len_rtn_hi = (len_return >> 8) & 0xff
                            len_rtn_lo = len_return & 0xff
                            response_list = transaction_id + [0, 0, len_rtn_hi, len_rtn_lo, virt_id, mb_func,
                                                              len_return - 3]
                            response_list.extend(raw_byte_return)
                            response = bytes(response_list)
                            if _debug: KlassModbusRequestHandler._debug('        - modbus return trans id %r: %r',
                                                                        transaction_id, response_list)
                    # response = bytes([0, 0, 0, 0, 0, 7, 1, 3, 4, 1, 2, 3, 4])
                    # if _debug: KlassModbusRequestHandler._debug('response to modbus request in process %s: %s',
                    #                                             cur_process, response)
                    self.request.sendall(response)
                else:
                    break

        def find_slave_id(self, virt_id):
            for dev_inst in self.app_dict:
                # print(dev_inst, virt_id, dev_inst % 100, type(self.app_dict[dev_inst]))
                if dev_inst % 100 == virt_id:
                    # print(dev_inst, 'properties:')
                    # print(self.app_dict[dev_inst].localDevice.deviceIp, self.app_dict[dev_inst].localDevice.modbusId)
                    # for key, val in self.app_dict[dev_inst].objectName['heat_flow_steam']._values.items():
                    #     print(key, val, self.app_dict[dev_inst].objectName['heat_flow_steam'].__getattr__(key))
                    #     # print('\t', key, ':', val)
                    #     if val.objectIdentifier[0] == 'device':
                    #         continue
                    #     print('\t', key)
                    #     print('\t\t', val.registerStart, val.reliability, val.presentValue)
                    #     # for key2, val2 in val.__dict__.items():
                    #     #     print('\t\t', key2, ':', val2)
                    if self.app_dict[dev_inst].localDevice.deviceIp == '0.0.0.0':
                        mb_ip = '/dev/serial0'
                    else:
                        mb_ip = self.app_dict[dev_inst].localDevice.deviceIp
                    return dev_inst, mb_ip, self.app_dict[dev_inst].localDevice.modbusId

            # if no matching device is found, assume a serial connection is desired
            return 0, '/dev/serial0', virt_id


    bacpypes_debugging(KlassModbusRequestHandler)
    return KlassModbusRequestHandler


@bacpypes_debugging
class HandleModbusBACnetRequests(RecurringTask):
    def __init__(self, mbtcp_to_bcnt_queue, bcnt_to_mbtcp_queue, app_dict, interval, max_run_time=50):
        if _debug: HandleModbusBACnetRequests._debug('init')
        RecurringTask.__init__(self, interval)

        self.mbtcp_to_bcnt_queue = mbtcp_to_bcnt_queue
        self.bcnt_to_mbtcp_queue = bcnt_to_mbtcp_queue
        self.app_dict = app_dict
        self.max_run_time = max_run_time / 1000  # set in s to coincide with interval

        # install it
        self.install_task()

    def process_task(self):
        start_time = _time()
        # if _debug: HandleModbusBACnetRequests._debug('start recurring task')

        # while (not self.bcnt_to_mbtcp_queue.empty()) and (_time() - start_time < self.max_run_time):
        #     # check timestamps and permanently remove old requests
        #     pass

        while (not self.mbtcp_to_bcnt_queue.empty()) and (_time() - start_time < self.max_run_time):
            # if not self.bank_to_bcnt_queue.empty():
            if _debug: HandleModbusBACnetRequests._debug('\tqueue not empty')

            try:
                bn_req = self.mbtcp_to_bcnt_queue.get_nowait()
                if _debug: HandleModbusBACnetRequests._debug('\tgot bacnet update')
            except Empty:
                if _debug: HandleModbusBACnetRequests._debug('\tno bacnet update')
                break

            dev_inst = bn_req['dev_inst']
            obj_inst = bn_req['obj_inst']

            if _debug: HandleModbusBACnetRequests._debug('\tdev_inst: %s, %s', dev_inst, obj_inst)

            bn_req['reliability'] = self.app_dict[dev_inst].objectIdentifier[obj_inst].reliability
            bn_req['presentValue'] = self.app_dict[dev_inst].objectIdentifier[obj_inst].presentValue
            bn_req['q_timestamp'] = _time()

            if _debug: HandleModbusBACnetRequests._debug('\t\tvals: %s, %s, %s', bn_req['presentValue'],
                                                         bn_req['reliability'], bn_req['q_timestamp'])

            self.bcnt_to_mbtcp_queue.put(bn_req, timeout=0.1)

        # if _debug: HandleModbusBACnetRequests._debug('end recurring task')


class MBTCPServer(socketserver.TCPServer):
    def __init__(self, mbtcp_to_bcnt_queue, bcnt_to_mbtcp_queue, server_address, RequestHandlerClass,
                 bind_and_activate=True):
        self.mbtcp_to_bcnt_queue = mbtcp_to_bcnt_queue
        self.bcnt_to_mbtcp_queue = bcnt_to_mbtcp_queue
        socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate=bind_and_activate)

class ForkedTCPServer(socketserver.ForkingMixIn, MBTCPServer):
    pass


# class ForkedTCPServer(socketserver.ForkingMixIn, socketserver.TCPServer):
#     pass


# class ForkedTCPServer(socketserver.ForkingMixIn, socketserver.TCPServer):
#     def __init__(self, app_dict, server_address, RequestHandlerClass, bind_and_activate=True):
#         socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate=bind_and_activate)
#         self.app_dict = app_dict
#
#     def finish_request(self, request, client_address):
#         """Finish one request by instantiating RequestHandlerClass."""
#         # print(self.test_var)
#         self.RequestHandlerClass(self.app_dict, request, client_address, self)


# def client(ip, port, message):
#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     sock.connect((ip, port))
#     try:
#         sock.sendall(bytes(message))
#         response = sock.recv(1024)
#         print('recieved', response)
#     finally:
#         sock.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('ip', type=str, help='ip of local machine')
    parser.add_argument('port', type=int, help='socket port')
    parser.add_argument('-f', '--fork', action='store_true', help='Create different process instead of different '
                                                                  'thread.')
    args = parser.parse_args()

    # HOST, PORT = 'localhost', 502
    # HOST, PORT = '130.91.139.94', 502
    HOST = args.ip
    PORT = args.port

    socketserver.TCPServer.allow_reuse_address = True

    ModbusRequestHandler = make_modbus_request_handler(mb_timeout=1000)
    modbus_fork_server = ForkedTCPServer((HOST, PORT), ModbusRequestHandler)
    ip, port = modbus_fork_server.server_address

    server_fork = multiprocessing.Process(target=modbus_fork_server.serve_forever)
    server_fork.daemon = True
    server_fork.start()
    # server_fork.join(timeout=1)

    print('server loop running in process:', server_fork.name)

    # client(ip, port, [0, 0, 0, 0, 0, 6, 15, 3, 0, 0, 0, 20])

    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass

    modbus_fork_server.socket.close()
