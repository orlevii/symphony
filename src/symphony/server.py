import multiprocessing as mp
import os
import socket
import sys
from datetime import datetime, timedelta
from io import BytesIO
from random import random
from typing import List

import click
import python3_midi as midi

from ._socket_wrapper import SocketWrapper
from .util import TimeUtil


class MidiFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self.data = data
        self.midi_file = midi.read_midifile(BytesIO(data))
        self.is_handled = False


class Server:
    def __init__(self, host, port, midi_path, sync_time, randomize):
        self.host = host
        self.port = port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind((host, port))
        self.server = SocketWrapper(sock)
        self.midi_path = midi_path
        self.clients = []
        self.files: List[MidiFile] = []
        self.sync_time = sync_time
        self.randomize = randomize

    def run(self):
        self.load_files()
        self.server.sock.listen()
        print(f'Server listening on: {self.host}:{self.port}')
        self.receive_connections()

        print('-----' * 10)
        print(f'Playing in {self.sync_time}s, syncing clients...')
        play_time = datetime.utcnow() + timedelta(seconds=self.sync_time)
        print(f'Expected play time: {play_time.timestamp()}')

        print(f'Clients to sync: {len(self.clients)}')
        for c in self.clients:
            print('-----' * 5)
            self.sync_client(c, play_time)
        self.server.close()

    def receive_connections(self):
        to_handle = [f for f in self.files if not f.is_handled]
        if self.randomize:
            to_handle.sort(key=lambda _: random())

        while any(to_handle):
            print(f'[INFO] - {len(to_handle)} tracks are left!')
            client_sock, addr = self.server.sock.accept()
            client = SocketWrapper(client_sock)
            self.clients.append(client)
            self.handle_client(client, to_handle)
            to_handle = [f for f in self.files if not f.is_handled]

    def handle_client(self, client: SocketWrapper, to_handle: List[MidiFile]):
        peer_name = self.__get_peer_name(client)
        print(f'[{peer_name}] - Connected')
        num_of_tracks = int.from_bytes(client.recv_message(), 'big')
        print(f'[{peer_name}] - Requesting {num_of_tracks} tracks')

        to_combine = to_handle[:num_of_tracks]
        midi_payload = self.combine_midi_files(to_combine)
        client.send_message(midi_payload)

        ready = client.recv_message()
        if ready == b'READY':
            print(f'[{peer_name}] - Client is ready')
        else:
            print('????')

    def load_files(self):
        print(f'Searching for midi files in {self.midi_path}')
        file_names = [f for f in os.listdir(self.midi_path) if f.endswith('.mid')]
        print(f'Loading {len(file_names)} midi files...')
        for f_name in file_names:
            path = os.path.join(self.midi_path, f_name)
            with open(path, 'rb') as f:
                try:
                    self.files.append(MidiFile(name=f_name,
                                               data=f.read()))
                except Exception:
                    raise TypeError(f'Invalid midi file {path}.')

    @classmethod
    def sync_client(cls, c: SocketWrapper, play_time: datetime):
        peer_name = cls.__get_peer_name(c)

        play_time_bytes = TimeUtil.timestamp_to_bytes(play_time.timestamp())
        c.send_message(play_time_bytes)

        print(f'[{peer_name}] - Syncing...')
        msg = c.recv_message()
        if msg != b'OK':
            print(f'[{peer_name}] - ???? - Invalid ack - {msg}.')
            sys.exit(-1)

        print(f'[{peer_name}] - Done!')

    @staticmethod
    def __get_peer_name(s: SocketWrapper):
        pn = s.sock.getpeername()
        return f'{pn[0]}:{pn[1]}'

    @staticmethod
    def combine_midi_files(to_combine: List[MidiFile]) -> bytes:
        first = to_combine[0]
        pattern = midi.read_midifile(BytesIO(first.data))
        first.is_handled = True

        for file in to_combine[1:]:
            for track in file.midi_file:
                pattern.append(track)
            file.is_handled = True

        res = BytesIO()
        midi.write_midifile(res, pattern)
        return res.getvalue()


@click.command()
@click.option('--host', default='0.0.0.0')
@click.option('--port', default=7777)
@click.option('--midi-path', default='./midi')
@click.option('--sync-time', default=5)
@click.option('--randomize', is_flag=True)
def cli(**kwargs):
    p = mp.Process(target=time_sync_server, kwargs=kwargs)
    s = Server(**kwargs)
    try:
        p.start()
        s.run()
        print('----DONE!----')
        sys.exit(0)
    finally:
        p.terminate()
        for c in s.clients:
            c.close()


def time_sync_server(host, port, **_):
    from .time_sync.timesyncserver import TimeSyncServer
    TimeSyncServer(host=host, port=port).run()


def main():
    cli()


if __name__ == '__main__':
    main()
