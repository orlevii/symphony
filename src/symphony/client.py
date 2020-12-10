import multiprocessing as mp
import socket
import struct
from datetime import datetime
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

        self.sync()

        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            sleep(1)

    def sync(self):
        times = []
        sleep_times_bytes = []

        for i in range(10):
            before = datetime.utcnow()
            sleep_times_bytes.append(self.sock.recv(4))
            after = datetime.utcnow()
            times.append((after - before).total_seconds())

        sleep_times = [struct.unpack('>f', t)[0] for t in sleep_times_bytes]
        last_sleep_time = sleep_times[-1]

        diff_times = []
        for i in range(len(sleep_times) - 1):
            diff_times.append(sleep_times[i] - sleep_times[i + 1])

        print(diff_times)

        total_sleep_time = last_sleep_time - diff_times[-1]

        print(f'waiting {total_sleep_time} seconds to start playing')
        sleep(total_sleep_time)


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
