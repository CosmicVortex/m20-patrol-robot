"""共享安全检测工具。

提取自 navigation/service.py 和 motion/service.py 的重复实现。
"""

from __future__ import annotations

from typing import Any


# V1.2.1 错误码表 - 保护类错误
PROTECTIVE_FAULT_CODES: set[int] = {
    0x8002, 0x8008, 0x8009, 0x8020,  # 电机/驱动器保护
    0x8103, 0x8106, 0x8107, 0x8108, 0x8112, 0x8115, 0x8116,  # 电池保护
    0x8117, 0x8118, 0x8119, 0x8120, 0x8121, 0x8122,  # 电池保护
    0x8211, 0x8212,  # CPU保护
}


def detect_protective_fault(errors: list[dict[str, Any]]) -> bool:
    """从错误列表检测保护类故障。

    Args:
        errors: 错误列表，每个元素包含 error_code 字段

    Returns:
        bool: 是否存在保护类故障
    """
    for err in errors:
        if err.get("error_code", 0) in PROTECTIVE_FAULT_CODES:
            return True
    return False
