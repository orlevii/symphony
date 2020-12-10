import multiprocessing as mp
import socket
import sys
from datetime import datetime
from io import BytesIO
from time import sleep

import click
import ntplib
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
        ntp_client = ntplib.NTPClient()
        resp = ntp_client.request(host=self.host,
                                  port=self.port,
                                  version=3)
        offset = resp.offset
        print(f'Clock offset: {offset}')

        self.sock.recv(1)
        play_time_bytes = self.sock.recv(8)
        play_time_ts = TimeUtil.timestamp_from_bytes(play_time_bytes)

        expected_play_time = play_time_ts - offset
        print(f'Expected play time: {expected_play_time}')

        now = datetime.utcnow()
        print(f'now: {now.timestamp()}')
        sleep_time = expected_play_time - now.timestamp()
        print(f'sleeping for {sleep_time}seconds')
        if sleep_time <= 0:
            print('????')
            sys.exit(-1)
        else:
            sleep(sleep_time)


@click.command()
@click.option('--host', default='127.0.0.1')
@click.option('--port', default=7777)
@click.option('--tracks', default=1)
def cli(tracks, **kwargs):
    if tracks == 1:
        c(kwargs)
    else:
        ps = []
        for _ in range(tracks):
            p = mp.Process(target=c,
                           args=(kwargs,))
            p.start()
            ps.append(p)

        for p in ps:
            p.join()


def c(kwargs):
    Client(**kwargs).run()


def main():
    cli()


if __name__ == '__main__':
    main()
