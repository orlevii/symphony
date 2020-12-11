from socket import socket


class SocketWrapper:
    BYTEORDER = 'big'

    def __init__(self, sock: socket):
        self.sock = sock

    def send_message(self, data: bytes):
        data_size = len(data)
        data_size_b = data_size.to_bytes(4, self.BYTEORDER)
        self.sock.sendall(data_size_b)
        self.sock.sendall(data)

    def recv_message(self):
        data_size_b = self.__recv(4)
        data_size = int.from_bytes(data_size_b, self.BYTEORDER)
        return self.__recv(data_size)

    def close(self):
        return self.sock.close()

    def __recv(self, size):
        data = b''
        while len(data) < size:
            data += self.sock.recv(size - len(data))

        assert len(data) == size
        return data
