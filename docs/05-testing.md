# 测试流程

## 离线验证

```bash
# 运行测试套件
PYTHONPATH=. uv run --with pytest pytest -q

# 编译检查
python3 -m compileall -q backend

# 部署脚本语法检查
bash -n deploy/scripts/*.sh
```

当前结果：180 passed

## 部署验证

`--dry-run` 输出：
```
NO_FILES_WRITTEN=true
NO_SYSTEMD_CHANGE=true
NO_NETWORK_SIDE_EFFECT=true
```

## 真实数据判定

满足以下条件才判定为真实数据：

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
