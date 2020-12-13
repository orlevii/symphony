import os
import socket
import sys
from datetime import datetime
from io import BytesIO

import click
import pygame
from symphony.time_sync.timesyncclient import TimeSyncClient

from time import sleep
from ._socket_wrapper import SocketWrapper
from .util import TimeUtil


class Client:
    def __init__(self, host, port, tracks: int):
        self.host = host
        self.port = port
        self.tracks = tracks
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client = SocketWrapper(sock)
        pygame.mixer.init(size=-8)
        pygame.mixer.music.set_volume(0.8)

    def run(self):
        self.client.sock.connect((self.host, self.port))
        print('Connected!')
        print(f'Requesting {self.tracks} tracks')
        self.client.send_message(self.tracks.to_bytes(4, 'big'))
        midi_data = self.client.recv_message()
        print(f'Got {len(midi_data)} bytes of midi')

        midi_stream = BytesIO(midi_data)
        pygame.mixer.music.load(midi_stream)

        self.client.send_message(b'READY')
        print('READY!')
        print('-----' * 2)

        self.sync()
        self.handle_os()

        try:
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                sleep(1)
        except Exception as e:
            print(e)
            sys.exit(-1)

    def minimize_ping(self):
        attempts = []
        ntp_client = TimeSyncClient(host=self.host,
                                    port=self.port)
        for i in range(10):
            resp = ntp_client.request()
            attempts.append(resp)

        return min(attempts, key=lambda r: r.ping)

    def sync(self):
        resp = self.minimize_ping()
        offset = resp.offset

        print(f'Approx ping: ~{resp.ping * 1000}ms')
        print(f'Clock offset: {offset}')

        play_time_bytes = self.client.recv_message()
        play_time_ts = TimeUtil.timestamp_from_bytes(play_time_bytes)
        self.client.send_message(b'OK')

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

    @staticmethod
    def handle_os():
        if os.name == 'posix':
            sleep(0.31)  # Not sure why it's needed...


@click.command()
@click.option('--host', default='127.0.0.1')
@click.option('--port', default=7777)
@click.option('--tracks', default=1)
def cli(**kwargs):
    Client(**kwargs).run()


def main():
    cli()


if __name__ == '__main__':
    main()
