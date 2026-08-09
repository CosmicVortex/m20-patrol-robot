# 建图、定位与标点测试

**适用型号：** 山猫 M20 Pro
**测试地点：** [内部测试场地]
**测试内容：** 建图、遥控器导航模式、标点工具使用

## 1. 依据与边界

### 指导文件

- 《山猫 M20 Pro 产品手册》V1.1.0，第 11、13、15–18 页：APP 控制界面、导航模式、标点工具、急停
- 《山猫 M20 Pro 软件使用手册》V0.0.1：NOS 建图、地图包、SSH/VNC 和 RViz 定位
- 《软件开发指南》V1.2.1：APDU/ASDU、basic_server 接口
- 《山猫 M20 系列软件开发手册》V0.1.0：basic_server 导航接口原始字典

文档文件版本与机器人软件/固件版本不同。先在 APP 的"设置 → 关于设备"记录设备型号、系统版本和 APP 版本。

### 两种导航控制路径

1. **遥控器/APP 控制路径：** APP 切换到"导航模式"，用标点工具保存和执行路线。本次测试只验证该路径。
2. **二次开发导航：** GOS 程序经 basic_server 下发单点导航。当前不具备实机测试条件，不得在本测试中启用。

### 安全与停止条件

开始前确认：
- 机器人周围至少 2m 清空；人员保持至少 2m 安全距离
- 两块电池已安装、状态正常；低于 20% 时停止
- 手柄已连接，软急停可用；硬急停仅用于紧急情况
- 遥控器操作员、安全观察员和现场负责人到位
- 测试区无玻璃、冰面、湿滑瓷砖、高处边缘或人群干扰
- 激光雷达无遮挡

以下情况立即停止：定位丢失；红色异常保护或持续黄色预警；腿乱摆、剧烈晃动、摔倒；低电量；人员进入排除区。

## 2. 连接与版本记录

| 主机 | 职责 | 手册候选地址 |
|---|---|---|
| AOS | 运动控制、basic_server | `10.21.31.103`（已确认） |
| NOS | 建图、定位、导航 | `10.21.31.106` |
| GOS | 二次开发主机 | `10.21.31.104` |

首次连接前，现场负责人核对 NOS 身份和 SSH 主机密钥。密码不得写入仓库、聊天或命令历史。

```bash
ssh <现场签认用户名>@<现场签认NOS地址>
```

在 APP 中记录：

```text
机器人型号：
系统版本：
APP 版本：
测试时间：
测试地点：
操作员：
安全观察员：
现场负责人：
```

## 3. 建图与地图备份

### 3.1 NOS 建图前核验

```bash
command -v drmap
ls -ld /var/opt/robot/data/maps
readlink -f /var/opt/robot/data/maps/active 2>&1 || true
```

`drmap` 或地图目录不存在时停止，保留完整输出。

### 3.2 启动建图

地图名称：`hxzx_office_<日期>`

```bash
sudo drmap mapping -n hxzx_office_<日期>
```

等待约 3–5 秒，确认终端显示 `Building map` 后开始行走。路线先小回环、后大回环，覆盖任务区域。避免急加速、急刹车和急转弯。

结束建图：

```bash
sudo drmap stop_mapping
```

等待终端明确显示建图结束后再关闭终端。

### 3.3 核验与整包备份

```bash
printf '===== ACTIVE MAP =====\n'
readlink -f /var/opt/robot/data/maps/active
printf '\n===== MAP FILES =====\n'
find -L /var/opt/robot/data/maps/active -maxdepth 1 -type f -printf '%f %s bytes\n' | sort
printf '\n===== OCCUPANCY METADATA =====\n'
sed -n '1,20p' /var/opt/robot/data/maps/active/occ_grid.yaml

mkdir -p /home/user/Downloads
drmap pack
ls -lah /home/user/Downloads
```

确认地图包文件名后记录 SHA-256：

```bash
MAP_PACKAGE_FILE='实际文件名.zip'
test -f "/home/user/Downloads/$MAP_PACKAGE_FILE" || { echo '地图包不存在'; exit 2; }
sha256sum "/home/user/Downloads/$MAP_PACKAGE_FILE" | tee /home/user/map-backup-sha256.txt
```

[测试场地]建图不执行 `drmap unpack`；该命令仅用于经批准的整包恢复/迁移。

## 4. RViz 定位核验

在 NOS 图形会话中执行：

```bash
su
source /opt/ros/foxy/setup.bash
export XAUTHORITY=/home/user/.Xauthority
rviz2
exit
```

加载配置：`/opt/robot/share/localization/conf/localization.rviz`

检查实时点云是否与激活地图重合。不重合时选择 **2D Pose Estimate**，在地图上点击真实位置并沿真实机头方向拖动箭头。只有点云与地图重合、定位可信后，才可进行标点和路线测试。

## 5. APP 标点工具

### 5.1 启用

1. APP 控制界面点击 **设置**
2. 进入 **辅助功能**
3. 找到并开启 **标点工具**
4. 返回控制页面，点击 **标点工具**

### 5.2 任务点：拍照点

1. 移动机器人到拍照姿态
2. 点击 **获取当前坐标**（绿色=成功，红色=失败）
3. 确认地图编号与当前激活地图一致
4. 点位类型选择 **任务点**
5. 步态选择基础步态
6. 导航模式选择 **自主导航**
7. 速度选择 **低速**，方向 **前进**
8. 开启 **障碍物检测**（蓝色高亮）
9. 保存点位和路线

记录：

```text
点位名称：拍照点
点位类型：任务点
地图编号：
坐标获取：成功 / 失败
步态：
导航模式：自主导航
速度：低速
障碍物检测：开启
```

### 5.3 充电点（只标记，不执行充电）

1. 在充电桩前停放机器人
2. 新增点位并点击 **获取当前坐标**
3. 点位类型选择 **充电点**
4. 记录设置，不执行一键充电

### 5.4 路线执行

1. 保存路线
2. APP 切换到 **导航模式**
3. 选择测试路线，循环次数设为 `1`
4. 复核路线预览、地图编号、任务点、低速、前进、障碍物检测
5. 点击 **执行**，到达拍照点后执行 APP 拍照

## 6. 测试结果记录

### 建图与定位

| 项目 | 结果 | 证据/输出文件 |
|---|---|---|
| `drmap mapping` 启动 | | |
| `drmap stop_mapping` 结束 | | |
| active 地图路径 | | |
| 地图包文件名 | | |
| 地图包 SHA-256 | | |
| RViz 点云与地图重合 | | |

### 标点与导航

| 项目 | 结果 |
|---|---|
| APP 版本 | |
| 系统版本 | |
| 拍照点坐标获取 | |
| 拍照点保存 | |
| 充电点坐标获取 | |
| 充电点保存 | |
| 导航模式切换 | |
| 路线执行 | |
| 拍照 | |
| 异常/保护/急停 | |

### 二次开发前置条件

| 条件 | 结果 |
|---|---|
| M20 Pro 型号与系统版本确认 | |
| 地图与定位记录完整 | |
| APP 单点路线基线通过 | |
| basic_server 权限与真实样本取得 | |
| 现场负责人书面安全放行 | |
