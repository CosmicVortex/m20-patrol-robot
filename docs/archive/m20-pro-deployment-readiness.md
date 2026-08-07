# M20 Pro GOS 部署说明

## 1. 当前可部署版本

本仓库当前可一键部署的是 **GOS 本地模拟只读服务**：

- 不连接 AOS、NOS 或相机；
- 不发送心跳、状态查询或导航报文；
- 服务只绑定 `127.0.0.1:8080`；
- `control_enabled=false` 固定关闭；
- 以 Git commit 作为发布版本；
- 支持按完整 commit SHA 切换到已安装 release。

这不是实时机器人状态服务，也不是导航控制服务。

## 2. GOS 前置条件

由现场负责人确认：

- 使用非 root 账户；
- Python 3 可用，且支持 `venv`；
- `systemctl --user` 可用，且用户服务管理器已启动；
- release 验证所需的 pytest 可用；
- 安装目录有写权限；
- 现场已批准仓库和 commit；
- 不需要访问机器人网络即可完成本次模拟部署。

如需执行现场只读核验，先使用 `deploy/scripts/collect-readonly-info.sh`，只填写已批准的 AOS/GOS/NOS 地址。

## 3. 安装

在已经检出的仓库目录执行：

```bash
bash deploy/scripts/install-gos.sh \
  --repo "$PWD" \
  --ref <APPROVED_COMMIT_SHA>
```

脚本执行内容：

1. 校验完整 commit SHA 存在；
2. 将 commit 导出到独立 release 目录；
3. 创建虚拟环境；
4. 使用批准环境中的 pytest 执行离线测试；pytest 不可用时直接失败，不安装未经批准的依赖；
5. 执行 Python 编译检查；
6. 写入并校验用户级 systemd 服务；
7. 启动模拟只读服务；
8. 服务启动成功后更新 `current` 软链接。

脚本不会执行 `git fetch`、网络探测、机器人连接或控制操作。

## 4. 验证

```bash
systemctl --user status m20-patrol-readonly.service --no-pager
curl -fsS http://127.0.0.1:8080/api/v1/status/latest
curl -fsS http://127.0.0.1:8080/ | grep 'SIMULATED / CONTROL OFF'
```

预期状态至少包含：

```json
{
  "source": "SIMULATED",
  "connected": false,
  "control_enabled": false
}
```

## 5. 停止与回滚

停止：

```bash
systemctl --user disable --now m20-patrol-readonly.service
```

回滚到已安装版本：

```bash
bash deploy/scripts/rollback-gos.sh \
  --ref <INSTALLED_COMMIT_SHA>
```

回滚脚本只切换本地 release 和服务配置，不访问机器人。

## 6. 真实接入禁止条件

以下条件未全部满足前，不得扩展安装脚本使其连接真实设备：

- 实际 M20 Pro 系统/固件版本已确认；
- basic_server 权限、地址、端口和真实脱敏报文样本已确认；
- 状态、定位、异常、急停和电量新鲜度可判定；
- 导航门控、授权、审计和取消逻辑通过离线测试；
- 现场负责人书面放行。
