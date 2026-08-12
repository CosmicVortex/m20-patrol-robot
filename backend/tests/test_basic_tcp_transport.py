from __future__ import annotations

import socket
import threading
import time
from datetime import datetime

from backend.app.protocol.frame import FrameCodec, m20_v010_layout
from backend.app.protocol.messages import ASDUFormat, PatrolMessage, decode_patrol_message, encode_patrol_message
from backend.app.robot.basic_client import BasicServerClient, BasicServerConfig


def test_tcp_client_sends_heartbeat_and_receives_response_and_status_frame():
    codec = FrameCodec(m20_v010_layout())
    ready = threading.Event()
    received: list[PatrolMessage] = []
    address: list[tuple[str, int]] = []

    def server() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            address.append(listener.getsockname())
            ready.set()
            connection, _ = listener.accept()
            with connection:
                data = connection.recv(4096)
                request = decode_patrol_message(codec.decode(data).payload, ASDUFormat.JSON)
                received.append(request)
                response = PatrolMessage(100, 100, "2026-08-06 14:00:00", {"ErrorCode": 0})
                status = PatrolMessage(1002, 6, "2026-08-06 14:00:00", {"BasicStatus": {"Version": "fixture"}})
                connection.sendall(
                    codec.encode(message_id=0, payload=encode_patrol_message(response, ASDUFormat.JSON), flags=1)
                    + codec.encode(message_id=99, payload=encode_patrol_message(status, ASDUFormat.JSON), flags=1)
                )

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    assert ready.wait(1)

    client = BasicServerClient(BasicServerConfig(host="10.21.31.103", transmit_enabled=True))
    client.connect_for_test(address[0])
    response = client.send_read_only(client.build_heartbeat())
    messages = client.receive_messages(timeout_seconds=1)
    client.close()
    thread.join(1)

    assert received[0].message_type == 100
    assert response.items == {"ErrorCode": 0}
    assert [(item.message_type, item.command) for item in messages] == [(1002, 6)]
    assert client.is_stale(datetime.now().astimezone()) is False


def test_tcp_client_reassembles_split_response_frame():
    codec = FrameCodec(m20_v010_layout())
    ready = threading.Event()
    address: list[tuple[str, int]] = []

    def server() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            address.append(listener.getsockname())
            ready.set()
            connection, _ = listener.accept()
            with connection:
                connection.recv(4096)
                response = PatrolMessage(100, 100, "2026-08-06 14:00:00", {"ErrorCode": 0})
                frame = codec.encode(message_id=0, payload=encode_patrol_message(response, ASDUFormat.JSON), flags=1)
                midpoint = len(frame) // 2
                connection.sendall(frame[:midpoint])
                time.sleep(0.05)
                connection.sendall(frame[midpoint:])

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    assert ready.wait(1)
    client = BasicServerClient(BasicServerConfig(host="10.21.31.103", transmit_enabled=True))
    client.connect_for_test(address[0])
    response = client.send_read_only(client.build_heartbeat())
    client.close()
    thread.join(1)

    assert response.items == {"ErrorCode": 0}
