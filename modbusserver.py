import threading
import socketserver
import socket
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
        mb_register = (message[8] << 8) & message[9]
        mb_num_regs = (message[10] << 8) & message[11]
    except IndexError:
        pass

    tcp_length = len(message)
    if tcp_length < 6:
        mb_error = mb_poll.mb_err_dict[108]
    elif exp_tcp_length != tcp_length - 6:
        mb_error = mb_poll.mb_err_dict[109]

    return mb_error, transaction_id, slave_id, mb_func, mb_register, mb_num_regs


class ThreadedModbusRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        cur_thread = threading.current_thread()
        print('in server.handle, thread:', cur_thread)

        data = self.request.recv(1024)

        mb_error, transaction_id, slave_id, mb_func, mb_register, mb_num_regs = parse_modbus_request(data)
        if mb_error != 0:
            response = bytes([transaction_id[0], transaction_id[1], 0, 0, 0, 3, slave_id, mb_func + 128, mb_error[1]])
        else:
            pass
        # response = bytes([0, 0, 0, 0, 0, 7, 1, 3, 4, 1, 2, 3, 4])
        self.request.sendall(response)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
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
    HOST, PORT = 'localhost', 502

    modbus_server = ThreadedTCPServer((HOST, PORT), ThreadedModbusRequestHandler)
    ip, port = modbus_server.server_address

    server_thread = threading.Thread(target=modbus_server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    print('server loop running in thread:', server_thread.name)

    client(ip, port, [0, 0, 0, 0, 0, 6, 1, 3, 0, 0, 0, 2])

    modbus_server.shutdown()
    modbus_server.server_close()
