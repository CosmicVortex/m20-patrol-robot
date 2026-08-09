# 阻塞项修复报告

**日期：** 2026-08-06
**状态：** 全部修复 ✅

---

## 修复汇总

| 阻塞项 | 问题描述 | 修复方案 | 状态 |
|---|---|---|---|
| message_id关联 | TCP响应按message_type+command匹配，可能误判延迟响应 | 新增message_id字段，按ID匹配 | ✅ |
| control_enabled门禁 | connect()允许在control_enabled=False时连接 | 增加control_enabled检查 | ✅ |
| 安装回滚 | rollback-gos.sh失败时无法恢复unit文件 | 保存前置状态，失败自动恢复 | ✅ |

---

## 详细变更

### 1. message_id关联

**文件：** `backend/app/protocol/messages.py`
```python
@dataclass(frozen=True)
class PatrolMessage:
    message_type: int
    command: int
    sent_at: str
    items: dict[str, Any]
    message_id: int = 0  # V1.2.1: 请求/响应关联ID
```

**文件：** `backend/app/robot/basic_client.py`
```python
# send_read_only: match by message_id
if response is None and received.message_id == frame_id:
    response = received
else:
    self._inbox.append(received)
```

**协议依据：** V1.2.1 §1.1.5 — "报文ID...值由请求方控制，响应帧将采用相同值回复"

### 2. control_enabled门禁

**文件：** `backend/app/robot/basic_client.py`
```python
def connect(self, *, timeout_seconds: float = 3.0) -> None:
    if not self.config.control_enabled:
        raise ClientStateError("control is disabled; cannot connect to real device")
    # 后续检查 protocol_evidence, firmware_evidence, permission_evidence
```

### 3. 安装回滚

**文件：** `deploy/scripts/rollback-gos.sh`
```bash
# 保存前置状态
SAVED_UNIT="$TARGET_ROOT/.rollback.saved-unit.$$"
if [ -f "$UNIT_PATH" ]; then
  cp -p "$UNIT_PATH" "$SAVED_UNIT"
fi

# 失败时自动恢复
cleanup() {
  local status=$?
  if [ "$status" -ne 0 ]; then
    if [ -f "$SAVED_UNIT" ] && [ -f "$UNIT_PATH" ]; then
      cp -p "$SAVED_UNIT" "$UNIT_PATH"
      systemctl --user daemon-reload 2>/dev/null || true
    fi
  fi
}
trap cleanup EXIT
```

---

## 验证结果

```bash
$ PYTHONPATH=. uv run --with pytest pytest -q
76 passed in 0.20s

$ python3 -m compileall -q backend
# 通过

$ git diff --check
# 通过
```

---

## 下一步

三个阻塞项已修复，代码已准备好进行[测试场地]阶段实机测试准入评审。
