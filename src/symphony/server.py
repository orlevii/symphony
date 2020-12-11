import multiprocessing as mp
import os
import socket
import sys
from datetime import datetime, timedelta

import click

from ._socket_wrapper import SocketWrapper
from .util import TimeUtil


class Server:
    def __init__(self, host, port, midi_path, sync_time):
        self.host = host
        self.port = port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, port))
        self.server = SocketWrapper(sock)
        self.midi_path = midi_path
        self.clients = []
        self.files = {}
        self.ready_count = 0
        self.sync_time = sync_time

    def run(self):
        self.load_files()
        self.server.sock.listen()
        print(f'Server listening on: {self.host}:{self.port}')
        self.receive_connections()
        if self.ready_count != len(self.files):
            print('Something is wrong!')
            sys.exit(-1)

        print('-----' * 10)
        print(f'Playing in {self.sync_time}s, syncing clients...')
        play_time = datetime.utcnow() + timedelta(seconds=self.sync_time)
        print(f'expected play time: {play_time.timestamp()}')

        print(f'clients to sync: {len(self.clients)}')
        for c in self.clients:
            self.sync_client(c, play_time)
        self.server.close()

    def receive_connections(self):
        for f_name, data in self.files.items():
            client_sock, addr = self.server.sock.accept()
            client = SocketWrapper(client_sock)
            self.clients.append(client)
            print('Connected by', addr)
            self.handle_client(client, f_name, data)

    def handle_client(self, client: SocketWrapper, file_name: str, data: bytes):
        client.send_message(file_name.encode('utf-8'))
        client.send_message(data)
        ready = client.recv_message()
        if ready == b'READY':
            print(f'Client {client.sock.getpeername()} is ready')
            self.ready_count += 1

    def load_files(self):
        print(f'Searching for midi files in {self.midi_path}')
        file_names = [f for f in os.listdir(self.midi_path) if f.endswith('.mid')]
        print(f'Loading {len(file_names)} midi files...')
        for f_name in file_names:
            path = os.path.join(self.midi_path, f_name)
            with open(path, 'rb') as f:
                self.files[f_name] = f.read()

    @staticmethod
    def sync_client(c: SocketWrapper, play_time: datetime):
        pn = c.sock.getpeername()
        peer_name = f'{pn[0]}:{pn[1]}'

        play_time_bytes = TimeUtil.timestamp_to_bytes(play_time.timestamp())
        c.send_message(play_time_bytes)

        print(f'Syncing client {peer_name}. Waiting..')
        msg = c.recv_message()
        if msg != b'OK':
            print(f'client sent {msg}. ???')
            sys.exit(-1)

        print(f'Done syncing client {peer_name}')


@click.command()
@click.option('--host', default='0.0.0.0')
@click.option('--port', default=7777)
@click.option('--midi-path', default='./midi')
@click.option('--sync-time', default=5)
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
