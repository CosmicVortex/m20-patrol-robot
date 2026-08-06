import pytest

from backend.app.protocol.frame import (
    FrameCodec,
    FrameLayout,
    FrameProtocolError,
    IncrementalDecoder,
    m20_v010_layout,
)


def make_layout(**overrides):
    values = dict(
        sync_word=b"\xAA\x55",
        length_offset=2,
        length_size=2,
        message_id_offset=4,
        message_id_size=4,
        flags_offset=8,
        header_size=16,
        length_includes_header=False,
        byteorder="little",
    )
    values.update(overrides)
    return FrameLayout(**values)


def test_encode_and_decode_json_frame():
    codec = FrameCodec(make_layout())
    encoded = codec.encode(message_id=1002, payload=b'{"status":"ok"}', flags=1)

    decoded = codec.decode(encoded)

    assert decoded.message_id == 1002
    assert decoded.flags == 1
    assert decoded.payload == b'{"status":"ok"}'


def test_big_endian_and_length_including_header():
    codec = FrameCodec(make_layout(byteorder="big", length_includes_header=True))

    encoded = codec.encode(message_id=0x01020304, payload=b"abc", flags=255)
    decoded = codec.decode(encoded)

    assert encoded[2:4] == (19).to_bytes(2, "big")
    assert decoded == codec.decode(encoded)
    assert (decoded.message_id, decoded.flags, decoded.payload) == (0x01020304, 255, b"abc")


def test_incremental_decoder_handles_bytewise_split_and_three_frames():
    codec = FrameCodec(m20_v010_layout())
    frames = [codec.encode(message_id=i, payload=bytes([i])) for i in range(3)]
    decoder = IncrementalDecoder(codec)

    received = []
    for frame in frames:
        for byte in frame:
            received.extend(decoder.feed(bytes([byte])))

    assert [(frame.message_id, frame.payload) for frame in received] == [(0, b"\x00"), (1, b"\x01"), (2, b"\x02")]


def test_incremental_decoder_handles_combined_frames():
    codec = FrameCodec(m20_v010_layout())
    first = codec.encode(message_id=1, payload=b"one")
    second = codec.encode(message_id=2, payload=b"two")

    assert [(f.message_id, f.payload) for f in IncrementalDecoder(codec).feed(first + second)] == [
        (1, b"one"),
        (2, b"two"),
    ]


def test_finalize_rejects_incomplete_frame_and_resets():
    codec = FrameCodec(m20_v010_layout())
    decoder = IncrementalDecoder(codec)
    decoder.feed(codec.encode(message_id=1, payload=b"x")[:-1])

    with pytest.raises(FrameProtocolError, match="end of stream"):
        decoder.finalize()

    assert decoder.feed(codec.encode(message_id=2, payload=b"ok"))[0].message_id == 2


def test_decoder_rejects_invalid_sync_and_clears_buffer():
    codec = FrameCodec(m20_v010_layout())
    decoder = IncrementalDecoder(codec)
    invalid = bytearray(codec.encode(message_id=1, payload=b"x"))
    invalid[0:2] = b"\x00\x00"

    with pytest.raises(FrameProtocolError, match="sync"):
        decoder.feed(bytes(invalid))

    assert decoder.feed(codec.encode(message_id=2, payload=b"ok"))[0].message_id == 2


def test_decoder_rejects_trailing_bytes():
    codec = FrameCodec(make_layout())

    with pytest.raises(FrameProtocolError, match="trailing"):
        codec.decode(codec.encode(message_id=1, payload=b"x") + b"extra")


def test_decode_requires_immutable_bytes_input():
    codec = FrameCodec(make_layout())
    encoded = codec.encode(message_id=1, payload=b"x")

    with pytest.raises(TypeError):
        codec.decode(bytearray(encoded))
    with pytest.raises(TypeError):
        codec.decode(memoryview(encoded))


def test_decoder_rejects_declared_payload_over_limit():
    codec = FrameCodec(make_layout(), max_payload_size=3)
    encoded = bytearray(codec.encode(message_id=1, payload=b"123"))
    encoded[2:4] = (4).to_bytes(2, "little")

    with pytest.raises(FrameProtocolError, match="payload"):
        codec.decode(bytes(encoded))


