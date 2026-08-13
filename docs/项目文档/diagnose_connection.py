#!/usr/bin/env python3
"""M20 Pro 连接诊断工具 - 检查basic_server连接状态"""

import socket
import sys
import time
from datetime import datetime

def check_tcp_connection(host, port, timeout=3.0):
    """检查TCP连接"""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True, f"TCP {host}:{port} 可达"
    except socket.timeout:
        return False, f"TCP {host}:{port} 连接超时"
    except ConnectionRefusedError:
        return False, f"TCP {host}:{port} 连接被拒绝 (服务可能未运行)"
    except FileNotFoundError as e:
        return False, f"TCP {host}:{port} 网络错误: {e}"
    except Exception as e:
        return False, f"TCP {host}:{port} 未知错误: {type(e).__name__}: {e}"

def check_dns_resolution(host):
    """检查DNS解析"""
    try:
        ip = socket.gethostbyname(host)
        return True, f"{host} -> {ip}"
    except socket.gaierror as e:
        return False, f"DNS解析失败: {e}"

def ping_host(host, count=3):
    """检查ICMP连通性"""
    import subprocess
    try:
        result = subprocess.run(
            ['ping', '-c', str(count), '-W', '2', host],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # 提取延迟信息
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'rtt' in line or 'round-trip' in line:
                    return True, f"ICMP ping 成功: {line.strip()}"
            return True, "ICMP ping 成功"
        else:
            return False, f"ICMP ping 失败 (exit code {result.returncode})"
    except subprocess.TimeoutExpired:
        return False, "ICMP ping 超时"
    except FileNotFoundError:
        return False, "ping命令未找到"
    except Exception as e:
        return False, f"ICMP ping 错误: {type(e).__name__}: {e}"

def check_basic_server_protocol():
    """测试basic_server协议响应"""
    import json
    # 发送一个简单的Type=1007 Cmd=2位置查询
    # APDU头部: eb 91 eb 90 + 长度 + 报文ID + 格式 + 预留
    header = bytes([0xeb, 0x91, 0xeb, 0x90])
    # ASDU: {"PatrolDevice":{"Type":1007,"Command":2,"Time":"...","Items":{}}}
    asdu = json.dumps({
        "PatrolDevice": {
            "Type": 1007,
            "Command": 2,
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Items": {}
        }
    }, ensure_ascii=False).encode('utf-8')
    
    # 长度字段 (小端字节序)
    length = len(asdu).to_bytes(2, 'little')
    # 报文ID (小端字节序)
    msg_id = (1).to_bytes(2, 'little')
    # 格式: 0x01 = JSON
    format_byte = bytes([0x01])
    # 预留7字节
    reserved = bytes(7)
    
    apdu = header + length + msg_id + format_byte + reserved + asdu
    
    try:
        sock = socket.create_connection(('10.21.31.103', 30001), timeout=3.0)
        sock.settimeout(3.0)
        sock.sendall(apdu)
        
        # 尝试接收响应
        response = b''
        sock.settimeout(2.0)
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if len(response) >= 4:
                    # 检查同步字符
                    if response[:4] == header:
                        # 解析长度
                        data_len = int.from_bytes(response[4:6], 'little')
                        if len(response) >= 16 + data_len:
                            break
            except socket.timeout:
                break
        
        sock.close()
        
        if response:
            return True, f"收到 {len(response)} 字节响应"
        else:
            return False, "无响应 (basic_server可能不支持此查询或需先建立订阅)"
    except Exception as e:
        return False, f"协议测试失败: {type(e).__name__}: {e}"

def main():
    print("=" * 60)
    print("M20 Pro 连接诊断工具")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    # 1. 检查本地网络接口
    print("【1. 本地网络状态】")
    try:
        import subprocess
        result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
        print(result.stdout[:500])
    except Exception as e:
        print(f"获取网络信息失败: {e}")
    print()
    
    # 2. 检查AOS主机可达性
    aos_host = '10.21.31.103'
    print(f"【2. AOS主机 ({aos_host}) 连通性检查】")
    
    success, msg = ping_host(aos_host)
    print(f"  ICMP ping: {msg}")
    results.append(("ICMP to AOS", success))
    
    # 3. 检查basic_server TCP端口
    print(f"\n【3. basic_server TCP端口 (30001) 检查】")
    success, msg = check_tcp_connection(aos_host, 30001)
    print(f"  TCP 30001: {msg}")
    results.append(("TCP 30001", success))
    
    # 4. 检查UDP端口 (可选)
    print(f"\n【4. basic_server UDP端口 (30000) 检查】")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        sock.sendto(b'test', (aos_host, 30000))
        try:
            data, addr = sock.recvfrom(1024)
            print(f"  UDP 30000: 收到响应 ({len(data)} 字节)")
            results.append(("UDP 30000", True))
        except socket.timeout:
            print(f"  UDP 30000: 无响应 (可能正常，UDP是无连接的)")
            results.append(("UDP 30000", None))
        finally:
            sock.close()
    except Exception as e:
        print(f"  UDP 30000: 错误 - {type(e).__name__}: {e}")
        results.append(("UDP 30000", False))
    
    # 5. 检查basic_server服务状态 (通过SSH)
    print(f"\n【5. AOS服务状态检查】")
    try:
        result = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', 'root@10.21.31.103', 
             'systemctl is-active basic_server; ps aux | grep basic_server | grep -v grep'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.stdout.strip():
            print(f"  basic_server状态:\n{result.stdout}")
        else:
            print(f"  无法获取服务状态 (SSH失败或无输出)")
    except FileNotFoundError:
        print(f"  SSH命令未找到")
    except subprocess.TimeoutExpired:
        print(f"  SSH连接超时")
    except Exception as e:
        print(f"  SSH检查失败: {type(e).__name__}: {e}")
    
    # 6. 测试协议响应
    print(f"\n【6. basic_server协议测试】")
    success, msg = check_basic_server_protocol()
    print(f"  协议响应: {msg}")
    results.append(("Protocol Test", success))
    
    # 7. 总结
    print("\n" + "=" * 60)
    print("【诊断总结】")
    print("=" * 60)
    
    passed = sum(1 for _, s in results if s is True)
    failed = sum(1 for _, s in results if s is False)
    skipped = sum(1 for _, s in results if s is None)
    
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    print(f"  跳过: {skipped}")
    
    if failed > 0:
        print("\n⚠️  发现问题:")
        for name, success in results:
            if success is False:
                print(f"    - {name} 检查失败")
        print("\n建议:")
        print("    1. 检查AOS主机是否开机并运行")
        print("    2. 确认basic_server服务已启动 (systemctl status basic_server)")
        print("    3. 检查防火墙规则是否允许TCP 30001")
        print("    4. 确认GOS和AOS在同一网段 (10.21.31.x)")
    else:
        print("\n✅ 所有检查通过!")
    
    return failed == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
