# 测试流程

## 运行测试

```bash
PYTHONPATH=. uv run --with pytest pytest -q
```

结果：180 passed

## 真实数据判定

```
source=REAL
message_parsed=true
telemetry_fresh=true
```

端口监听、HTTP 200 不能替代真实遥测。

## 禁止项

以下操作在未获书面放行前禁止执行：
- 发送心跳（Type=100）
- 发送控制命令（Type=2）
- 修改 AOS/NOS 配置
- 使用旧地址 10.21.31.101
