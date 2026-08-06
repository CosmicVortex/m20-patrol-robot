"""Offline codec for the documented basic_server APDU/ASDU transport.

The exact vendor header byte map is intentionally represented by FrameLayout so
field offsets can be corrected from a real protocol sample without changing the
stream decoder. This module does not open sockets or send robot commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


class FrameProtocolError(ValueError):
    """Raised when a frame violates the configured transport layout."""


@dataclass(frozen=True)
class FrameLayout:
    sync_word: bytes
    length_offset: int
    length_size: int
    message_id_offset: int
    message_id_size: int
    flags_offset: int
    header_size: int
    length_includes_header: bool = False
    byteorder: Literal["little", "big"] = "little"
    reserved_offset: int | None = None
    reserved_size: int = 0
    allowed_flags: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.sync_word, bytes) or not self.sync_word:
            raise ValueError("sync_word must be non-empty bytes")
        if type(self.header_size) is not int or self.header_size < len(self.sync_word):
            raise ValueError("header_size must contain sync_word")
        for name, value in (
            ("length_offset", self.length_offset),
            ("length_size", self.length_size),
            ("message_id_offset", self.message_id_offset),
            ("message_id_size", self.message_id_size),
            ("flags_offset", self.flags_offset),
        ):
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.length_size not in (1, 2, 4, 8):
            raise ValueError("length_size must be a native integer width")
        if self.message_id_size not in (1, 2, 4, 8):
            raise ValueError("message_id_size must be a native integer width")
        if self.byteorder not in ("little", "big"):
            raise ValueError("byteorder must be little or big")
        if self.reserved_offset is None and self.reserved_size != 0:
            raise ValueError("reserved_size requires reserved_offset")
        if self.reserved_offset is not None and (
            type(self.reserved_offset) is not int or self.reserved_offset < 0
        ):
            raise ValueError("reserved_offset must be a non-negative integer")
        if type(self.reserved_size) is not int or self.reserved_size < 0:
            raise ValueError("reserved_size must be a non-negative integer")
        if self.allowed_flags is not None and any(
            type(value) is not int or value < 0 or value > 255 for value in self.allowed_flags
        ):
            raise ValueError("allowed_flags must contain byte-sized integers")
        fields = {
            "sync_word": (0, len(self.sync_word)),
            "length": (self.length_offset, self.length_size),
            "message_id": (self.message_id_offset, self.message_id_size),
            "flags": (self.flags_offset, 1),
        }
        for name, (offset, size) in fields.items():
            if offset + size > self.header_size:
                raise ValueError(f"{name} field exceeds header_size")
        if self.reserved_offset is not None:
            if self.reserved_offset + self.reserved_size > self.header_size:
                raise ValueError("reserved field exceeds header_size")
            if self.reserved_size == 0:
                raise ValueError("reserved_size must be positive")
            fields["reserved"] = (self.reserved_offset, self.reserved_size)
        ranges = list(fields.items())
        for index, (left_name, (left_offset, left_size)) in enumerate(ranges):
            for right_name, (right_offset, right_size) in ranges[index + 1 :]:
                if max(left_offset, right_offset) < min(
                    left_offset + left_size, right_offset + right_size
                ):
                    raise ValueError(f"{left_name} overlaps {right_name}")


@dataclass(frozen=True)
class Frame:
    message_id: int
    payload: bytes
    flags: int = 0


class FrameCodec:
    def __init__(self, layout: FrameLayout, *, max_payload_size: int = 4 * 1024 * 1024):
        if type(max_payload_size) is not int or max_payload_size < 0:
            raise ValueError("max_payload_size must be a non-negative integer")
        self.layout = layout
        self.max_payload_size = max_payload_size

    def encode(self, *, message_id: int, payload: bytes, flags: int = 0) -> bytes:
        if not isinstance(payload, bytes):
            raise TypeError("payload must be bytes")
        self._validate_integer(message_id, self.layout.message_id_size, "message_id")
        self._validate_integer(flags, 1, "flags")
        self._validate_format(flags)
        if len(payload) > self.max_payload_size:
            raise FrameProtocolError("payload exceeds configured limit")

        length_value = len(payload) + (
            self.layout.header_size if self.layout.length_includes_header else 0
        )
        self._validate_integer(length_value, self.layout.length_size, "length")
        header = bytearray(self.layout.header_size)
        header[: len(self.layout.sync_word)] = self.layout.sync_word
        self._put(header, self.layout.length_offset, self.layout.length_size, length_value)
        self._put(header, self.layout.message_id_offset, self.layout.message_id_size, message_id)
        self._put(header, self.layout.flags_offset, 1, flags)
        if self.layout.reserved_offset is not None:
            header[self.layout.reserved_offset : self.layout.reserved_offset + self.layout.reserved_size] = (
                b"\x00" * self.layout.reserved_size
            )
        return bytes(header) + payload

    def decode(self, data: bytes) -> Frame:
        if type(data) is not bytes:
            raise TypeError("data must be bytes")
        if len(data) < self.layout.header_size:
            raise FrameProtocolError("truncated header")
        if data[: len(self.layout.sync_word)] != self.layout.sync_word:
            raise FrameProtocolError("invalid sync word")
        self._validate_format(self._get(data, self.layout.flags_offset, 1))
        self._validate_reserved(data)
        expected_size = self.frame_size(data[: self.layout.header_size])
        if len(data) < expected_size:
            raise FrameProtocolError("truncated frame")
        if len(data) != expected_size:
            raise FrameProtocolError("trailing bytes after frame")
        return Frame(
            message_id=self._get(data, self.layout.message_id_offset, self.layout.message_id_size),
            payload=data[self.layout.header_size :],
            flags=self._get(data, self.layout.flags_offset, 1),
        )

    def frame_size(self, header: bytes) -> int:
        if len(header) < self.layout.header_size:
            raise FrameProtocolError("truncated header")
        if header[: len(self.layout.sync_word)] != self.layout.sync_word:
            raise FrameProtocolError("invalid sync word")
        self._validate_format(self._get(header, self.layout.flags_offset, 1))
        self._validate_reserved(header)
        length_value = self._get(header, self.layout.length_offset, self.layout.length_size)
        payload_size = length_value - self.layout.header_size if self.layout.length_includes_header else length_value
        if payload_size < 0 or payload_size > self.max_payload_size:
            raise FrameProtocolError("invalid payload length")
        return self.layout.header_size + payload_size

    def _get(self, data: bytes, offset: int, size: int) -> int:
        return int.from_bytes(data[offset : offset + size], self.layout.byteorder)

    def _put(self, data: bytearray, offset: int, size: int, value: int) -> None:
        data[offset : offset + size] = value.to_bytes(size, self.layout.byteorder)

    @staticmethod
    def _validate_integer(value: int, size: int, name: str) -> None:
        if type(value) is not int or value < 0 or value >= 1 << (size * 8):
            raise ValueError(f"{name} does not fit configured field")

    def _validate_format(self, value: int) -> None:
        if self.layout.allowed_flags is not None and value not in self.layout.allowed_flags:
            raise FrameProtocolError("invalid ASDU format")

    def _validate_reserved(self, data: bytes) -> None:
        if self.layout.reserved_offset is not None:
            start = self.layout.reserved_offset
            end = start + self.layout.reserved_size
            if data[start:end] != b"\x00" * self.layout.reserved_size:
                raise FrameProtocolError("reserved header bytes must be zero")


class IncrementalDecoder:
    def __init__(self, codec: FrameCodec):
        self.codec = codec
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[Frame]:
        if type(data) is not bytes:
            raise TypeError("data must be bytes")
        frames: list[Frame] = []
        max_buffer = self.codec.layout.header_size + self.codec.max_payload_size
        try:
            # Parse bounded chunks so an incomplete frame cannot make the
            # internal buffer temporarily larger than the configured limit.
            cursor = 0
            while cursor < len(data):
                room = max_buffer - len(self._buffer)
                if room <= 0:
                    self._drain(frames)
                    room = max_buffer - len(self._buffer)
                    if room <= 0:
                        raise FrameProtocolError("buffer exceeds configured frame limit")
                chunk_size = min(room, len(data) - cursor)
                self._buffer.extend(data[cursor : cursor + chunk_size])
                cursor += chunk_size
                self._drain(frames)
        except FrameProtocolError:
            self.reset()
            raise
        return frames

    def _drain(self, frames: list[Frame]) -> None:
        consumed = 0
        while len(self._buffer) - consumed >= self.codec.layout.header_size:
            view = bytes(self._buffer[consumed : consumed + self.codec.layout.header_size])
            size = self.codec.frame_size(view)
            if len(self._buffer) - consumed < size:
                break
            frames.append(self.codec.decode(bytes(self._buffer[consumed : consumed + size])))
            consumed += size
        if consumed:
            del self._buffer[:consumed]

    def finalize(self) -> None:
        """Mark end-of-stream and reject any incomplete buffered frame."""
        if self._buffer:
            self.reset()
            raise FrameProtocolError("truncated frame at end of stream")

    def reset(self) -> None:
        self._buffer.clear()


def m20_v010_layout() -> FrameLayout:
    """Return the M20 V0.1.0 APDU header layout from the supplied handbook."""
    return FrameLayout(
        sync_word=b"\xeb\x91\xeb\x90",
        length_offset=4,
        length_size=2,
        message_id_offset=6,
        message_id_size=2,
        flags_offset=8,
        header_size=16,
        length_includes_header=False,
        byteorder="little",
        reserved_offset=9,
        reserved_size=7,
        allowed_flags=(0, 1),
    )
