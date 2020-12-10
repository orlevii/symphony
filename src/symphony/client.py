import multiprocessing as mp
import socket
from datetime import datetime
from io import BytesIO
from time import sleep

import click
import pygame

from .util import TimeUtil


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

        self.sync()

        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            sleep(1)

    def sync(self):
        self.sock.recv(1)
        t1_dt = datetime.utcnow()
        t1_b = TimeUtil.timestamp_to_bytes(t1_dt.timestamp())
        self.sock.send(t1_b)
        self.sock.recv(8)

        t3_dt = datetime.utcnow()
        t3_b = TimeUtil.timestamp_to_bytes(t3_dt.timestamp())
        self.sock.send(t3_b)

        play_time_b = self.sock.recv(8)
        play_time_ts = TimeUtil.timestamp_from_bytes(play_time_b)
        play_time_dt = datetime.fromtimestamp(play_time_ts)

        now = datetime.utcnow()
        sleep_time = (play_time_dt - now).total_seconds()
        sleep(sleep_time)


@click.command()
@click.option('--host', default='127.0.0.1')
@click.option('--port', default=7777)
@click.option('--tracks', default=1)
def cli(tracks, **kwargs):
    if tracks == 1:
        Client(**kwargs).run()
    else:
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
