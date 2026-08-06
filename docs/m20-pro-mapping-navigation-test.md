# M20 Pro 建图、定位与单点导航测试

**适用型号：** 山猫 M20 Pro
**手册依据：**

- 《山猫 M20 Pro 软件使用手册》V0.0.1，2025-07-31；
- 《软件开发指南》V1.2.1，2026-05-18；
- 《导航任务下发》在线开发文档。

本文用于现场建图、定位核验和首条单点路线测试。协议和接口以最新《软件开发指南》文件版本为准；机器人实际软件/固件版本、账号、主机密钥和当前地图以现场核验结果为准。

> 本文只允许 NOS 与官方 APP/遥控器完成首条路线测试。自研程序和 Web 页面不得发送心跳、速度、模式、步态、定位重置或导航指令。

## 1. 主机与连接

| 主机 | 职责 | 手册地址 |
|---|---|---|
| AOS | 运动控制、basic_server | `10.21.31.103` |
| NOS | 建图、定位、导航 | `10.21.31.106` |
| GOS | 用户开发主机 | `10.21.31.104` |

本流程仅登录 NOS，不登录或修改 AOS，也不从 Web 发起导航。

### 1.1 连接 NOS

1. 笔记本连接机器人热点或机器人局域网。
2. 在笔记本终端执行：

```bash
ssh user@10.21.31.106
```

首次连接前，应由现场负责人核对 NOS 主机身份和 SSH 主机密钥。密码不得写入仓库、命令历史或聊天记录。

连接失败时，只在笔记本检查本机网络：

```bash
ip -br addr
ip route
ping -c 2 10.21.31.106
```

不得扫描网段、修改路由或重启机器人主机。

## 2. 建图前检查

建图仅支持约 `50 m × 50 m` 的小面积点云和栅格地图。开始前确认：

- 机器人型号为 M20 Pro；
- 两块电池正常，遥控器已配对，软急停可用；
- 操作员、安全观察员和现场负责人到位；
- 机器人周边至少 2 m 清空，无未评估台阶、边沿、玻璃、湿滑地面、陡坡或人群；
- 已清理路线杂物，打开需要经过的门；
- 激光雷达无遮挡，建图区没有频繁移动的人群和大型临时物体；
- 路线先小回环、后大回环，覆盖任务区域；
- 机器人静止并站立。

出现定位丢失、保护告警、异常姿态、低电量、人员进入排除区或路线异常时，立即停止测试。

- **APP 路线测试：** 仅在当前 APP 指引已确认 Stop 行为后，按确认的 Stop 方式结束；异常运动使用遥控器软急停。硬急停仅用于紧急情况。
- **建图：** 先使机器人安全停止。确认人员与机器人安全后，在建图终端执行：

```bash
sudo drmap stop_mapping
```

等待终端明确显示建图结束。未确认结束前，不得核验、打包、标点或导航。

## 3. NOS 建图

### 3.1 建图前核验

登录 NOS 后执行：

```bash
command -v drmap
ls -ld /var/opt/robot/data/maps
readlink -f /var/opt/robot/data/maps/active 2>&1 || true
```

`drmap` 或 `/var/opt/robot/data/maps` 不存在时停止并保存输出，不猜测替代路径。

### 3.2 启动建图

默认建图。建图结束后默认激活新地图：

```bash
sudo drmap mapping
```

指定地图名称：

```bash
sudo drmap mapping -n dgzs_showroom_20260805_001
```

不打开 RViz：

```bash
sudo drmap mapping -s
```

建图后不立即激活：

```bash
sudo drmap mapping -b
```

手册未明确 `-n` 与 `-s` 或 `-b` 的组合。若确有组合需求，先执行 `drmap -h`，并取得厂商或现场管理员对当前版本的确认。

### 3.3 建图过程与结束

等待约 3–5 秒，确认终端显示 `Building map` 或等效提示后，按预定路线平稳行走。避免急加速、急刹车、急转弯和剧烈运动；全程保持雷达无遮挡。

完成后执行：

```bash
sudo drmap stop_mapping
```

等待终端明确显示建图结束后再关闭终端。

## 4. 地图核验与备份

地图根目录：`/var/opt/robot/data/maps`

当前激活地图：`/var/opt/robot/data/maps/active`

### 4.1 核验激活地图

```bash
printf '===== ACTIVE MAP =====\n'
readlink -f /var/opt/robot/data/maps/active
printf '\n===== MAP FILES =====\n'
find -L /var/opt/robot/data/maps/active -maxdepth 1 -type f -printf '%f %s bytes\n' | sort
printf '\n===== OCCUPANCY METADATA =====\n'
sed -n '1,20p' /var/opt/robot/data/maps/active/occ_grid.yaml
```

