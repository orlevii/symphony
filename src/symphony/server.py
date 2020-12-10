import os
import socket
import threading
from datetime import datetime, timedelta

import click

from .util import TimeUtil


class Server:
    def __init__(self, host, port, midi_path):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.midi_path = midi_path
        self.clients = []
        self.files = []
        self.ready_count = 0

    def run(self):
        self.load_files()
        self.sock.listen()
        print(f'Server listening on: {self.host}:{self.port}')
        self.receive_connections()
        if self.ready_count != len(self.files):
            print('Something is wrong!')

        print('-----' * 10)
        print('Playing in 10s, syncing clients...')
        play_time = datetime.utcnow() + timedelta(seconds=10)
        print(f'expected play time: {play_time.timestamp()}')
        for c in self.clients:
            self.sync_client(c, play_time)
            print('-----' * 10)
        self.sock.close()

    def receive_connections(self):
        for i, f in enumerate(self.files, 1):
            client, addr = self.sock.accept()
            self.clients.append(client)
            print('Connected by', addr)
            threading.Thread(target=self.handle_client,
                             args=[client, f]).run()

    def handle_client(self, client: socket.socket, data: bytes):
        length = len(data)
        print(f'sending {length} bytes to client {client.getpeername()}')
        client.send(length.to_bytes(4, 'big'))
        client.send(data)

        ready = client.recv(1)
        if ready == b'R':
            print(f'Client {client.getpeername()} is ready')
            self.ready_count += 1

    def load_files(self):
        print(f'Searching for midi files in {self.midi_path}')
        file_names = [f for f in os.listdir(self.midi_path) if f.endswith('.mid')]
        print(f'Loading {len(file_names)} midi files...')
        for f_name in file_names:
            path = os.path.join(self.midi_path, f_name)
            with open(path, 'rb') as f:
                self.files.append(f.read())

    @staticmethod
    def sync_client(c: socket.socket, play_time: datetime):
        ip = c.getpeername()[0]
        fis = []
        for i in range(10):
            c.send(b'S')
            t0 = TimeUtil.timestamp_from_bytes(c.recv(8))
            t1 = datetime.utcnow().timestamp()
            t2 = datetime.utcnow().timestamp()
            c.send(TimeUtil.timestamp_to_bytes(t2))
            t3 = TimeUtil.timestamp_from_bytes(c.recv(8))

            fi = ((t1 - t0) + (t2 - t3)) / 2
            fis.append(fi)
            round_trip_delay = (t3 - t0) - (t2 - t1)
            # print(f'[{ip}] - round trip delay: {round_trip_delay}')
            print(f'[{ip}] - clock time diff: {fi * 1000}ms')

        c.send(b'R')
        fi = min(fis, key=lambda f: abs(f))
        print(f'[{ip}] - MIN clock time diff: {fi * 1000}ms')
        play_time = play_time + timedelta(seconds=-fi)
        c.send(TimeUtil.timestamp_to_bytes(play_time.timestamp()))


@click.command()
@click.option('--host', default='0.0.0.0')
@click.option('--port', default=7777)
@click.option('--midi-path', default='./midi')
def cli(**kwargs):
    s = Server(**kwargs)
    try:
        s.run()
        print('done')
    finally:
        for c in s.clients:
            c.close()


def main():
    cli()


if __name__ == '__main__':
    main()
