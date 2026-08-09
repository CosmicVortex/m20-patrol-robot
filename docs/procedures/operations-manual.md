# 现场操作手册

本文档汇总 M20 Pro 机器狗现场操作的所有关键指令，按场景分类。

## 目录

1. [主机连接](#1-主机连接)
2. [版本确认](#2-版本确认)
3. [网络配置](#3-网络配置)
4. [建图操作](#4-建图操作)
5. [定位核验](#5-定位核验)
6. [状态监控](#6-状态监控)
7. [视频接入](#7-视频接入)
8. [故障排查](#8-故障排查)

---

## 1. 主机连接

### SSH 连接到 NOS（建图主机）

```bash
ssh user@13.21.31.106
```

**注意**：首次连接需确认主机密钥，密码由现场负责人提供，不得写入代码仓库。

### SSH 连接到 GOS（开发主机）

```bash
ssh user@10.21.31.104
```

### 端口信息

| 服务 | 协议 | 端口 | 说明 |
|------|------|------|------|
| basic_server | TCP | 30001 | 状态订阅、任务下发 |
| basic_server | UDP | 30000 | 高频速度指令 |
| RTSP | TCP | 8554 | 相机视频流 |
| Web HTTP | TCP | 8080 | 仪表盘访问 |

---

## 2. 版本确认

### 查询机器人固件版本

```bash
# 在 NOS 上执行
ssh user@13.21.31.106
cat /var/opt/robot/release_note.json
```

预期输出：
```json
{
  "software_version": "V1.1.8",
  "firmware_version": "V1.1.8",
  "aos_version": "...",
  "nos_version": "...",
  "gos_version": "..."
}
```

### 查询 APP 版本

在机器人 APP 中：设置 → 关于设备

记录：
- 机器人型号
- 系统版本
- APP 版本
- 测试时间
- 测试地点

---

## 3. 网络配置

### 确认主机身份

```bash
# 在 GOS 上执行
hostname
ip -brief address
```

### 测试网络连通性

```bash
# GOS 到 AOS
ping -c 3 10.21.31.103

# GOS 到 NOS
ping -c 3 13.21.31.106

# AOS basic_server 端口测试
nc -zv 10.21.31.103 30001
```

### 禁用旧地址

```bash
# 确认无旧地址引用
grep -r "10.21.31.101" . --include="*.py" --include="*.sh" --include="*.md"
```

---

## 4. 建图操作

### 4.1 建图前准备

**环境要求**：
- 机器人周围 2m 清空
- 两块电池安装且电量 > 20%
- 激光雷达无遮挡
- 无玻璃、冰面、湿滑区域

**安全确认**：
- [ ] 遥控器已连接
- [ ] 软急停可用
- [ ] 硬急停 accessible
- [ ] 操作员、安全观察员、现场负责人到位

### 4.2 启动建图

```bash
# 在 NOS 上执行
sudo drmap mapping -n <地图名称>
```

地图命名规范：`<场地>_map_<日期>`，例如 `site_a_20260809`

### 4.3 建图过程

- 先走小回环（3-5 圈），再走大回环
- 速度适中，避免急加速/急刹车
- 覆盖所有任务区域
- 等待终端显示 `Building map` 后再开始行走

### 4.4 结束建图

```bash
sudo drmap stop_mapping
```

等待终端明确显示建图结束。

### 4.5 地图备份

```bash
# 确认激活地图
readlink -f /var/opt/robot/data/maps/active

# 查看地图文件
find -L /var/opt/robot/data/maps/active -maxdepth 1 -type f

# 打包地图
drmap pack

# 记录 SHA-256
sha256sum /home/user/Downloads/*.zip
```

**重要**：每个场地必须记录独立的地图身份、生成时间、场地和整包 SHA-256。

---

## 5. 定位核验

### RViz 定位检查

```bash
# 在 NOS 图形会话中执行
su
source /opt/ros/foxy/setup.bash
export XAUTHORITY=/home/user/.Xauthority
rviz2
```

加载配置：`/opt/robot/share/localization/conf/localization.rviz`

**检查项**：
- 实时点云与激活地图重合
- 定位状态正常（无红色警告）
- 航向角与实际方向一致

**不重合时的处理**：
1. 选择 **2D Pose Estimate**
2. 在地图上点击机器人真实位置
3. 沿机头方向拖动箭头
4. 确认点云与地图重合

### APP 标点工具

1. APP → 设置 → 辅助功能 → 开启**标点工具**
2. 返回控制页面 → 点击**标点工具**
3. 移动机器人到目标位置
4. 点击**获取当前坐标**
5. 确认地图编号与激活地图一致
6. 保存点位

---

## 6. 状态监控

### 实时状态查询

```bash
# Web API 查询
curl -s http://10.21.31.104:8080/api/v1/status/latest

# 健康检查
curl -s http://10.21.31.104:8080/api/v1/health
```

### 状态判定标准

真实遥测必须满足：
```text
source=REAL
connected=true
valid_frames>0
message_parsed=true
status_accepted=true
age_ms < stale_after_seconds * 1000
```

### 系统服务状态

```bash
# 检查服务
systemctl --user status m20-patrol-readonly.service

# 查看日志
journalctl --user -u m20-patrol-readonly.service -n 50 --no-pager
```

---

## 7. 视频接入

### RTSP 地址

| 相机 | URL |
|------|-----|
| 前相机 | `rtsp://10.21.31.103:8554/video1` |
| 后相机 | `rtsp://10.21.31.103:8554/video2` |

### 测试视频流

```bash
# 检查 ffprobe 是否可用
command -v ffprobe

# 探测 RTSP 流
ffprobe rtsp://10.21.31.103:8554/video1

# 记录编码参数
# - 编码格式：H.264 或 H.265
# - 分辨率
# - 帧率
# - 码率
```

---

## 8. 故障排查

### 8.1 服务无法启动

```bash
# 检查 Python 版本
python3.8 --version

# 检查依赖
python3.8 -c 'import backend; print("IMPORT_OK")'

# 检查端口占用
ss -ltnup | grep 8080
```

### 8.2 遥测无数据

```bash
# 检查 TCP 连接
ss -tn | grep 10.21.31.103:30001

# 检查服务日志
journalctl --user -u m20-patrol-readonly.service -n 100 --no-pager
```

### 8.3 视频无响应

```bash
# 检查 RTSP 可达性
ffprobe rtsp://10.21.31.103:8554/video1

# 检查 FFmpeg
command -v ffmpeg
```

### 8.4 定位异常

1. 检查地图是否激活：`readlink -f /var/opt/robot/data/maps/active`
2. 检查点云重合：RViz 可视化
3. 重新估计位姿：2D Pose Estimate

---

## 附录：快速命令速查

| 任务 | 命令 |
|------|------|
| SSH 到 NOS | `ssh user@13.21.31.106` |
| SSH 到 GOS | `ssh user@10.21.31.104` |
| 查询固件版本 | `cat /var/opt/robot/release_note.json` |
| 启动建图 | `sudo drmap mapping -n <名称>` |
| 停止建图 | `sudo drmap stop_mapping` |
| 打包地图 | `drmap pack` |
| 计算地图哈希 | `sha256sum /home/user/Downloads/*.zip` |
| 测试网络连通 | `ping -c 3 <IP>` |
| 测试端口可达 | `nc -zv <IP> <端口>` |
| 查询状态 API | `curl http://10.21.31.104:8080/api/v1/status/latest` |
| 检查服务状态 | `systemctl --user status m20-patrol-readonly` |
| 查看服务日志 | `journalctl --user -u m20-patrol-readonly -n 50` |
| 部署系统 | `bash deploy/scripts/deploy-readonly.sh --one-shot` |
| 回滚系统 | `bash deploy/scripts/deploy-readonly.sh --rollback <SHA>` |

---

**文档版本**: V1.0  
**最后更新**: 2026-08-09  
**适用范围**: M20 Pro 现场操作
