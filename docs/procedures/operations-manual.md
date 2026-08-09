# 现场操作手册

本文档汇总 M20 Pro 现场操作的关键指令。

## 1. 主机连接

### SSH

```bash
# 连接到 NOS（建图主机）
ssh user@13.21.31.106

# 连接到 GOS（开发主机）
ssh user@10.21.31.104
```

### 端口

| 服务 | 端口 | 用途 |
|------|------|------|
| basic_server TCP | 30001 | 状态订阅 |
| basic_server UDP | 30000 | 高频指令 |
| RTSP | 8554 | 视频流 |
| Web | 8080 | 仪表盘 |

## 2. 版本确认

```bash
# 查询固件版本
ssh user@13.21.31.106
cat /var/opt/robot/release_note.json
```

记录：机器人型号、系统版本、APP 版本、测试时间、地点。

## 3. 网络测试

```bash
# 连通性测试
ping -c 3 10.21.31.103
ping -c 3 13.21.31.106

# 端口测试
nc -zv 10.21.31.103 30001
```

## 4. 建图操作

### 4.1 安全准备

- 机器人周围 2m 清空
- 电池电量 > 20%
- 激光雷达无遮挡
- 操作员、安全观察员到位

### 4.2 启动建图

```bash
sudo drmap mapping -n <地图名称>
```

地图命名：`<场地>_map_<日期>`

### 4.3 结束建图

```bash
sudo drmap stop_mapping
```

### 4.4 地图备份

```bash
# 确认激活地图
readlink -f /var/opt/robot/data/maps/active

# 打包
drmap pack

# 记录哈希
sha256sum /home/user/Downloads/*.zip
```

## 5. 定位核验

```bash
# RViz 定位检查
su
source /opt/ros/foxy/setup.bash
rviz2
```

加载配置：`/opt/robot/share/localization/conf/localization.rviz`

检查点云与地图重合。

## 6. 状态监控

```bash
# 查询状态
curl http://10.21.31.104:8080/api/v1/status/latest

# 健康检查
curl http://10.21.31.104:8080/api/v1/health

# 服务状态
systemctl --user status m20-patrol-readonly.service
```

## 7. 视频测试

```bash
# 探测视频流
ffprobe rtsp://10.21.31.103:8554/video1
```

记录编码格式、分辨率、帧率。

## 8. 故障排查

### 服务无法启动

```bash
python3.8 --version
python3.8 -c 'import backend; print("OK")'
ss -ltnup | grep 8080
```

### 遥测无数据

```bash
ss -tn | grep 10.21.31.103:30001
journalctl --user -u m20-patrol-readonly.service -n 50
```

### 视频无响应

```bash
ffprobe rtsp://10.21.31.103:8554/video1
command -v ffmpeg
```

## 快速命令

| 任务 | 命令 |
|------|------|
| SSH 到 NOS | `ssh user@13.21.31.106` |
| 查询固件 | `cat /var/opt/robot/release_note.json` |
| 启动建图 | `sudo drmap mapping -n <名称>` |
| 停止建图 | `sudo drmap stop_mapping` |
| 打包地图 | `drmap pack` |
| 部署系统 | `bash deploy/scripts/deploy-readonly.sh --one-shot` |
| 回滚系统 | `bash deploy/scripts/deploy-readonly.sh --rollback <SHA>` |