def test_incremental_decoder_rejects_oversized_incomplete_input_before_retaining_it():
    codec = FrameCodec(make_layout(), max_payload_size=2)
    decoder = IncrementalDecoder(codec)

    with pytest.raises(FrameProtocolError, match="invalid payload length"):
        decoder.feed(codec.layout.sync_word + b"\xff\xff" + b"x" * 100)

    assert decoder.feed(codec.encode(message_id=2, payload=b"ok"))[0].message_id == 2


def test_zero_and_maximum_payload_are_supported():
    codec = FrameCodec(make_layout(), max_payload_size=2)

    assert codec.decode(codec.encode(message_id=1, payload=b"")).payload == b""
    assert codec.decode(codec.encode(message_id=1, payload=b"12")).payload == b"12"


def test_rejects_invalid_layouts():
    for overrides in (
        {"length_offset": -1},
        {"length_offset": 15, "length_size": 2},
        {"message_id_offset": 15, "message_id_size": 4},
        {"flags_offset": 16},
        {"length_offset": 0, "length_size": 2},
    ):
        with pytest.raises(ValueError):
            make_layout(**overrides)


def test_rejects_boolean_integer_fields():
    codec = FrameCodec(make_layout())

    with pytest.raises(ValueError):
        codec.encode(message_id=True, payload=b"")
    with pytest.raises(ValueError):
        codec.encode(message_id=1, payload=b"", flags=False)


def test_m20_v010_layout_matches_handbook_header():
    codec = FrameCodec(m20_v010_layout(), max_payload_size=65535)
    payload = b'{"PatrolDevice":{"Type":100,"Command":100,"Time":"2025-09-16 00:00:00","Items":{}}}'

    encoded = codec.encode(message_id=7, payload=payload, flags=1)

    assert encoded[:4] == b"\xeb\x91\xeb\x90"
    assert int.from_bytes(encoded[4:6], "little") == len(payload)
    assert int.from_bytes(encoded[6:8], "little") == 7
    assert encoded[8] == 1
    assert encoded[9:16] == b"\x00" * 7
    assert codec.decode(encoded).payload == payload


def test_m20_v010_layout_supports_json_and_xml_format_values():
    codec = FrameCodec(m20_v010_layout())
    json_payload = b'{"PatrolDevice":{"Type":100,"Command":100,"Time":"2025-09-16 00:00:00","Items":{}}}'
    xml_payload = b'<?xml version="1.0" encoding="UTF-8"?><PatrolDevice><Type>100</Type><Command>100</Command><Time>2025-09-16 00:00:00</Time><Items/></PatrolDevice>'

    json_frame = codec.encode(message_id=1, payload=json_payload, flags=1)
    xml_frame = codec.encode(message_id=2, payload=xml_payload, flags=0)

    assert json_frame[8] == 0x01
    assert xml_frame[8] == 0x00
    assert codec.decode(json_frame).payload == json_payload
    assert codec.decode(xml_frame).payload == xml_payload


def test_m20_v010_layout_enforces_asdu_length_limit():
    codec = FrameCodec(m20_v010_layout(), max_payload_size=65535)
    maximum = codec.encode(message_id=1, payload=b"x" * 65535, flags=1)

    assert int.from_bytes(maximum[4:6], "little") == 65535
    assert len(codec.decode(maximum).payload) == 65535
    with pytest.raises(FrameProtocolError, match="payload"):
        codec.encode(message_id=1, payload=b"x" * 65536, flags=1)


def test_m20_v010_layout_rejects_every_nonzero_reserved_byte():
    codec = FrameCodec(m20_v010_layout())
    encoded = codec.encode(message_id=1, payload=b"{}", flags=1)

    for offset in range(9, 16):
        invalid = bytearray(encoded)
        invalid[offset] = 1
        with pytest.raises(FrameProtocolError, match="reserved"):
            codec.decode(bytes(invalid))


def test_m20_v010_layout_rejects_nonzero_reserved_header_bytes():
    codec = FrameCodec(m20_v010_layout())
    encoded = bytearray(codec.encode(message_id=1, payload=b"{}", flags=1))
    encoded[9] = 1

    with pytest.raises(FrameProtocolError, match="reserved"):
        codec.decode(bytes(encoded))


def test_m20_v010_layout_rejects_unsupported_format_flag():
    codec = FrameCodec(m20_v010_layout())
    encoded = codec.encode(message_id=1, payload=b"{}", flags=1)
    invalid = bytearray(encoded)
    invalid[8] = 2

    with pytest.raises(FrameProtocolError, match="format"):
        codec.decode(bytes(invalid))
