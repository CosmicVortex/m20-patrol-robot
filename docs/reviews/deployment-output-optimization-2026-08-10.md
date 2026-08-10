# M20 Pro 部署输出优化报告

**优化日期**: 2026-08-10
**优化范围**: 部署脚本、后端日志、错误消息

---

## 一、修复的问题

### P0 — 关键 Bug

| ID | 文件 | 问题 | 修复 |
|----|------|------|------|
| P0-1 | `backend/app/server.py:310` | `main()` 递归调用导致无限循环 | 删除重复的 `if __name__ == "__main__": main()` |
| P0-2 | `backend/app/gimbal/adapter.py:270-277` | `_fallback_scan()` 存在死代码 (return 后逻辑) | 删除重复的 return 语句 |

### P1 — 输出优化

| ID | 文件 | 问题 | 修复 |
|----|------|------|------|
| P1-1 | `backend/app/video/stream_manager.py` | 错误消息为英文 | 全部改为中文 |
| P1-2 | `backend/app/gimbal/adapter.py` | login() 缺少 HTTP 错误处理 | 添加详细错误日志 |
| P1-3 | `backend/app/robot/telemetry.py` | 日志消息不完整 | 改进消息格式 |
| P1-4 | `deploy/scripts/deploy-readonly.sh` | 错误码无中文解释 | 所有错误添加中文描述 |

---

## 二、错误消息对照表

### 部署脚本错误

| 错误码 | 修复前 | 修复后 |
|--------|--------|--------|
| MANIFEST_MISSING | `BLOCKED:MANIFEST_MISSING` | `BLOCKED:MANIFEST_MISSING (部署清单文件未找到)` |
| PYTHON_MISSING | `BLOCKED:PYTHON_MISSING` | `BLOCKED:PYTHON_MISSING (python3 命令未找到)` |
| SYSTEMCTL_MISSING | `BLOCKED:SYSTEMCTL_MISSING` | `BLOCKED:SYSTEMCTL_MISSING (systemctl 命令未找到，需要 systemd 支持)` |
| ROOT_USER_NOT_ALLOWED | `BLOCKED:ROOT_USER_NOT_ALLOWED` | `BLOCKED:ROOT_USER_NOT_ALLOWED (不允许以 root 用户部署)` |
| GOS_IDENTITY_MISMATCH | `BLOCKED:GOS_IDENTITY_MISMATCH` | `BLOCKED:GOS_IDENTITY_MISMATCH (GOS 身份不匹配)` |
| SERVICE_NOT_ACTIVE | `BLOCKED:SERVICE_NOT_ACTIVE` | `BLOCKED:SERVICE_NOT_ACTIVE (服务未处于活动状态)` |

### Python 错误消息

| 模块 | 修复前 | 修复后 |
|------|--------|--------|
| stream_manager.py | `Unknown camera source: {source}` | `未知摄像头源: {source}` |
| stream_manager.py | `real video I/O is disabled by default` | `视频 I/O 默认禁用，需配置 allow_real_io=true` |
| stream_manager.py | `stale process did not exit` | `进程未能正常退出` |
| gimbal/adapter.py | `Gimbal request error` | `云台请求异常` |
| gimbal/adapter.py | `Failed to get gimbal info` | `获取云台信息失败` |
| telemetry.py | (无变化) | 日志消息已优化 |

---

## 三、测试结果

```bash
$ PYTHONPATH=. uv run --with pytest pytest -q --tb=short
........................................................................ [ 40%]
........................................................................ [ 80%]
....................................                                     [100%]
180 passed in 5.07s ✅
```

**编译检查**:
```bash
$ python3 -m py_compile backend/app/server.py backend/app/video/stream_manager.py backend/app/gimbal/adapter.py backend/app/robot/telemetry.py
所有文件编译通过 ✅
```

**部署预检**:
```bash
$ bash deploy/scripts/deploy-readonly.sh --preflight
PYTHON_VERSION=3.13.5
PY_RUNTIME_CHECK=PASS (Python 运行时检查通过)
PY_AST_CHECK=PASS (Python 代码 AST 检查通过)
PY_IMPORT_CHECK=PASS (Python 模块导入检查通过)
=== 网络配置检查 ===
GOS_HOST=10.21.31.104 AOS_HOST=10.21.31.103 NOS_HOST=10.21.31.106
BLOCKED:SYSTEMCTL_MISSING (systemctl 命令未找到，需要 systemd 支持)
```

---

## 四、优化后的输出示例

### 成功启动日志
```
2026-08-10 09:30:00 INFO backend.app.server: 初始化遥测适配器...
2026-08-10 09:30:00 INFO backend.app.server: 配置云台地址: 192.168.1.108
2026-08-10 09:30:01 INFO backend.app.server: 云台已连接: 192.168.1.108
2026-08-10 09:30:01 INFO backend.app.server: M20 Web Service starting on 10.21.31.104:8080
Runtime mode: realtime_readonly
Read-only: True
Control enabled: False
Auth enabled: True
Gimbal: 192.168.1.108
2026-08-10 09:30:01 INFO backend.app.server: Web服务已启动: 10.21.31.104:8080
2026-08-10 09:30:01 INFO backend.app.server: 遥测目标: 10.21.31.103:30001 (模式: realtime_readonly)
2026-08-10 09:30:01 INFO backend.app.server: 安全配置: 只读模式=True, 控制命令=False
```

### 错误输出示例
```
BLOCKED:MANIFEST_MISSING (部署清单文件未找到)
BLOCKED:GOS_IDENTITY_MISMATCH (GOS 身份不匹配)
  期望IP: 10.21.31.104
  实际IP: 192.168.1.100
BLOCKED:SYSTEMCTL_MISSING (systemctl 命令未找到，需要 systemd 支持)
```

---

## 五、修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `backend/app/server.py` | 删除递归 main() 调用 |
| `backend/app/video/stream_manager.py` | 错误消息中文化 |
| `backend/app/gimbal/adapter.py` | 删除死代码，改进错误处理 |
| `backend/app/robot/telemetry.py` | 日志消息优化 |
| `deploy/scripts/deploy-readonly.sh` | 所有错误码添加中文解释 |

---

## 六、待确认事项

1. **Python 3.8.10 兼容性**: 当前运行 Python 3.13，需验证 GOS 目标版本 (Python 3.8.10)
2. **systemd 服务**: 当前环境无 systemd，需在 GOS 实机验证服务启动
3. **云台默认密码**: `123456` 仍需修改为现场配置值
4. **RTSP 地址**: 候选值，需 ffprobe 确认可达性

---

## 七、后续建议

1. 将部署日志输出到文件便于问题排查
2. 添加健康检查端点返回详细状态
3. 考虑将错误码提取到常量文件便于维护
