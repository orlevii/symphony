import multiprocessing as mp
import os
import socket
import sys
from datetime import datetime, timedelta
from time import sleep

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
            sys.exit(-1)

        print('-----' * 10)
        print('Playing in 15s, syncing clients...')
        play_time = datetime.utcnow() + timedelta(seconds=15)
        print(f'expected play time: {play_time.timestamp()}')

        print(f'clients to sync: {len(self.clients)}')
        for c in self.clients:
            self.sync_client(c, play_time)
            sleep(0.1)
        self.sock.close()

    def receive_connections(self):
        for i, f in enumerate(self.files, 1):
            client, addr = self.sock.accept()
            self.clients.append(client)
            print('Connected by', addr)
            self.handle_client(client, f)
            sleep(0.25)

    def handle_client(self, client: socket.socket, data: bytes):
        client.sendall(b'M')
        length = len(data)
        print(f'sending {length} bytes to client {client.getpeername()}')
        client.sendall(length.to_bytes(4, 'big'))
        client.sendall(data)

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
        c.sendall(b'R')
        c.sendall(TimeUtil.timestamp_to_bytes(play_time.timestamp()))
        while c.recv(1) != b'R':
            pass


@click.command()
@click.option('--host', default='0.0.0.0')
@click.option('--port', default=7777)
@click.option('--midi-path', default='./midi')
def cli(**kwargs):
    p = mp.Process(target=ntp_server, kwargs=kwargs)
    s = Server(**kwargs)
    try:
        p.start()
        s.run()
        print('done')
        sys.exit(0)
    finally:
        p.terminate()
        for c in s.clients:
            c.close()


def ntp_server(host, port, **_):
    from .ntp.server import run
    run(host=host, port=port)


def main():
    cli()


if __name__ == '__main__':
    main()
