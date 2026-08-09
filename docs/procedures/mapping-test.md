# 建图、定位与标点测试

**适用型号：** 山猫 M20 Pro

## 1. 依据与边界

### 指导文件

- 《山猫 M20 Pro 产品手册》V1.1.0，第 11、13、15-18 页
- 《山猫 M20 Pro 软件使用手册》V0.0.1：建图、地图包、RViz 定位
- 《软件开发指南》V1.2.1：APDU/ASDU、basic_server 接口

### 导航控制路径

1. **遥控器/APP 控制**：APP 导航模式 + 标点工具（本次测试）
2. **二次开发导航**：GOS 程序经 basic_server 下发（当前不启用）

### 安全条件

开始前确认：
- 机器人周围 2m 清空，人员保持 2m 距离
- 电池电量 > 20%，两块电池状态正常
- 手柄连接，软急停可用
- 激光雷达无遮挡
- 操作员、安全观察员到位

立即停止条件：定位丢失、红色异常、腿乱摆/摔倒、低电量、人员进入排除区。

## 2. 连接与版本记录

| 主机 | 职责 | IP |
|------|------|-----|
| AOS | 运动控制、basic_server | 10.21.31.103 |
| NOS | 建图、定位、导航 | 10.21.31.106 |
| GOS | 二次开发主机 | 10.21.31.104 |

```bash
ssh user@10.21.31.106
```

记录版本信息：
```
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

### 3.1 核验

```bash
command -v drmap
ls -ld /var/opt/robot/data/maps
readlink -f /var/opt/robot/data/maps/active
```

不存在时停止。

### 3.2 启动建图

地图名称：`hxzx_office_<日期>`

```bash
sudo drmap mapping -n hxzx_office_20260809
```

行走路线：小回环 → 大回环，覆盖任务区域。避免急加速/刹车/转弯。

结束：
```bash
sudo drmap stop_mapping
```

### 3.3 核验与备份

```bash
readlink -f /var/opt/robot/data/maps/active
find -L /var/opt/robot/data/maps/active -maxdepth 1 -type f -printf '%f %s bytes\n' | sort
drmap pack
ls -lah /home/user/Downloads
sha256sum /home/user/Downloads/*.zip
```

建图不执行 `drmap unpack`。

## 4. RViz 定位核验

```bash
su
source /opt/ros/foxy/setup.bash
export XAUTHORITY=/home/user/.Xauthority
rviz2
```

配置：`/opt/robot/share/localization/conf/localization.rviz`

检查点云与地图重合。不重合时使用 **2D Pose Estimate** 标定。

## 5. APP 标点工具

### 启用

设置 → 辅助功能 → 标点工具

### 拍照点

1. 移动到拍照姿态
2. 点击 **获取当前坐标**（绿色=成功）
3. 点位类型：任务点
4. 步态：基础步态
5. 导航模式：自主导航
6. 速度：低速，方向：前进
7. 开启障碍物检测
8. 保存

### 充电点

1. 停靠在充电桩前
2. 新增点位 → 获取坐标
3. 类型：充电点
4. 记录，不执行充电

### 路线执行

1. 保存路线，循环次数=1
2. 复核：地图编号、任务点、低速、前进、障碍物检测
3. 执行 → 到达拍照点后 APP 拍照

## 6. 测试结果

### 建图与定位

| 项目 | 结果 |
|------|------|
| drmap mapping 启动 | |
| drmap stop_mapping 结束 | |
| active 地图路径 | |
| 地图包文件名 | |
| 地图包 SHA-256 | |
| RViz 点云与地图重合 | |

### 标点与导航

| 项目 | 结果 |
|------|------|
| APP 版本 | |
| 系统版本 | |
| 拍照点坐标获取 | |
| 拍照点保存 | |
| 充电点坐标获取 | |
| 导航模式切换 | |
| 路线执行 | |
| 拍照 | |
| 异常/保护/急停 | |

### 二次开发前置条件

| 条件 | 结果 |
|------|------|
| M20 Pro 型号确认 | |
| 地图与定位记录完整 | |
| APP 单点路线基线通过 | |
| basic_server 权限与样本 | |
| 现场负责人书面放行 | |
