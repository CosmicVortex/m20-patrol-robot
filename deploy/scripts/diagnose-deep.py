#!/usr/bin/env python3
"""
M20 Pro 深度诊断脚本 - 在GOS主机上运行
分析TCP连接和数据接收的完整流程
"""

import sys
import socket
import time
import json
import struct
from datetime import datetime

AOS_HOST = "10.21.31.103"
AOS_PORT = 30001
TIMEOUT = 5

def test_tcp_connection():
    """测试TCP连接"""
    print("=" * 60)
    print("【1. TCP连接测试】")
    print("=" * 60)
    
    try:
        sock = socket.create_connection((AOS_HOST, AOS_PORT), timeout=TIMEOUT)
        print(f"✓ TCP连接成功: {AOS_HOST}:{AOS_PORT}")
        sock.settimeout(2)
        return sock
    except socket.timeout:
        print(f"✗ 连接超时 ({TIMEOUT}s)")
        return None
    except ConnectionRefusedError:
        print(f"✗ 连接被拒绝 - 端口未开放或服务未运行")
        return None
    except Exception as e:
        print(f"✗ 连接失败: {type(e).__name__}: {e}")
        return None

def send_heartbeat_and_receive(sock):
    """发送心跳并接收数据"""
    print("\n" + "=" * 60)
    print("【2. 心跳发送与数据接收测试】")
    print("=" * 60)
    
    # 构建心跳包
    heartbeat = {
        "PatrolDevice": {
            "Type": 100,
            "Command": 100,
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Items": {}
        }
    }
    
    payload = json.dumps(heartbeat, separators=(',', ':')).encode('utf-8')
    
    # APDU头部: 16字节
    # 同步字符: 0xEB 0x91 0xEB 0x90
    # 长度: 2字节小端 (ASDU长度，不包含头部)
    # 报文ID: 2字节小端
    # 格式: 1字节 (0x01=JSON)
    # 预留: 7字节
    
    msg_id = 1
    flags = 0x01  # JSON格式
    length = len(payload)
    
    header = bytearray()
    header.extend(b'\xeb\x91\xeb\x90')  # 同步字符
    header.extend(struct.pack('<H', length))  # 长度（小端）
    header.extend(struct.pack('<H', msg_id))   # 报文ID（小端）
    header.append(flags)                         # 格式
    header.extend(b'\x00' * 7)                  # 预留
    
    frame = bytes(header) + payload
    
    print(f"发送心跳包: {len(frame)} 字节")
    print(f"  头部: {header.hex()}")
    print(f"  Payload: {payload.decode()[:100]}...")
    
    try:
        sock.sendall(frame)
        print("✓ 心跳已发送")
    except Exception as e:
        print(f"✗ 发送失败: {e}")
        return False
    
    # 等待响应（3秒）
    print("\n等待AOS响应（3秒）...")
    sock.settimeout(3)
    
    received_data = bytearray()
    start_time = time.time()
    
    while time.time() - start_time < 3:
        try:
            data = sock.recv(4096)
            if data:
                received_data.extend(data)
                print(f"✓ 收到 {len(data)} 字节 (累计: {len(received_data)} 字节)")
        except socket.timeout:
            break
    
    if len(received_data) == 0:
        print("✗ 未收到任何响应")
        return False
    
    print(f"\n完整接收: {len(received_data)} 字节")
    
    # 解析APDU帧
    print("\n【3. 协议帧解析】")
    print("=" * 60)
    
    if len(received_data) < 16:
        print(f"✗ 数据不足16字节（头部长度）")
        return False
    
    # 解析头部
    sync = received_data[:4]
    length = struct.unpack('<H', received_data[4:6])[0]
    msg_id = struct.unpack('<H', received_data[6:8])[0]
    flags = received_data[8]
    
    print(f"同步字符: {sync.hex()} {'✓' if sync == b'\\xeb\\x91\\xeb\\x90' else '✗'}")
    print(f"ASDU长度: {length}")
    print(f"报文ID: {msg_id}")
    print(f"格式: {flags} {'(JSON)' if flags == 1 else '(XML)'}")
    
    # 检查长度一致性
    expected_total = 16 + length
    if len(received_data) < expected_total:
        print(f"✗ 数据不完整（期望{expected_total}字节，实际{len(received_data)}字节）")
        return False
    
    # 解析ASDU
    asdu_json = received_data[16:16+length].decode('utf-8', errors='replace')
    print(f"\nASDU内容:\n{asdu_json[:500]}...")
    
    try:
        asdu = json.loads(asdu_json)
        device = asdu.get('PatrolDevice', {})
        print(f"\n解析结果:")
        print(f"  Type: {device.get('Type')}")
        print(f"  Command: {device.get('Command')}")
        print(f"  Time: {device.get('Time')}")
        
        # 检查是否心跳响应
        if device.get('Type') == 100 and device.get('Command') == 100:
            print("\n✓ 收到心跳响应")
            return True
        else:
            print(f"\n! 收到的是 Type={device.get('Type')}, Command={device.get('Command')}")
            return True
            
    except json.JSONDecodeError as e:
        print(f"✗ JSON解析失败: {e}")
        return False

