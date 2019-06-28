import socketserver
import struct
import mbpy.mb_poll as mb_poll
import select
import socket
from time import time as _time
from bacpypes.debugging import bacpypes_debugging, ModuleLogger


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


def make_modbus_request_handler(app_dict, mb_timeout=1000, tcp_timeout=5000, mb_translation=True):
    # @bacpypes_debugging
    class KlassModbusRequestHandler(socketserver.BaseRequestHandler):  # , object):
        def __init__(self, *args, **kwargs):
            if _debug: KlassModbusRequestHandler._debug('__init__ mb timeout: %r, tcp timeout: %r',
                                                        mb_timeout, tcp_timeout)

            self.app_dict = app_dict  # don't think this works the way I want since this is a class constructor
            self.mb_timeout = mb_timeout
            self.tcp_timeout = tcp_timeout / 1000.0
            self.mb_translation = mb_translation

            super(KlassModbusRequestHandler, self).__init__(*args, **kwargs)

        def handle(self):
            # available class variables
            #     self.request -
            #     self.client_address -
            #     self.server -

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

                    if _debug: KlassModbusRequestHandler._debug('    - modbus request: virt_id: %s, register: %s at %s',
                                                                virt_id, mb_register, _time())

                    if mb_error != 0:
                        # if error found in request
                        if _debug: KlassModbusRequestHandler._debug('    - modbus request error: %r', mb_error)
                        response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id, mb_func + 128,
                                          mb_error[1]])
                    elif dev_inst != 0 and self.mb_translation and 19999 < mb_register < 40000:
                        # TBD
                        # search for device info, then use that to make direct query of modbus device, modifying for
                        # datatype
                        response = self._convert_req_float(mb_ip, transaction_id, virt_id, slave_id, mb_func,
                                                           mb_register, mb_num_regs)
                    elif dev_inst != 0 and self.mb_translation and 39999 < mb_register < 60000:
                        # search for device info and grab values direct from bacnet objects (limit to one?)
                        response = self._bacnet_request(dev_inst, transaction_id, virt_id, mb_func, mb_register,
                                                        mb_num_regs)
                    else:
                        # straight through request to meter
                        response = self._straight_through_request(mb_ip, transaction_id, virt_id, slave_id, mb_func,
                                                                  mb_register, mb_num_regs)

                    # if _debug: KlassModbusRequestHandler._debug('response to modbus request in process %s: %s',
                    #                                             cur_process, response)
                    self.request.sendall(response)
                else:
                    break

        def find_slave_id(self, virt_id):
            for dev_inst in self.app_dict:
                if dev_inst % 100 == virt_id:
                    if self.app_dict[dev_inst].localDevice.deviceIp == '0.0.0.0':
                        mb_ip = '/dev/serial0'
                    else:
                        mb_ip = self.app_dict[dev_inst].localDevice.deviceIp
                    return dev_inst, mb_ip, self.app_dict[dev_inst].localDevice.modbusId

            # if no matching device is found, assume a serial connection is desired
            return 0, '/dev/serial0', virt_id

        def _convert_req_float(self, mb_ip, transaction_id, virt_id, slave_id, mb_func, mb_register, mb_num_regs):
            # TBD
            mb_error = mb_poll.MB_ERR_DICT[2]
            response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id, mb_func + 128,
                              mb_error[1]])
            return response

        def _bacnet_request(self, dev_inst, transaction_id, virt_id, mb_func, mb_register, mb_num_regs):
            if _debug: KlassModbusRequestHandler._debug('    - bacnet store request: %r, virt_id: %r, func: %r, '
                                                        'register: %r, num_regs: %r', transaction_id,
                                                        virt_id, mb_func, mb_register, mb_num_regs)
            if mb_num_regs == 2:
                for obj_inst in self.app_dict[dev_inst].objectIdentifier:
                    bcnt_pt = self.app_dict[dev_inst].objectIdentifier[obj_inst]

                    if bcnt_pt.objectIdentifier[0] == 'device':
                        continue

                    if bcnt_pt.registerStart == (mb_register - 39999):
                        if _debug: KlassModbusRequestHandler._debug('        - request for %s, %s', dev_inst, obj_inst)

                        if bcnt_pt.reliability == 'noFaultDetected':
                            val = bytearray(struct.pack('>f', bcnt_pt.presentValue))  # > forces big endian

                            if self.app_dict[dev_inst].localDevice.meterRespWordOrder == 'msw':
                                pass  # nothing to do here
                            else:
                                val.extend(val[0:2])
                                val = val[2:]

                            response = bytearray([transaction_id[0], transaction_id[1], 0, 0, 0, 7, virt_id, mb_func,
                                                  4])
                            response.extend(val)

                            if _debug: KlassModbusRequestHandler._debug('    - modbus return success: %r at %s',
                                                                        list(response), _time())
                        else:
                            # bad reliability
                            mb_error = mb_poll.MB_ERR_DICT[4]
                            response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id, mb_func + 128,
                                              mb_error[1]])
                            if _debug: KlassModbusRequestHandler._debug('    - modbus return comm FAILURE: %r at %s',
                                                                        list(response), _time())
                        break
                else:
                    if _debug: KlassModbusRequestHandler._debug('    - bad register request: %s not in library',
                                                                mb_register)
                    # no such register found: mb_register - 49999
                    mb_error = mb_poll.MB_ERR_DICT[2]
                    response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id, mb_func + 128,
                                      mb_error[1]])
            else:
                # wrong number of regs requested
                if _debug: KlassModbusRequestHandler._debug('    - bad number of regs requested (%s), should be 2',
                                                            mb_num_regs)
                mb_error = mb_poll.MB_ERR_DICT[2]
                response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, virt_id, mb_func + 128,
                                  mb_error[1]])

            return response

        def _straight_through_request(self, mb_ip, transaction_id, virt_id, slave_id, mb_func, mb_register,
                                      mb_num_regs):
            if _debug: KlassModbusRequestHandler._debug('    - straighthrough request: %r, slave: %r, func: %r, '
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
                response_list = transaction_id + [0, 0, len_rtn_hi, len_rtn_lo, virt_id, mb_func, len_return - 3]
                response_list.extend(raw_byte_return)
                response = bytes(response_list)
                if _debug: KlassModbusRequestHandler._debug('        - modbus return success %r', response_list[0:9])
            return response
    bacpypes_debugging(KlassModbusRequestHandler)
    return KlassModbusRequestHandler


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


if __name__ == '__main__':
    pass
