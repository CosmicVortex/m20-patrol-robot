# MobaXterm 部署指南 — 离线传输与解压

**适用场景：** GOS 主机未接入互联网，需从笔记本电脑手动传输程序

---

## 一、原理说明

本程序的 Web 应用是一个 **Python TCP 客户端 + HTTP 服务端**：

```
┌─────────────────────────────────────────────────────────────────┐
│                        浏览器                                   │
│                  http://10.21.31.104:8080/                     │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP/JSON（GOS 作为服务端）
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GOS (10.21.31.104)                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Python Web 服务（HTTP 服务端，监听 127.0.0.1:8080）     │   │
│  │  - 提供 /api/v1/status/latest                            │   │
│  │  - 提供 Web 页面                                         │   │
│  └─────────────────────┬───────────────────────────────────┘   │
│                        │                                        │
│  ┌─────────────────────▼───────────────────────────────────┐   │
│  │  TelemetryAdapter（TCP 客户端，连接 AOS 30001）           │   │
│  │  - 每 1 秒发送心跳（Type=100, Cmd=100）                  │   │
│  │  - 接收状态消息并解析                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────────┘
                      │ TCP 30001（GOS 作为客户端）
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AOS (10.21.31.103)                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  basic_server（TCP/UDP 服务端）                          │   │
│  │  - TCP 30001：状态订阅、任务下发                          │   │
│  │  - UDP 30000：高频速度指令                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  RTSP 视频流：                                                   │
│  - rtsp://10.21.31.103:8554/video1（前相机）                    │
│  - rtsp://10.21.31.103:8554/video2（后相机）                    │
└─────────────────────────────────────────────────────────────────┘
```

**关键事实：**
- GOS 程序是 **TCP 客户端**（主动连接 AOS），不是服务端
- GOS 同时是 **HTTP 服务端**（供浏览器访问）
- 程序不修改 AOS/NOS 的任何服务或配置
- 默认 `control_enabled=false`，导航命令需 Web 授权 + 书面放行

---

## 二、程序包结构

```
m20-patrol-robot/
├── backend/                    # 核心代码（约 556KB）
│   ├── app/
│   │   ├── protocol/           # APDU/ASDU 编解码
│   │   ├── robot/              # TCP 客户端、状态解析
│   │   ├── navigation/         # 导航报文构造、控制服务
│   │   ├── video/              # 视频流管理
│   │   ├── dashboard.py        # 模拟仪表盘
│   │   └── dashboard_realtime.py  # 实时仪表盘
│   └── tests/                  # 测试代码
├── deploy/                     # 部署脚本
│   ├── scripts/
│   │   ├── install-gos.sh      # 安装脚本
│   │   ├── rollback-gos.sh     # 回滚脚本
│   │   └── collect-readonly-info.sh  # 只读信息收集
│   └── systemd/
│       ├── m20-patrol-readonly.service  # 模拟模式服务
│       └── m20-patrol-realtime.service  # 真实模式服务
└── docs/                       # 文档（约 6.6MB，部署时可省略）
```

**最小部署包：** 仅 `backend/` + `deploy/` 目录，约 600KB

---

## 三、MobaXterm 传输步骤

### 3.1 准备传输包

在笔记本电脑上，进入仓库目录：

```bash
# 创建轻量化部署包（仅包含必要文件）
cd /path/to/m20-patrol-robot
tar -czf ~/m20-patrol-deploy.tar.gz \
  backend/ \
  deploy/ \
  --exclude='backend/tests' \
  --exclude='backend/__pycache__' \
  --exclude='*/__pycache__'
```

或者传输完整包（包含文档，约 14MB）：

```bash
tar -czf ~/m20-patrol-full.tar.gz .
```

### 3.2 通过 MobaXterm 传输

#### 方式一：MobaXterm SFTP 拖拽

1. 打开 MobaXterm，连接到 GOS：
   ```
   SSH 主机：10.21.31.104
   用户名：user（或实际账户）
   ```

2. 连接成功后，左侧会出现 SFTP 会话窗口

3. 在 SFTP 窗口中导航到目标目录：
   ```
   /home/user/
   ```

4. 从笔记本电脑的 MobaXterm 资源管理器（左下角）找到 `m20-patrol-deploy.tar.gz`

5. **拖拽** 文件到 SFTP 窗口的 `/home/user/` 目录

#### 方式二：MobaXterm 内置传输命令

在 MobaXterm SSH 终端中执行：

```bash
# 创建目标目录
mkdir -p ~/m20-patrol-robot
cd ~/m20-patrol-robot

# 从 MobaXterm 传输（如果文件已在本地缓存）
# 或者使用 scp 从笔记本电脑传输：
# 在笔记本电脑上执行：
scp ~/m20-patrol-deploy.tar.gz user@10.21.31.104:/home/user/m20-patrol-robot/
```

#### 方式三：U 盘传输

1. 将 `m20-patrol-deploy.tar.gz` 复制到 U 盘
2. 插入 GOS 主机（如果有 USB 接口）
3. 在 GOS 上挂载并解压：
   ```bash
   mount /dev/sda1 /mnt
   cp /mnt/m20-patrol-deploy.tar.gz ~/m20-patrol-robot/
   umount /mnt
   cd ~/m20-patrol-robot
   tar -xzf m20-patrol-deploy.tar.gz
   ```

