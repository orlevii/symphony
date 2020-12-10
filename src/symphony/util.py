MICRO_SECOND = 10 ** 6


class TimeUtil:
    @staticmethod
    def timestamp_from_bytes(data: bytes) -> int:
        return int.from_bytes(data, 'big') / MICRO_SECOND

    @staticmethod
    def timestamp_to_bytes(ts: float) -> bytes:
        ts = int(ts * MICRO_SECOND)
        return ts.to_bytes(8, 'big')
