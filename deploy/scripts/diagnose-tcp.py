#!/usr/bin/env python3
"""
M20 Pro TCP连接诊断工具
在GOS主机上运行此脚本诊断TCP连接问题
"""

import sys
import socket
import time
import json
from datetime import datetime

AOS_HOST = "10.21.31.103"
AOS_PORT = 30001
TIMEOUT = 5

def check_network():
    """检查网络连通性"""
    print("=" * 60)
    print("【网络连通性检查】")
    print("=" * 60)
    
    # 1. Ping测试
    print(f"\n1. Ping测试: {AOS_HOST}")
    try:
        start = time.time()
        socket.create_connection((AOS_HOST, AOS_PORT), timeout=TIMEOUT)
        elapsed = time.time() - start
        print(f"   ✓ TCP连接成功 (耗时: {elapsed:.2f}s)")
        return True
    except socket.timeout:
        print(f"   ✗ 连接超时 ({TIMEOUT}s)")
        return False
    except ConnectionRefusedError:
        print(f"   ✗ 连接被拒绝 - 端口未开放或服务未运行")
        return False
    except Exception as e:
        print(f"   ✗ 连接失败: {type(e).__name__}: {e}")
        return False

def test_tcp_port():
    """测试TCP端口"""
    print("\n" + "=" * 60)
    print("【TCP端口测试】")
    print("=" * 60)
    
    ports = [30001, 30000, 8080, 80]
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((AOS_HOST, port))
            if result == 0:
                print(f"   ✓ 端口 {port}: 开放")
            else:
                print(f"   ✗ 端口 {port}: 关闭 (错误码: {result})")
            sock.close()
        except Exception as e:
            print(f"   ? 端口 {port}: 测试失败 ({e})")

def send_heartbeat():
    """发送心跳并接收响应"""
    print("\n" + "=" * 60)
    print("【心跳测试】")
    print("=" * 60)
    
    try:
        sock = socket.create_connection((AOS_HOST, AOS_PORT), timeout=TIMEOUT)
        sock.settimeout(5)
        print(f"   ✓ TCP连接成功")
        
        # 构建心跳包
        heartbeat = {
            "PatrolDevice": {
                "Type": 100,
                "Command": 100,
                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Items": {}
            }
        }
        
        # APDU头部: 同步字符(4) + 长度(2) + 报文ID(2) + 格式(1) + 预留(7)
        payload = json.dumps(heartbeat).encode('utf-8')
        msg_id = 1
        flags = 0x01  # JSON格式
        
        # 计算长度（小端）
        length = len(payload)
        
        # 构建完整帧
        header = bytes([0xEB, 0x91, 0xEB, 0x90])  # 同步字符
        header += length.to_bytes(2, 'little')      # 长度
        header += msg_id.to_bytes(2, 'little')      # 报文ID
        header += bytes([flags])                     # 格式
        header += bytes(7)                           # 预留
        
        frame = header + payload
        print(f"   发送心跳包: {len(frame)} 字节")
        
        # 发送
        sock.sendall(frame)
        print(f"   ✓ 心跳已发送")
        
        # 接收响应
        print(f"   等待响应...")
        sock.settimeout(3)
        try:
            data = sock.recv(4096)
            if data:
                print(f"   ✓ 收到响应: {len(data)} 字节")
                print(f"   响应内容: {data[:200].decode('utf-8', errors='replace')}...")
            else:
                print(f"   ! 无响应数据")
        except socket.timeout:
            print(f"   ! 响应超时（可能AOS不回应心跳，但会继续推送数据）")
        
        # 继续接收主动推送数据
        print(f"   继续监听数据...")
        sock.settimeout(5)
        received = 0
        start = time.time()
        while time.time() - start < 5:
            try:
                data = sock.recv(4096)
                if data:
                    received += len(data)
                    print(f"   ✓ 收到 {len(data)} 字节 (总计: {received} 字节)")
                    # 尝试解析
                    try:
                        text = data.decode('utf-8', errors='replace')
                        if 'PatrolDevice' in text:
                            print(f"   内容预览: {text[:300]}...")
                    except:
                        pass
            except socket.timeout:
                break
        
        print(f"\n   统计: 接收 {received} 字节")
        sock.close()
        
        if received > 0:
            print("   ✓ 数据接收正常")
            return True
        else:
            print("   ✗ 未接收到任何数据")
            return False
            
    except Exception as e:
        print(f"   ✗ 测试失败: {type(e).__name__}: {e}")
        return False

def check_service():
    """检查本地服务状态"""
    print("\n" + "=" * 60)
    print("【本地服务状态】")
    print("=" * 60)
    
    # 检查Python进程
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'backend.app.server'], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"   ✓ Python服务运行中 (PID: {result.stdout.strip()})")
    else:
        print(f"   ✗ Python服务未运行")
    
    # 检查端口监听
    result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
    if ':8080' in result.stdout:
        print(f"   ✓ 8080端口监听中")
    else:
        print(f"   ✗ 8080端口未监听")
    
    # API健康检查
    try:
        import urllib.request
        with urllib.request.urlopen('http://127.0.0.1:8080/api/v1/health', timeout=3) as resp:
            data = json.loads(resp.read().decode())
            print(f"   健康状态: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"   ✗ API检查失败: {e}")

def main():
    print("\n" + "╔" + "=" * 58 + "╗")
    print("║        M20 Pro TCP连接诊断工具                      ║")
    print("╚" + "=" * 58 + "╝")
    print(f"\n目标: {AOS_HOST}:{AOS_PORT}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 执行测试
    connected = check_network()
    
    if not connected:
        print("\n" + "=" * 60)
        print("【诊断结论】")
        print("=" * 60)
        print("TCP连接失败，无法接收数据。")
        print("\n可能原因:")
        print("  1. AOS主机未开机或网络断开")
        print("  2. AOS IP地址已变更（当前配置: 10.21.31.103）")
        print("  3. 防火墙阻止TCP 30001端口")
        print("  4. AOS basic_server服务未运行")
        print("\n建议操作:")
        print("  1. 检查机器狗主机是否开机")
        print("  2. 确认AOS IP地址（查看主机屏幕或路由器DHCP表）")
        print("  3. 如IP变更，更新 deploy/readonly-manifest.json")
        print("  4. 重启服务: systemctl --user restart m20-patrol-readonly.service")
        return 1
    
    # 继续测试
    test_tcp_port()
    data_received = send_heartbeat()
    check_service()
    
    print("\n" + "=" * 60)
    print("【最终结论】")
    print("=" * 60)
    
    if data_received:
        print("✓ TCP连接正常，数据接收正常")
        print("  请检查服务日志确认数据解析:")
        print("  journalctl --user -u m20-patrol-readonly.service -f")
        return 0
    else:
        print("✗ TCP连接成功但无数据")
        print("  可能原因:")
        print("  1. AOS未配置推送数据到GOS IP")
        print("  2. 心跳格式不正确")
        print("  3. AOS服务异常")
        return 1

if __name__ == '__main__':
    sys.exit(main())
