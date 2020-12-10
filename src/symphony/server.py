import os
import socket
import struct
import threading
from datetime import datetime, timedelta
from time import sleep

import click


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

        print('Playing in 15s, syncing clients...')
        play_time = datetime.utcnow() + timedelta(seconds=15)
        for c in self.clients:
            for _ in range(10):
                now = datetime.utcnow()
                sleep_time = (play_time - now).total_seconds()
                sleep_time_bytes = struct.pack('>f', sleep_time)
                c.send(sleep_time_bytes)
                sleep(0.250)
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
            path = os.path.join('./midi', f_name)
            with open(path, 'rb') as f:
                self.files.append(f.read())


@click.command()
@click.option('--host', default='0.0.0.0')
@click.option('--port', default=7777)
@click.option('--midi-path', default='./midi')
def cli(**kwargs):
    Server(**kwargs).run()
    print('done')


def main():
    cli()


if __name__ == '__main__':
    main()
