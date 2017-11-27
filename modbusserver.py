import threading
import socketserver
import socket
import multiprocessing
import mbpy.mb_poll as mb_poll


def parse_modbus_request(message):
    mb_error = 0
    transaction_id = [0, 0]
    exp_tcp_length = 0
    slave_id = 1
    mb_func = 3
    mb_register = 0
    mb_num_regs = 1

    try:
        transaction_id = [message[0], message[1]]
        exp_tcp_length = message[5]
        slave_id = message[6]
        mb_func = message[7]
        mb_register = (message[8] << 8) | message[9]
        mb_num_regs = (message[10] << 8) | message[11]
        # print('tcp_length: ', exp_tcp_length, ', slave_id: ', slave_id, ', mb_func: ', mb_func, ', mb_register: ',
        #       mb_register, ', mb_num_regs: ', mb_num_regs, sep='')
    except IndexError:
        mb_error = mb_poll.mb_err_dict[108]

    tcp_length = len(message)
    if tcp_length < 6:
        mb_error = mb_poll.mb_err_dict[108]
    elif exp_tcp_length != tcp_length - 6:
        mb_error = mb_poll.mb_err_dict[109]

    return mb_error, transaction_id, slave_id, mb_func, mb_register, mb_num_regs


class ThreadedModbusRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        cur_thread = threading.current_thread()
        cur_process = multiprocessing.current_process()
        print('in server.handle, process: ', cur_process, ', thread: ', cur_thread, sep='')

        data = self.request.recv(1024)

        print('\t', data)

        mb_error, transaction_id, slave_id, mb_func, mb_register, mb_num_regs = parse_modbus_request(data)
        if mb_error != 0:
            response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, slave_id, mb_func + 128, mb_error[1]])
        elif mb_register > 39999 and mb_register < 50000:
            # search for device info, then use that to make direct query of modbus device, modifying for datatype
            mb_error = mb_poll.mb_err_dict[2]
            response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, slave_id, mb_func + 128, mb_error[1]])
        elif mb_register > 49999 and mb_register < 60000:
            # search for device info and grab values direct from bacnet objects (limit to one?)
            mb_error = mb_poll.mb_err_dict[2]
            response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, slave_id, mb_func + 128, mb_error[1]])
        else:
            # assume serial for now!
            raw_byte_return = mb_poll.mb_poll('/dev/serial0', slave_id, mb_register, mb_num_regs, data_type='uint16',
                                              zero_based=True, mb_func=mb_func, b_raw_bytes=True, mb_timeout=1000)
            if raw_byte_return[0] == 'Err':
                mb_error = raw_byte_return
                response = bytes(
                    [transaction_id[0], transaction_id[1], 0, 0, 0, 3, slave_id, mb_func + 128, mb_error[1]])
            else:
                len_return = len(raw_byte_return) + 3
                len_rtn_hi = (len_return >> 8) & 0xff
                len_rtn_lo = len_return & 0xff
                response_list = transaction_id + [0, 0, len_rtn_hi, len_rtn_lo, slave_id, mb_func, len_return - 3]
                response_list.extend(raw_byte_return)
                response = bytes(response_list)

        # response = bytes([0, 0, 0, 0, 0, 7, 1, 3, 4, 1, 2, 3, 4])
        print('\t', cur_process, cur_thread, response)
        self.request.sendall(response)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class ForkedTCPServer(socketserver.ForkingMixIn, socketserver.TCPServer):
    pass


def client(ip, port, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    try:
        sock.sendall(bytes(message))
        response = sock.recv(1024)
        print('recieved', response)
    finally:
        sock.close()


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

    if not args.fork:
        modbus_server = ThreadedTCPServer((HOST, PORT), ThreadedModbusRequestHandler)
        ip, port = modbus_server.server_address

        server_thread = threading.Thread(target=modbus_server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        print('server loop running in thread:', server_thread.name)
    else:
        modbus_fork_server = ForkedTCPServer((HOST, PORT), ThreadedModbusRequestHandler)
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

    if not args.fork:
        modbus_server.shutdown()
        modbus_server.server_close()
    else:
        # modbus_fork_server.shutdown()
        # modbus_fork_server.server_close()
        modbus_fork_server.socket.close()
