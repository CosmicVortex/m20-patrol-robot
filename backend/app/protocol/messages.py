"""M20 V0.1.0 JSON/XML ASDU semantic codec.

This module has no network, robot-control, navigation or filesystem side effects.
It validates the documented common ASDU envelope before a transport client may use
it. Command-specific validation remains in separate read-only/control modules.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import IntEnum
from typing import Any
from xml.etree import ElementTree


class ASDUSemanticError(ValueError):
    """Raised when an ASDU is not a valid documented PatrolDevice message."""


class ASDUFormat(IntEnum):
    XML = 0x00
    JSON = 0x01


@dataclass(frozen=True)
class PatrolMessage:
    message_type: int
    command: int
    sent_at: str
    items: dict[str, Any]


def encode_patrol_message(message: PatrolMessage, asdu_format: ASDUFormat) -> bytes:
    _validate_message(message)
    format_value = _coerce_format(asdu_format)
    if format_value is ASDUFormat.JSON:
        envelope = {
            "PatrolDevice": {
                "Type": message.message_type,
                "Command": message.command,
                "Time": message.sent_at,
                "Items": message.items,
            }
        }
        return json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    root = ElementTree.Element("PatrolDevice")
    ElementTree.SubElement(root, "Type").text = str(message.message_type)
    ElementTree.SubElement(root, "Command").text = str(message.command)
    ElementTree.SubElement(root, "Time").text = message.sent_at
    items = ElementTree.SubElement(root, "Items")
    _append_xml_items(items, message.items)
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def decode_patrol_message(payload: bytes, asdu_format: ASDUFormat) -> PatrolMessage:
    if type(payload) is not bytes:
        raise ASDUSemanticError("ASDU payload must be immutable bytes")
    format_value = _coerce_format(asdu_format)
    try:
        if format_value is ASDUFormat.JSON:
            envelope = json.loads(payload.decode("utf-8"))
            device = envelope["PatrolDevice"]
            if not isinstance(envelope, dict) or not isinstance(device, dict):
                raise ASDUSemanticError("ASDU must contain PatrolDevice object")
            message = PatrolMessage(
                message_type=device["Type"],
                command=device["Command"],
                sent_at=device["Time"],
                items=device["Items"],
            )
        else:
            root = ElementTree.fromstring(payload)
            if root.tag != "PatrolDevice":
                raise ASDUSemanticError("XML ASDU root must be PatrolDevice")
            message = PatrolMessage(
                message_type=_read_xml_int(root, "Type"),
                command=_read_xml_int(root, "Command"),
                sent_at=_read_xml_text(root, "Time"),
                items=_read_xml_items(root),
            )
    except (KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError, ElementTree.ParseError) as error:
        raise ASDUSemanticError("invalid ASDU envelope") from error
    _validate_message(message)
    return message


def _coerce_format(value: ASDUFormat) -> ASDUFormat:
    if type(value) is not ASDUFormat:
        raise ASDUSemanticError("unsupported ASDU format")
    return value


def _validate_message(message: PatrolMessage) -> None:
    if not isinstance(message, PatrolMessage):
        raise ASDUSemanticError("message must be PatrolMessage")
    for name, value in (("Type", message.message_type), ("Command", message.command)):
        if type(value) is not int or value < 0:
            raise ASDUSemanticError(f"{name} must be a non-negative integer")
    if not isinstance(message.sent_at, str) or not message.sent_at:
        raise ASDUSemanticError("Time must be a non-empty string")
    if not isinstance(message.items, dict):
        raise ASDUSemanticError("Items must be an object")


def _append_xml_items(parent: ElementTree.Element, items: dict[str, Any]) -> None:
    for key, value in items.items():
        if not isinstance(key, str) or not key:
            raise ASDUSemanticError("XML item names must be non-empty strings")
        child = ElementTree.SubElement(parent, key)
        if isinstance(value, dict):
            _append_xml_items(child, value)
        elif isinstance(value, (str, int, float, bool)):
            child.text = str(value).lower() if isinstance(value, bool) else str(value)
        else:
            raise ASDUSemanticError("XML items support only object or scalar values")


def _read_xml_text(root: ElementTree.Element, name: str) -> str:
    node = root.find(name)
    if node is None or node.text is None or not node.text:
        raise ASDUSemanticError(f"XML ASDU missing {name}")
    return node.text


def _read_xml_int(root: ElementTree.Element, name: str) -> int:
    try:
        return int(_read_xml_text(root, name))
    except ValueError as error:
        raise ASDUSemanticError(f"XML {name} must be integer") from error


def _read_xml_items(root: ElementTree.Element) -> dict[str, Any]:
    items = root.find("Items")
    if items is None:
        raise ASDUSemanticError("XML ASDU missing Items")
    return {child.tag: _xml_value(child) for child in items}


def _xml_value(node: ElementTree.Element) -> Any:
    if list(node):
        return {child.tag: _xml_value(child) for child in node}
    return node.text or ""
