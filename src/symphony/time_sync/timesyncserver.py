import socket
from datetime import datetime

from .consts import MICRO_SECONDS


class TimeSyncServer:
    """
    UDP Server for time syncing
    """

    def __init__(self, host, port):
        self.host = host,
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))

    def run(self):
        print(f'[INFO] Time Sync Server is running on port {self.port}')
        while True:
            self.handle_request()

    def handle_request(self):
        data, sender = self.sock.recvfrom(1)

        if data != b'S':
            return

        now = int(datetime.utcnow().timestamp() * MICRO_SECONDS)
        now_b = now.to_bytes(8, 'big')

        self.sock.sendto(now_b, sender)
