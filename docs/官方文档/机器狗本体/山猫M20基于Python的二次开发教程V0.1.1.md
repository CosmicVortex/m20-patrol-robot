# 山猫 M20 基于 Python 的二次开发教程

**版本号：** V0.1.1  
**更新日期：** 2025-12-24  
**适用型号：** 山猫 M20、山猫 M20 Pro  
**适用软件包版本：** V1.1.7 及以后

---

## 运行代码

### Linux 端（Ubuntu 为例）

**步骤 1：将附录中的代码保存为 Python 脚本**

```bash
sudo vim udp_demo.py
```

**步骤 2：运行 Python 脚本**

确保已安装 Python 3（一般 Ubuntu/Windows 都预装了）：

```bash
sudo python3 udp_demo.py
```

你应该会看到类似输出：

**UDP 协议：**
```
消息发送成功！
```

**TCP 协议：**
```
正在连接到服务器 10.21.31.103:30001...
消息发送成功！
TCP 连接已关闭
```

### Windows 端

**步骤 1：在本地创建并编辑 py 文件**

使用你喜欢的编辑器（VS Code、Notepad++ 等）创建 `udp_demo.py`。

**步骤 2：进入终端**

按 Win + R，输入 `cmd` 回车（或搜索"命令提示符" / "PowerShell"）。

**步骤 3：切换到 py 文件所在目录并执行代码**

```bash
python3 udp_demo.py
```

---

## 编辑代码

附录示例代码中，协议头部分（16 字节）为固定格式，无需修改。开发者仅需根据实际业务需求调整 **ASDU 数据内容**（即 JSON 或 XML 内容），其余协议头字段已按规范封装，保持不变。

```python
# 只需替换此处的 json_data 即可发送不同指令
json_data = """
{
    "PatrolDevice": {
        "Type": 100,
        "Command": 100,
        "Time": "2023-01-01 00:00:00",
        "Items": {}
    }
}
"""
```

> **具体 ASDU 格式参考《软件开发指南》**

### 示例：控制山猫 M20 站立

如果想要编辑一段可以控制山猫 M20 站立的代码，则只需要将上述 JSON 更换为如下内容：

```python
# 控制山猫 M20 的运动状态为站立
json_data = """
{
 "PatrolDevice": {
  "Type": 2,
  "Command": 22,
  "Time": "2023-01-01 00:00:00",
  "Items": {
    "MotionParam": 1
  }
 }
}
"""
```

---

## 附录

### UDP 示例代码

```python
import socket

# =============================================
# 1. 协议头构造函数
# =============================================
def build_protocol_header(data_length: int, msg_id: int = 1, asdu_format: int = 0x01) -> bytearray:
    if not (0 <= data_length <= 65535):
        raise ValueError("data_length 必须在 0 ~ 65535 之间")
    if not (0 <= msg_id <= 65535):
        raise ValueError("msg_id 必须在 0 ~ 65535 之间")
    if asdu_format not in [0x00, 0x01]:
        raise ValueError("asdu_format 必须是 0x00（XML）或 0x01（JSON）")

    header = bytearray(16)
    header[0] = 0xeb
    header[1] = 0x91
    header[2] = 0xeb
    header[3] = 0x90
    header[4] = data_length & 0xFF
    header[5] = (data_length >> 8) & 0xFF
    header[6] = msg_id & 0xFF
    header[7] = (msg_id >> 8) & 0xFF
    header[8] = asdu_format  # 0x01 表示 JSON

    # 8~14 字节：预留 7 字节，已经默认是 0，无需设置

    return header

# =============================================
# 2. 基础配置
# =============================================
SERVER_IP = "10.21.31.103"  # 目标服务器 IP
PORT = 30000                # 目标端口

# =============================================
# 3. 构造 JSON 数据
# =============================================
json_data = """
{
    "PatrolDevice":{
        "Type":100,
         "Command":100,
         "Time":"2023-01-01 00:00:00",
         "Items":{
         }
     }
}
"""

# 转为 UTF-8 bytes，并计算长度（即 ASDU 长度）
asdu_data = json_data.encode('utf-8')
data_length = len(asdu_data)  # 用于协议头中的长度字段

# =============================================
# 4. 构造协议头
#    - 报文ID 示例为 1
#    - ASDU格式为 JSON（0x01）
# =============================================
header = build_protocol_header(
    data_length=data_length,
    msg_id=1,          # 可以设为变量，每次递增
    asdu_format=0x01   # 0x01 表示 JSON
)

# =============================================
# 5. 拼接完整消息：header + asdu_data（JSON）
# =============================================
message = header + asdu_data

# =============================================
# 6. 创建 UDP 套接字并发送
# =============================================
try:
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (SERVER_IP, PORT)

    send_len = client_sock.sendto(message, server_address)
    print(f"消息发送成功！")

except Exception as e:
    print(f"发送失败：{e}")

finally:
    client_sock.close()
```