确认 `active` 指向本次地图，且地图文件和 `occ_grid.yaml` 可读。否则停止，不进入标点或导航。

### 4.2 整包备份

地图必须按整个地图包管理。不得单独复制、替换或编辑包内 `pgm`、`yaml`、`pcd` 等文件。

```bash
mkdir -p /home/user/Downloads
drmap pack
ls -lah /home/user/Downloads
```

确认本次生成的 zip 文件名后执行：

```bash
MAP_PACKAGE_FILE='实际生成的地图包文件名.zip'
test -f "/home/user/Downloads/$MAP_PACKAGE_FILE" || { echo '地图包不存在，停止'; exit 2; }
sha256sum "/home/user/Downloads/$MAP_PACKAGE_FILE" | tee /home/user/map-backup-sha256.txt
```

`drmap unpack` 会解压并激活地图，且需要重启生效。除非处于单独批准的地图维护窗口，否则不得执行。

## 5. 定位核验

在 NOS 图形桌面会话中启动 RViz。以下命令来自使用手册：

```bash
su
source /opt/ros/foxy/setup.bash
export XAUTHORITY=/home/user/.Xauthority
rviz2
exit
```

`su` 后仅可执行上方三条启动 RViz 所需命令。关闭 RViz 后立即执行 `exit`；不得在 root shell 执行其他操作。若 `/opt/ros/foxy/setup.bash`、`/home/user/.Xauthority` 或 `rviz2` 不存在，停止并保留输出。

在 RViz 中：

1. 选择 **File → Open Config**；
2. 加载：

   ```text
   /opt/robot/share/localization/conf/localization.rviz
   ```

3. 检查实时点云与激活地图是否重合；
4. 不重合时，选择 **2D Pose Estimate**，在地图中点击机器人真实位置，并沿真实机头方向拖动箭头；
5. 仅在点云与地图重合、定位可信时进入标点和路线测试。

定位仍不正确或定位丢失时，停止，不执行路线。

## 6. APP 标点与路线测试

《山猫 M20 Pro 软件使用手册》V0.0.1 没有记录 APP 标点工具菜单、任务点类型、循环次数、Execute、Stop 或低速/前进/避障等界面项。以下步骤必须由现场负责人对照**当前固件配套的官方 APP 指引**逐项确认；菜单或语义不同、Stop 行为未确认时，停止，不做路线测试。

确认后：

1. 在 APP 启用标点工具；
2. 新建路线；
3. 用遥控器将机器人移动到目标巡检姿态；
4. 添加点并获取当前坐标；
5. 仅保留获取成功的点；
6. 按当前官方 APP 指引选择任务点类型；
7. 首次测试仅使用当前官方 APP 指引确认的低速、前进和避障开启配置；
8. 步态和导航模式仅从当前 APP、当前固件实际可选项中选择；不手工填写旧文档步态数值；
9. 保存路线。

记录路线名称、任务点名称、激活地图目录、地图包 SHA256、坐标获取时间、机头方向，以及实际速度、方向和避障配置。

### 6.1 首个单点测试

操作员和安全观察员共同确认：

- 激活地图与第 4 节记录一致；
- 当前 APP 指引已明确路线预览、任务点类型、循环次数、Execute 和 Stop 的含义；
- 路线只有一个任务点，没有残留或未知路线；
- 当前 APP 指引确认循环次数为 1，且确认低速、前进、避障开启；
- RViz 点云与地图重合；
- 操作员、观察员和机器人全程可视，排除区无人，软急停责任人明确。

任一项不一致或 Stop 行为未确认时，停止，不点击 Execute。

按当前官方 APP 指引选择已核对路线，将循环次数设为 1 后执行。运行中持续观察姿态、路径、避障和人员。异常运动使用遥控器软急停。到达失败、取消、异常、定位丢失或保护触发时，本次测试判定失败；不自动重试，不进入下一点。

记录开始/结束时间、地图目录、路线与点位、是否到达、定位状态、避障状态、告警、是否使用 Stop/软急停/硬急停，以及操作员和安全观察员结论。

## 7. 自研程序与 Web 边界

- 建图、地图激活、定位和首条路线测试由 NOS 与官方 APP/遥控器完成；
- NOS 原生维护地图。GOS/Web 后续只能读取经过核验的地图副本用于展示，不得写入或修改 NOS 地图；
- APP 建立的路线和点位是第一阶段原生基线，自研 Web 不得直接写入；
- 建图完成不代表 Web 可以启动巡逻；
- 当前 Web 页面仅显示 `SIMULATED / CONTROL OFF`，不得连接 basic_server 或下发导航；
- 只有完成真实状态接入、定位/保护解析、视频验证、导航安全门控、单点回归、审计授权和书面安全放行后，才可单独评审 Web 控制。
