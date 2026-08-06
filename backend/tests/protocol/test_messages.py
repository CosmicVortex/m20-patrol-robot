import json

import pytest

from backend.app.protocol.messages import (
    ASDUFormat,
    ASDUSemanticError,
    PatrolMessage,
    decode_patrol_message,
    encode_patrol_message,
)


def test_encodes_documented_json_heartbeat_with_utf8_byte_length():
    message = PatrolMessage(
        message_type=100,
        command=100,
        sent_at="2026-08-05 12:00:00",
        items={"label": "展厅"},
    )

    payload = encode_patrol_message(message, ASDUFormat.JSON)

    assert len(payload) == len(payload.decode("utf-8").encode("utf-8"))
    assert json.loads(payload)["PatrolDevice"] == {
        "Type": 100,
        "Command": 100,
        "Time": "2026-08-05 12:00:00",
        "Items": {"label": "展厅"},
    }


def test_decodes_documented_json_asdu_into_typed_message():
    payload = b'{"PatrolDevice":{"Type":1002,"Command":6,"Time":"2026-08-05 12:00:00","Items":{"BasicStatus":{"Version":"PRO"}}}}'

    decoded = decode_patrol_message(payload, ASDUFormat.JSON)

    assert decoded.message_type == 1002
    assert decoded.command == 6
    assert decoded.sent_at == "2026-08-05 12:00:00"
    assert decoded.items["BasicStatus"]["Version"] == "PRO"


@pytest.mark.parametrize(
    "payload",
    [
        b"{not-json}",
        b'{"PatrolDevice":{"Type":100,"Command":100,"Items":{}}}',
        b'{"PatrolDevice":{"Type":true,"Command":100,"Time":"2026-08-05 12:00:00","Items":{}}}',
        b'{"PatrolDevice":{"Type":100,"Command":100,"Time":"2026-08-05 12:00:00","Items":[]}}',
        b"\xff",
    ],
)
def test_rejects_invalid_json_asdu(payload):
    with pytest.raises(ASDUSemanticError):
        decode_patrol_message(payload, ASDUFormat.JSON)


def test_round_trips_documented_xml_asdu():
    original = PatrolMessage(
        message_type=100,
        command=100,
        sent_at="2026-08-05 12:00:00",
        items={},
    )

    decoded = decode_patrol_message(encode_patrol_message(original, ASDUFormat.XML), ASDUFormat.XML)

    assert decoded == original


def test_rejects_unknown_asdu_format():
    message = PatrolMessage(100, 100, "2026-08-05 12:00:00", {})

    with pytest.raises(ASDUSemanticError):
        encode_patrol_message(message, 99)  # type: ignore[arg-type]
