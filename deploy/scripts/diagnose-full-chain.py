#!/usr/bin/env python3
"""
M20 Pro 全链路诊断工具
测试从TCP连接到前端显示的完整数据流
"""

import sys
import socket
import struct
import json
import time
from datetime import datetime

class FullChainDiagnostic:
    def __init__(self, aos_host="10.21.31.103", aos_port=30001):
        self.aos_host = aos_host
        self.aos_port = aos_port
        self.results = {}
        
    def test_tcp_connection(self):
        """测试TCP连接"""
        print("\n" + "="*60)
        print("【1. TCP连接测试】")
        print("="*60)
        
        try:
            sock = socket.create_connection((self.aos_host, self.aos_port), timeout=5)
            sock.settimeout(2)
            print(f"✓ TCP连接成功: {self.aos_host}:{self.aos_port}")
            self.results['tcp'] = True
            return sock
        except Exception as e:
            print(f"✗ TCP连接失败: {e}")
            self.results['tcp'] = False
            return None
    
    def test_heartbeat(self, sock):
        """测试心跳发送和响应"""
        print("\n" + "="*60)
        print("【2. 心跳测试】")
        print("="*60)
        
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
        
        # APDU头部
        header = bytearray()
        header.extend(b'\xeb\x91\xeb\x90')  # 同步字符
        header.extend(struct.pack('<H', len(payload)))  # 长度
        header.extend(struct.pack('<H', 1))   # 报文ID
        header.append(0x01)                    # 格式(JSON)
        header.extend(b'\x00' * 7)            # 预留
        
        frame = bytes(header) + payload
        
        try:
            sock.sendall(frame)
            print(f"✓ 心跳已发送 ({len(frame)} 字节)")
            self.results['heartbeat_sent'] = True
        except Exception as e:
            print(f"✗ 心跳发送失败: {e}")
            self.results['heartbeat_sent'] = False
            return False
        
        # 等待响应
        print("等待AOS响应...")
        try:
            data = sock.recv(4096)
            if data:
                print(f"✓ 收到响应: {len(data)} 字节")
                self.results['heartbeat_response'] = True
                
                # 解析响应
                if len(data) >= 16:
                    sync = data[:4]
                    length = struct.unpack('<H', data[4:6])[0]
                    flags = data[8]
                    print(f"  同步字符: {sync.hex()} {'✓' if sync == b'\\xeb\\x91\\xeb\\x90' else '✗'}")
                    print(f"  ASDU长度: {length}")
                    print(f"  格式: {flags} {'(JSON)' if flags == 1 else '(XML)'}")
                    
                    if length > 0 and len(data) >= 16 + length:
                        asdu_json = data[16:16+length].decode('utf-8', errors='replace')
                        print(f"  ASDU内容: {asdu_json[:200]}...")
                        try:
                            asdu = json.loads(asdu_json)
                            device = asdu.get('PatrolDevice', {})
                            print(f"  Type: {device.get('Type')}, Command: {device.get('Command')}")
                        except:
                            pass
                return True
            else:
                print("! 无响应数据（AOS可能不回应心跳，但会推送数据）")
                self.results['heartbeat_response'] = None
                return True  # 非阻断
        except socket.timeout:
            print("! 响应超时（正常，AOS可能异步推送数据）")
            self.results['heartbeat_response'] = None
            return True
    
    def test_data_push(self, sock, duration=5):
        """测试数据主动推送"""
        print("\n" + "="*60)
        print(f"【3. 数据推送测试（{duration}秒）】")
        print("="*60)
        
        sock.settimeout(1)
        messages = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                data = sock.recv(4096)
                if data:
                    # 解析APDU帧
                    if len(data) >= 16:
                        try:
                            length = struct.unpack('<H', data[4:6])[0]
                            flags = data[8]
                            asdu_json = data[16:16+length].decode('utf-8', errors='replace')
                            asdu = json.loads(asdu_json)
                            device = asdu.get('PatrolDevice', {})
                            msg_type = device.get('Type')
                            cmd = device.get('Command')
                            messages.append({
                                'type': msg_type,
                                'cmd': cmd,
                                'time': datetime.now().strftime('%H:%M:%S')
                            })
                            print(f"  [{len(messages)}] Type={msg_type}, Command={cmd}")
                        except Exception as e:
                            print(f"  ! 解析错误: {e}")
            except socket.timeout:
                continue
        
        print(f"\n共收到 {len(messages)} 条消息")
        self.results['data_push'] = len(messages) > 0
        return len(messages) > 0
    
    def test_api_endpoint(self):
        """测试API端点"""
        print("\n" + "="*60)
        print("【4. API端点测试】")
        print("="*60)
        
        endpoints = [
            '/api/v1/health',
            '/api/v1/status/latest',
            '/api/v1/devices',
        ]
        
        for endpoint in endpoints:
            try:
                url = f'http://127.0.0.1:8080{endpoint}'
                sock = socket.create_connection(('127.0.0.1', 8080), timeout=3)
                request = f'GET {endpoint} HTTP/1.1\r\nHost: 127.0.0.1:8080\r\nConnection: close\r\n\r\n'
                sock.sendall(request.encode())
                
                response = b''
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                sock.close()
                
                # 解析响应
                parts = response.decode('utf-8', errors='replace').split('\r\n\r\n', 1)
                status_line = parts[0].split('\r\n')[0] if parts else ''
                body = parts[1] if len(parts) > 1 else ''
                
                print(f"  {endpoint}: {status_line}")
                if '200' in status_line:
                    try:
                        data = json.loads(body)
                        if endpoint == '/api/v1/health':
                            print(f"    healthy: {data.get('healthy')}")
                            print(f"    source: {data.get('source')}")
                            print(f"    connected: {data.get('connected')}")
                            print(f"    valid_frames: {data.get('valid_frames')}")
                            print(f"    bytes_received: {data.get('bytes_received')}")
                        elif endpoint == '/api/v1/status/latest':
                            print(f"    source: {data.get('source')}")
                            print(f"    connected: {data.get('connected')}")
                            print(f"    data keys: {list(data.get('data', {}).keys())}")
                    except:
                        pass
                self.results[endpoint] = '200' in status_line
            except Exception as e:
                print(f"  {endpoint}: 错误 - {e}")
                self.results[endpoint] = False
    
    def run(self):
        """运行完整诊断"""
        print("\n" + "╔" + "="*58 + "╗")
        print("║        M20 Pro 全链路诊断工具                      ║")
        print("╚" + "="*58 + "╝")
        print(f"\n目标: {self.aos_host}:{self.aos_port}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. TCP连接测试
        sock = self.test_tcp_connection()
        
        if not sock:
            print("\n" + "="*60)
            print("【诊断结论】TCP连接失败，无法继续")
            print("="*60)
            print("\n可能原因:")
            print("  1. AOS主机未开机")
            print("  2. IP地址已变更")
            print("  3. 防火墙阻止连接")
            print("  4. 网络断开")
            return 1
        
        # 2. 心跳测试
        self.test_heartbeat(sock)
        
        # 3. 数据推送测试
        self.test_data_push(sock, duration=3)
        
        # 4. API测试
        self.test_api_endpoint()
        
        sock.close()
        
        # 总结
        print("\n" + "="*60)
        print("【诊断总结】")
        print("="*60)
        
        issues = []
        if not self.results.get('tcp'):
            issues.append("TCP连接失败")
        if self.results.get('heartbeat_sent') and not self.results.get('heartbeat_response'):
            issues.append("心跳无响应（可能正常，AOS不回应心跳）")
        if not self.results.get('data_push'):
            issues.append("未收到主动推送数据")
        if not self.results.get('/api/v1/health'):
            issues.append("API端点不可访问")
        
        if not issues:
            print("✓ 所有检查通过")
            print("\n建议:")
            print("  1. 重启服务确认数据流:")
            print("     systemctl --user restart m20-patrol-readonly.service")
            print("  2. 查看实时日志:")
            print("     journalctl --user -u m20-patrol-readonly.service -f")
            return 0
        else:
            print("✗ 发现问题:")
            for issue in issues:
                print(f"  - {issue}")
            return 1

if __name__ == '__main__':
    diag = FullChainDiagnostic()
    sys.exit(diag.run())
