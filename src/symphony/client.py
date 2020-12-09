import multiprocessing as mp
import socket
from io import BytesIO
from time import sleep

import click
import pygame


class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pygame.mixer.init()
        pygame.mixer.music.set_volume(0.8)

    def run(self):
        self.sock.connect((self.host, self.port))
        print('connected')
        payload_size_bytes = self.sock.recv(4)
        payload_size = int.from_bytes(payload_size_bytes, 'big')
        midi_data = self.sock.recv(payload_size)
        print(f'Got {len(midi_data)} bytes')

        midi_stream = BytesIO(midi_data)
        pygame.mixer.music.load(midi_stream)

        self.sock.send(b'R')
        print('READY!')

        self.sock.recv(1)

        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            sleep(1)


@click.command()
@click.option('--host', default='127.0.0.1')
@click.option('--port', default=7777)
@click.option('--tracks', default=1)
def cli(tracks, **kwargs):
    ps = []
    for _ in range(tracks):
        p = mp.Process(target=lambda: Client(**kwargs).run())
        p.start()
        ps.append(p)

    for p in ps:
        p.join()


def main():
    cli()


if __name__ == '__main__':
    main()
