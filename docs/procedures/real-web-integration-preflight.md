# M20 Pro 真实Web联调前置采集

**用途：** 在GOS或笔记本执行，采集真实接口、版本、视频证据。  
**边界：** 不发送basic_server报文，不修改服务/配置，不启动导航/运动控制。

## 一、执行环境

```bash
hostname; id; uname -a
python3 --version 2>&1 || true
ip -4 addr; ip route
command -v ffprobe || true
systemctl --user show-environment
```

## 二、目标连通性

```bash
AOS_HOST=10.21.31.103
GOS_HOST=10.21.31.104
NOS_HOST=10.21.31.106

ping -c 2 -W 1 $AOS_HOST 2>&1 || true
nc -zvw3 $AOS_HOST 30001
nc -zvw3 $AOS_HOST 8554
```

## 三、协议服务证据

```bash
AOS_HOST=10.21.31.103 GOS_HOST=10.21.31.104 NOS_HOST=10.21.31.106 \
bash deploy/scripts/collect-readonly-info.sh
```

返回完整原始输出，不得截断或改写。

## 四、视频探测

仅在现场确认RTSP地址后执行：

```bash
ffprobe -v error -rtsp_transport tcp \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of json 'RTSP_URL'
```

返回：RTSP URL、ffprobe JSON输出、鉴权信息、编码格式、分辨率、帧率。

## 五、控制放行材料

真实导航/运动接口需负责人确认以下事项后方可启用：

- M20 Pro型号、软件/固件版本
- basic_server TCP/UDP权限
- 定位正常、避障正常、急停可用
- 无活动导航任务、电量满足阈值
- 安全区域、观察员、回滚方案
- 负责人姓名、时间、授权事项

## 六、返回格式

```
HOST_EXECUTION=笔记本|GOS
OUTPUT_COMPLETE=true|false
CONTROL_AUTHORIZATION=未授权|已授权
VIDEO_EVIDENCE=未提供|已提供
```
