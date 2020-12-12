import socket
from datetime import datetime

from .consts import MICRO_SECONDS


class TimeSyncResponse:
    def __init__(self, offset, ping):
        self.offset = offset
        self.ping = ping


class TimeSyncClient:
    """
    UDP Client for time syncing
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1)

    def request(self):
        try:
            t0 = datetime.utcnow().timestamp()
            self.sock.sendto(b'S', (self.host, self.port))

            sender = None
            data = None
            while sender != self.host:
                data, sender = self.sock.recvfrom(8)
                sender = sender[0]

            t3 = datetime.utcnow().timestamp()
            t1 = t2 = int.from_bytes(data, 'big') / MICRO_SECONDS

            offset = ((t1 - t0) + (t2 - t3)) / 2

            return TimeSyncResponse(offset=offset,
                                    ping=t3 - t0)

        except socket.timeout:
            raise TimeoutError(f'Request timed out, no answer from {self.host}:{self.port}')
