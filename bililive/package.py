import dataclasses
import struct
import zlib
from enum import Enum
from io import BytesIO
from typing import Iterable

import brotli

WS_PACKAGE_HEADER_TOTAL_LENGTH = 16
WS_PACKAGE_LENGTH_OFFSET = 0
WS_HEADER_LENGTH_OFFSET = 4
WS_VERSION_OFFSET = 6
WS_OPERATION_OFFSET = 8
WS_SEQUENCE_OFFSET = 12


class PackageProtocolVersion(int, Enum):
    NORMAL = 0
    DEFAULT = 1
    ZLIB = 2
    BROTLI = 3


class PackageOperation(int, Enum):
    NORMAL = 0
    DEFAULT = 1
    HEARTBEAT = 2
    HEARTBEAT_REPLY = 3
    MESSAGE = 5
    USER_AUTHENTICATION = 7
    CONNECT_SUCCESS = 8


class PackageSequence(int, Enum):
    NORMAL = 0
    DEFAULT = 1


@dataclasses.dataclass
class Package:
    _struct = struct.Struct("!ihhii")
    header_length = WS_PACKAGE_HEADER_TOTAL_LENGTH

    data: bytes = dataclasses.field(default_factory=bytes)
    protocol_version: PackageProtocolVersion = PackageProtocolVersion.NORMAL
    operation: PackageOperation = PackageOperation.NORMAL
    sequence: PackageSequence = PackageSequence.NORMAL

    @property
    def package_length(self) -> int:
        return self.header_length + len(self.data)

    @property
    def header(self) -> bytes:
        return self._struct.pack(
            self.package_length,
            self.header_length,
            self.protocol_version,
            self.operation,
            self.sequence,
        )

    def pack(self) -> bytes:
        return self.header + self.data

    @classmethod
    def unpack(cls, data: bytes) -> Iterable["Package"]:
        bio = BytesIO(data)
        while True:
            header = bio.read(WS_PACKAGE_HEADER_TOTAL_LENGTH)
            if len(header) < WS_PACKAGE_HEADER_TOTAL_LENGTH:
                break

            pl, hl, pv, op, seq = cls._struct.unpack(header)

            fragment = bio.read(pl - hl)
            if len(fragment) < pl - hl:
                break

            if pv == PackageProtocolVersion.BROTLI:
                decompressed = brotli.decompress(fragment)
                yield from cls.unpack(decompressed)
            elif pv == PackageProtocolVersion.ZLIB:
                decompressed = zlib.decompress(fragment)
                yield from cls.unpack(decompressed)
            else:
                package = cls(fragment, pv, op, seq)
                yield package