def receive_pushed_data(sock, duration=5):
    """接收主动推送数据"""
    print("\n" + "=" * 60)
    print(f"【4. 主动数据推送测试（{duration}秒）】")
    print("=" * 60)
    
    sock.settimeout(1)
    messages = []
    start_time = time.time()
    
    while time.time() - start_time < duration:
        try:
            data = sock.recv(4096)
            if data:
                # 解析并记录
                if len(data) >= 16:
                    try:
                        asdu_len = struct.unpack('<H', data[4:6])[0]
                        asdu_json = data[16:16+asdu_len].decode('utf-8')
                        asdu = json.loads(asdu_json)
                        device = asdu.get('PatrolDevice', {})
                        msg_type = device.get('Type')
                        cmd = device.get('Command')
                        messages.append({'type': msg_type, 'cmd': cmd, 'time': datetime.now().strftime('%H:%M:%S')})
                        print(f"  [{len(messages)}] Type={msg_type}, Command={cmd}")
                    except:
                        pass
        except socket.timeout:
            continue
    
    print(f"\n共收到 {len(messages)} 条消息")
    return len(messages) > 0

def main():
    print("\n" + "╔" + "=" * 58 + "╗")
    print("║        M20 Pro 深度诊断工具                        ║")
    print("╚" + "=" * 58 + "╝")
    print(f"\n目标: {AOS_HOST}:{AOS_PORT}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试TCP连接
    sock = test_tcp_connection()
    if not sock:
        print("\n无法建立TCP连接，请检查:")
        print("  1. AOS主机是否开机")
        print("  2. IP地址是否正确 (10.21.31.103)")
        print("  3. 网络连接是否正常")
        return 1
    
    # 发送心跳并测试响应
    success = send_heartbeat_and_receive(sock)
    
    # 测试主动推送
    if success:
        has_pushed = receive_pushed_data(sock, duration=3)
        if not has_pushed:
            print("\n⚠ 警告: 心跳响应正常但未收到主动推送数据")
            print("可能原因:")
            print("  1. AOS未配置向GOS IP推送数据")
            print("  2. 需要订阅特定消息类型")
            print("  3. AOS服务异常")
    
    sock.close()
    
    print("\n" + "=" * 60)
    print("【诊断完成】")
    print("=" * 60)
    
    if success:
        print("✓ TCP连接和心跳响应正常")
        print("  如果仍然无数据，请检查:")
        print("  1. 服务日志: journalctl --user -u m20-patrol-readonly.service -f")
        print("  2. 健康状态: curl http://127.0.0.1:8080/api/v1/health")
        return 0
    else:
        print("✗ 诊断发现问题，请检查上述输出")
        return 1

if __name__ == '__main__':
    sys.exit(main())