### TCP 示例代码

```python
import socket

# =============================================
# 1. 协议头构造函数
# =============================================
def build_protocol_header(data_length: int, msg_id: int = 1, asdu_format: int = 0x01) -> bytearray:
    if not (0 <= data_length <= 65535):
        raise ValueError("data_length 必须在 0 ~ 65535 之间")
    if not (0 <= msg_id <= 65535):
        raise ValueError("msg_id 必须在 0 ~ 65535 之间")
    if asdu_format not in [0x00, 0x01]:
        raise ValueError("asdu_format 必须是 0x00（XML）或 0x01（JSON）")

    header = bytearray(16)
    header[0] = 0xeb
    header[1] = 0x91
    header[2] = 0xeb
    header[3] = 0x90
    header[4] = data_length & 0xFF
    header[5] = (data_length >> 8) & 0xFF
    header[6] = msg_id & 0xFF
    header[7] = (msg_id >> 8) & 0xFF
    header[8] = asdu_format  # 0x01 表示 JSON

    # 8~14 字节：预留 7 字节，默认 0，无需设置
    return header

# =============================================
# 2. 基础配置（IP 和端口）
# =============================================
SERVER_IP = "10.21.31.103"  # 目标服务器 IP
PORT = 30001                # 目标端口（确保服务端是 TCP 监听！）

# =============================================
# 3. 构造 JSON 数据
# =============================================
json_data = """
{
    "PatrolDevice":{
        "Type":100,
        "Command":100,
        "Time":"2023-01-01 00:00:00",
        "Items":{
        }
    }
}
"""

# 转为 UTF-8 bytes，并计算长度（ASDU 长度）
asdu_data = json_data.encode('utf-8')
data_length = len(asdu_data)  # 用于协议头中的长度字段

# =============================================
# 4. 构造协议头
# =============================================
header = build_protocol_header(
    data_length=data_length,
    msg_id=1,          # 可自定义，比如递增
    asdu_format=0x01   # 0x01 表示 JSON 格式
)

# =============================================
# 5. 拼接完整消息：header + asdu_data
# =============================================
message = header + asdu_data

# =============================================
# 6. 创建 TCP 套接字并发送
# =============================================
try:
    # 创建 TCP 套接字（注意：不再是 SOCK_DGRAM，而是 SOCK_STREAM）
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 连接到服务器
    server_address = (SERVER_IP, PORT)
    print(f"正在连接到服务器 {SERVER_IP}:{PORT}...")
    client_sock.connect(server_address)

    # 发送完整消息（TCP 使用 sendall，确保全部发送）
    send_len = client_sock.sendall(message)
    # 注意：sendall() 没有返回值，它要么全部发送成功，要么抛异常
    print(f"消息发送成功！")

except Exception as e:
    print(f"发送失败：{e}")

finally:
    # 关闭套接字
    client_sock.close()
    print("TCP 连接已关闭")
```

### 用 tcpdump 抓取 UDP 包

如代码运行后不确定是否收到数据，可以直接在 Ubuntu 中使用 tcpdump 抓取自己发出的 UDP 包：

```bash
sudo tcpdump -i any udp port 30000 -vvv -X
```

| 参数 | 说明 |
|---|---|
| `-i any` | 监听所有网卡 |
| `udp port 30000` | 只抓目标端口 30000 的 UDP 包 |
| `-vvv` | 更详细输出 |
| `-X` | 以 Hex + ASCII 格式同时显示包内容 |

这样就可以在终端直接看到发送的 UDP 数据内容。

---

## 注意事项

1. **目标服务器（即山猫 M20 运动主机）必须存在并监听 UDP 30000 或 TCP 30001 端口。**
2. 如运行程序后未预期输出，请检查：
   - 代码中配置的 `SERVER_IP` 是否填写正确
   - 山猫 M20 运动主机中对应端口确实被监听
   - 客户端与山猫 M20 运动主机通信正常（比如在同一局域网下，且防火墙未阻隔）
3. 协议头部分（16 字节）为固定格式，无需修改。
4. 仅需根据实际业务需求调整 ASDU 数据内容（即 JSON 或 XML 内容）。

---

## 相关资源

- [basic_server 通信协议总览](./basic-server-protocol-overview.md)
- [运动控制（basic_server 协议）](./motion-control-basic-server.md)
- [基于 C++ 的二次开发教程](./cpp-tutorial.md)
- [软件开发指南 V1.2.1](../V1.2.1.md)

---

**版本号：** V0.1.1  
**更新日期：** 2025-12-24  
**版权归属：** 杭州云深处科技