### 3.3 解压与验证

```bash
# 进入目标目录
cd ~/m20-patrol-robot

# 解压
tar -xzf m20-patrol-deploy.tar.gz

# 验证文件结构
ls -la
ls -la backend/app/
ls -la deploy/scripts/

# 检查 Python 环境
python3 --version
python3 -m venv --help  # 确认 venv 可用

# 检查 systemd
systemctl --user --version
```

---

## 四、GOS 安装步骤

### 4.1 创建虚拟环境

```bash
cd ~/m20-patrol-robot

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖（如有 requirements.txt）
# pip install -r requirements.txt

# 验证
python3 -c "import backend; print('import ok')"
```

### 4.2 运行安装脚本

```bash
# 使用安装脚本
bash deploy/scripts/install-gos.sh \
  --repo "$PWD" \
  --ref $(git rev-parse HEAD 2>/dev/null || echo "manual")

# 或者手动安装（如果没有 git）
# 直接复制文件到目标位置
mkdir -p ~/.local/share/m20-patrol-robot/releases/manual
cp -r . ~/.local/share/m20-patrol-robot/releases/manual/
ln -sfn ~/.local/share/m20-patrol-robot/releases/manual \
        ~/.local/share/m20-patrol-robot/current
```

### 4.3 启动服务

```bash
# 启动模拟只读模式
systemctl --user start m20-patrol-readonly.service

# 或启动真实状态订阅模式
systemctl --user start m20-patrol-realtime.service

# 查看状态
systemctl --user status m20-patrol-realtime.service --no-pager
```

### 4.4 验证运行

```bash
# 检查 API
curl -fsS http://127.0.0.1:8080/api/v1/status/latest

# 检查 Web 页面
curl -fsS http://127.0.0.1:8080/ | head -20

# 从笔记本访问（如网络互通）
# curl -fsS http://10.21.31.104:8080/api/v1/status/latest
```

---

## 五、版本验证

### 5.1 固件版本确认

```bash
# 在 NOS 上执行（通过 GOS 跳转或直连）
ssh user@10.21.31.106 "cat /var/opt/robot/release_note.json"
```

预期输出包含：
```json
{
  "software_version": "V1.1.8",
  "firmware_version": "V1.1.8",
  "aos_version": "...",
  "nos_version": "...",
  "gos_version": "..."
}
```

### 5.2 程序版本确认

```bash
# 检查部署的 commit
cat ~/.local/share/m20-patrol-robot/current/.git/COMMIT_SHA 2>/dev/null

# 或检查代码版本
grep -r "version" backend/app/__init__.py 2>/dev/null || echo "无版本文件"
```

### 5.3 协议对齐确认

代码依据 V1.2.1 开发手册（2026-05-18）：
- ✅ 16 字节 APDU 帧头（EB 91 EB 90）
- ✅ Gait 值 0x3002（平地敏捷）
- ✅ 26 个导航错误码映射
- ✅ 1007/3 导航异常主动上报（≥V1.1.8）
- ✅ BatteryList 数组解析

---

## 六、常见故障处理

### 6.1 文件传输失败

```bash
# 检查磁盘空间
df -h ~/

# 检查权限
ls -la ~/m20-patrol-deploy.tar.gz

# 重新传输
# 在笔记本电脑上：
scp ~/m20-patrol-deploy.tar.gz user@10.21.31.104:/home/user/
```

### 6.2 解压失败

```bash
# 检查压缩包完整性
tar -tzf m20-patrol-deploy.tar.gz | head -20

# 重新解压
rm -rf backend/ deploy/
tar -xzf m20-patrol-deploy.tar.gz
```

### 6.3 服务启动失败

```bash
# 查看详细日志
journalctl --user -u m20-patrol-realtime -n 50 --no-pager

# 检查端口占用
netstat -tlnp | grep 8080

# 检查 Python 环境
ls -la .venv/bin/python
```

---

## 七、轻量化部署建议

### 7.1 最小部署包（约 600KB）

```bash
# 创建最小部署包
cd /path/to/m20-patrol-robot
tar -czf m20-patrol-minimal.tar.gz \
  backend/app/ \
  deploy/scripts/ \
  deploy/systemd/ \
  --exclude='*/__pycache__' \
  --exclude='*.pyc'

# 验证大小
ls -lh m20-patrol-minimal.tar.gz
```

### 7.2 完整部署包（约 14MB）

```bash
# 完整包（包含文档和测试）
tar -czf m20-patrol-complete.tar.gz .
```

### 7.3 推荐传输策略

| 场景 | 推荐包 | 大小 | 说明 |
|---|---|---|---|
| 仅部署运行 | minimal.tar.gz | ~600KB | 最快传输 |
| 需要查看文档 | complete.tar.gz | ~14MB | 包含所有文档 |
| 首次部署 | complete.tar.gz | ~14MB | 便于后续维护 |

---

## 八、安全提醒

- 导航控制启用前必须获得书面放行
- 程序默认 `control_enabled=false`，无法绕过
- 所有控制操作记录审计日志
- 异常情况立即停止服务并回滚
