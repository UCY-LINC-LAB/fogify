from enum import Enum


class RateUnit(Enum):
    bit = "bit"  # Bits per second
    kbit = "kbit"  # Kilobits per second
    mbit = "mbit"  # Megabits per second
    gbit = "gbit"  # Gigabits per second
    tbit = "tbit"  # Terabits per second
    bps = "bps"  # Bytes per second
    kbps = "kbps"  # Kilobytes per second
    mbps = "mbps"  # Megabytes per second
    gbps = "gbps"  # Gigabytes per second
    tbps = "tbps"  # Terabytes per second

    @classmethod
    def get_values(cls):
        return list(map(lambda c: c.value, cls))
