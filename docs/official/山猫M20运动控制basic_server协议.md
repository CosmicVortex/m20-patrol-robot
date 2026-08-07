# 山猫 M20 运动控制（basic_server 协议）

**文档版本：** V1.0.0  
**适用型号：** 山猫 M20、山猫 M20 Pro  
**适用软件包版本：** V1.1.7 及以后  
**更新日期：** 2026-06-18

---

## 前置说明

本章节主要描述通过 basic_server 协议（UDP/TCP）调用运动控制的逻辑。如需在机载进行算法开发（导航、SLAM 等），参见 [运动控制（ROS2）](./motion-control-ros2.md)。

ROS2 接口的调用逻辑和 basic_server 协议略有差别。

相关文档：[basic_server 通信协议总览](./basic-server-protocol-overview.md) | [软件开发指南](../V1.2.1.md)

---

## 1. 运动状态定义

运动控制使用以下统一的状态值：

| 十六进制值 | 十进制值 | 名称 | 说明 |
|---|---|---|---|
| 0x0 | 0 | 空闲 | 空闲状态，无动作，等待指令 |
| 0x1 | 1 | 站立 | 临时过渡状态，会自动跳转到 RL 控制状态 |
| 0x2 | 2 | 软急停 | 关节断电，最高优先级，任意状态下均可触发 |
| 0x3 | 3 | 开机阻尼 | 开机后自动进入的阻尼状态 |
| 0x4 | 4 | 趴下 | 安全趴下状态 |
| 0x11 | 17 | RL 控制 | 强化学习控制模式，唯一可执行移动和步态切换的状态 |

> **关键：** 站立（1）是一个临时过渡状态，不是可以持续保持的状态。机器人会自动从站立（1）进入 RL 控制（17），此时才能执行移动控制和步态切换。

---

## 2. 步态定义

| 十六进制值 | 十进制值 | 名称 | 运动模式 | 适用场景 |
|---|---|---|---|---|
| 0x1001 | 4097 | 基础 | 标准 | 室内平坦地面，手动遥控 |
| 0x1003 | 4099 | 楼梯 | 标准 | 台阶/路沿，手动遥控 |
| 0x3002 | 12290 | 平地 | 敏捷 | 自主导航 + 平地行走 |
| 0x3003 | 12291 | 楼梯 | 敏捷 | 自主导航 + 台阶跨越 |

> **敏捷运动模式**下的步态速度响应性能较好，适用于导航等自主算法开发。  
> 每次起立后或切换使用模式（常规/辅助/导航）时，步态会自动重置为基础步态（0x1001）。

---

## 3. 状态转换逻辑

### 调用逻辑建议

- 在读取当前运动状态时，开发者可以读取到所有运动状态值。
- 使用 UDP/TCP 协议下发切换运动状态时，除软急停外，仅能有效切换上图由绿色箭头连接的状态，且机器人在运动状态下将拒绝执行起立/趴下指令：
  - 若机器人处于开机阻尼/空闲/趴下状态且姿态正常，可直接执行起立指令；若姿态异常，机器人将拒绝起立并上报错误。
  - 若机器人处于 RL 控制状态且静止时，可直接执行趴下指令；若机器人正在运动中，将拒绝趴下指令。
  - 软急停指令为最高优先级，任意状态下均可下发生效。
  - 起立/趴下过程中，除软急停外，其余运动控制操作均被禁用。
  - 仅在 RL 控制状态（17）下可切换步态或执行运动控制指令。

---

## 4. 下发运控指令 — basic_server 协议

### 4.1 协议概述

在 basic_server 协议中，运动控制统一使用 **Type=2**，通过以下子命令（Command）区分功能：

| Command | 功能 | 频率建议 | 传输方式 | 使用模式限制 |
|---|---|---|---|---|
| 21 | 运动控制-轴指令（归一化速度控制） | 20Hz | UDP 优先 | 仅常规/辅助模式 |
| 22 | 运动状态转换（站立/趴下/软急停等） | 事件触发 | TCP/UDP | — |
| 23 | 步态切换 | 事件触发 | TCP/UDP | — |
| 25 | 运动控制-速度指令 | 20Hz | UDP 优先 | 仅导航模式 |

> **推荐：** 高频速度指令（Cmd=21/25）使用 UDP（端口 30000），以获得最低延迟；状态切换类指令使用 TCP（端口 30001）以保证可靠性。

> **文档中出现的所有 Type / Command 均为十进制数字。**

### 4.2 运动状态转换（Cmd=22）

通过 MotionParam 字段控制机器人的运动状态。

下发控制指令前，请通过 BasicStatus 上报（Type=1002 Cmd=6）读取 MotionState 字段，结合状态转换逻辑来判断当前机器人是否处于可下发运动状态切换指令的运动状态。

#### JSON 请求

```json
{
  "PatrolDevice": {
    "Type": 2,
    "Command": 22,
    "Time": "2026-05-20 10:00:00",
    "Items": {
      "MotionParam": 1
    }
  }
}
```

#### XML 请求

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PatrolDevice>
  <Type>2</Type>
  <Command>22</Command>
  <Time>2026-05-20 10:00:00</Time>
  <Items>
    <MotionParam>1</MotionParam>
  </Items>
</PatrolDevice>
```

#### MotionParam 值说明

| MotionParam 值（十进制） | 对应运动状态 | 说明 |
|---|---|---|
| 1 | 站立 | 仅在处于开机阻尼（MotionState=3）/空闲（MotionState=0）/趴下状态（MotionState=4）且姿态正常时有效 |
| 2 | 软急停 | 最高优先级，任意状态下可触发 |
| 4 | 趴下 | 仅在 RL 控制状态（MotionState=17）且静止时有效 |

下发控制指令后，请通过 BasicStatus 上报（Type=1002 Cmd=6）确认 MotionState 字段是否已反映目标状态。

### 4.3 步态切换（Cmd=23）

通过 GaitParam 字段切换机器人的步态模式。

#### JSON 请求

```json
{
  "PatrolDevice": {
    "Type": 2,
    "Command": 23,
    "Time": "2026-05-20 10:00:00",
    "Items": {
      "GaitParam": 4097
    }
  }
}
```

#### XML 请求

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PatrolDevice>
  <Type>2</Type>
  <Command>23</Command>
  <Time>2026-05-20 10:00:00</Time>
  <Items>
    <GaitParam>4097</GaitParam>
  </Items>
</PatrolDevice>
```

#### 调用逻辑建议

- 步态切换仅在 RL 控制状态（MotionState=17）下执行，且必须等前一步态切换指令完成后才能下发下一个。
- 每次起立后或切换使用模式时，步态会自动重置为基础步态（0x1001）。
- 步态切换仅在静止状态下允许；运动过程中下发的步态切换指令将被拒绝。

下发控制指令后，请通过 BasicStatus 上报（Type=1002 Cmd=6）确认 Gait 字段是否已切换为目标步态值。

### 4.4 运动控制-轴指令（Cmd=21）

> **仅在常规模式和辅助模式下可使用。导航模式下请使用 Cmd=25。**

向机器人发送运动速度指令。所有轴使用归一化值（[-1.0, 1.0]），表示相对于该轴最大速度的百分比。

#### JSON 请求

```json
{
  "PatrolDevice": {
    "Type": 2,
    "Command": 21,
    "Time": "2026-05-20 10:00:00.050",
    "Items": {
      "X": 0.5,
      "Y": 0.0,
      "Z": 0.0,
      "Roll": 0.0,
      "Pitch": 0.0,
      "Yaw": 0.3
    }
  }
}
```

#### 字段说明

| 字段 | 类型 | 范围 | 含义 |
|---|---|---|---|
| X | float | [-1, 1] | 前进/后退（归一化百分比） |
| Y | float | [-1, 1] | 左移/右移（归一化百分比） |
| Z | float | [-1, 1] | 上升/下降（归一化百分比） |
| Roll | float | [-1, 1] | 横滚角控制（归一化百分比） |
| Pitch | float | [-1, 1] | 俯仰角控制（归一化百分比） |
| Yaw | float | [-1, 1] | 偏航角速度（归一化百分比） |

#### 注意事项

- **发送频率：** 建议不低于 20Hz
- **传输方式：** 强烈推荐 UDP（低延迟）
- **参数生效：** 当前开放的四种移动步态仅有 X、Y、Yaw 三个参数项生效
- **超时保护：** 如果超过 500ms 未收到新的速度指令，机器人会自动减速并进入安全状态

下发控制指令后，可通过运动数据上报（Type=1002 Cmd=4）确认 MotionStatus.LinearX / LinearY 等字段是否已反映目标运动状态。

### 4.5 运动控制-速度指令（Cmd=25）

> **仅在导航模式下可使用。常规/辅助模式下请使用 Cmd=21。**

Cmd=25 与 Cmd=21 的字段格式相同，但传输的是速度值，可用于导航规划输出的速度指令下发。

#### JSON 请求

```json
{
  "PatrolDevice": {
    "Type": 2,
    "Command": 25,
    "Time": "2023-01-01 00:00:00",
    "Items": {
      "X": 0.0,
      "Y": 0.0,
      "Z": 0.0,
      "Roll": 0.0,
      "Pitch": 0.0,
      "Yaw": 0.0
    }
  }
}
```

#### 字段说明

| 字段 | 类型 | 范围 | 含义 |
|---|---|---|---|
| X | float | 视步态而定 | 前后方向运动速度（m/s） |
| Y | float | 视步态而定 | 左右方向运动速度（m/s） |
| Z | float | 视步态而定 | 高度方向运动速度（m/s） |
| Roll | float | 视步态而定 | 翻滚角速度（rad/s） |
| Pitch | float | 视步态而定 | 俯仰角速度（rad/s） |
| Yaw | float | 视步态而定 | 偏航角速度（rad/s） |

> **注意：** 当前开放的四种移动步态仅有 X、Y、Yaw 三个参数项生效。

#### 各步态的有效速度范围

> **适用范围：** 软件包版本≥V1.1.7

| 步态名称 | 十六进制码 | X 轴线速度 (m/s) | Y 轴线速度 (m/s) | Yaw 角速度 (rad/s) |
|---|---|---|---|---|
| 标准-基础 | 0x1001 | [-2.0, -0.2] ∪ [0.2, 2.0] | [-1.0, -0.35] ∪ [0.35, 1.0] | [-2.0, -0.5] ∪ [0.5, 2.0] |
| 标准-楼梯 | 0x1003 | [-2.0, -0.15] ∪ [0.15, 2.0] | [-1.0, -0.3] ∪ [0.3, 1.0] | [-2.0, -0.4] ∪ [0.4, 2.0] |
| 敏捷-平地 | 0x3002 | [-2.0, -0.15] ∪ [0.15, 2.0] | [-1.0, -0.25] ∪ [0.25, 1.0] | [-1.5, -0.35] ∪ [0.35, 1.5] |
| 敏捷-楼梯 | 0x3003 | [-2.0, -0.15] ∪ [0.15, 2.0] | [-1.0, -0.3] ∪ [0.3, 1.0] | [-2.0, -0.4] ∪ [0.4, 2.0] |

---

## 5. 状态与数据上报 — basic_server 协议

### 5.1 基础状态上报（Type=1002 Cmd=6）

基础状态由 RobotServer 以 **2Hz** 频率主动推送，包含运动状态、步态、使用模式等聚合信息。需先发送心跳指令（Type=100 Cmd=100）后才会接收此上报。

#### JSON 上报

```json
{
  "PatrolDevice": {
    "Type": 1002,
    "Command": 6,
    "Time": "2026-05-20 10:00:00",
    "Items": {
      "BasicStatus": {
        "MotionState": 17,
        "Gait": 4097,
        "Charge": 0,
        "HES": 0,
        "ControlUsageMode": 0,
        "Direction": 0,
        "OOA": 0,
        "PowerManagement": 0,
        "Sleep": 0,
        "Version": "STD"
      }
    }
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| MotionState | int | 运动状态值（见第 1 节） |
| Gait | int | 步态值（见第 2 节） |
| Charge | int | 充电状态（0=空闲, 1=前往充电桩, 2=充电中, 3=退出充电桩, 4=异常, 5=在桩上未充电） |
| HES | int | 硬急停状态（0=未触发, 1=已触发） |
| ControlUsageMode | int | 使用模式（0=常规, 1=导航, 2=辅助） |
| Version | string | 设备版本（STD/PRO） |

验证运动状态切换和步态切换的结果时，应查看此上报中的 MotionState 和 Gait 字段。

### 5.2 运控状态上报（Type=1002 Cmd=4）

运控状态由 RobotServer 以 **10Hz** 频率主动推送，包含机身姿态、线速度和 16 个关节的详细状态。

#### JSON 上报

```json
{
  "PatrolDevice": {
    "Type": 1002,
    "Command": 4,
    "Time": "2023-01-01 00:00:00",
    "Items": {
      "MotionStatus": {
        "Roll": 0.0,
        "Pitch": 0.0,
        "Yaw": 0.0,
        "OmegaZ": 0.0,
        "LinearX": 0.0,
        "LinearY": 0.0,
        "Height": 0.0,
        "Payload": 0.0,
        "RemainMile": 0.0
      },
      "MotorStatus": {
        "Joint": [0.0, 0.0, ...],
        "LeftFrontHipX": 0.0,
        "LeftFrontHipY": 0.0,
        "LeftFrontKnee": 0.0,
        "LeftFrontWheel": 0.0,
        "RightFrontHipX": 0.0,
        "RightFrontHipY": 0.0,
        "RightFrontKnee": 0.0,
        "RightFrontWheel": 0.0,
        "LeftBackHipX": 0.0,
        "LeftBackHipY": 0.0,
        "LeftBackKnee": 0.0,
        "LeftBackWheel": 0.0,
        "RightBackHipX": 0.0,
        "RightBackHipY": 0.0,
        "RightBackKnee": 0.0,
        "RightBackWheel": 0.0
      }
    }
  }
}
```

#### MotionStatus 字段

| 字段 | 类型 | 单位 | 含义 |
|---|---|---|---|
| Roll/Pitch/Yaw | float | rad | 机器人姿态角度 |
| OmegaZ | float | rad/s | Z 方向角速度 |
| LinearX / LinearY | float | m/s | 机器人当前 X/Y 方向线速度 |
| Height | float | m | 当前机身高度 |
| RemainMile | float | km | 预计剩余续航里程 |

#### MotorStatus 字段

- **Joint**：长度为 16 的数组，按顺序依次表示：LeftFrontHipX、LeftFrontHipY、LeftFrontKnee、LeftFrontWheel、RightFrontHipX、RightFrontHipY、RightFrontKnee、RightFrontWheel、LeftBackHipX、LeftBackHipY、LeftBackKnee、LeftBackWheel、RightBackHipX、RightBackHipY、RightBackKnee、RightBackWheel
- 各关节独立字段：HipX（侧摆）、HipY（髋关节）、Knee（膝关节）、Wheel（足轮）

---

## 6. 快速启动流程参考

以下是启动一段标准运动的最小流程：

```
1. Type=1002, Cmd=6  →  查看运动状态 MotionState
2. Type=2,   Cmd=22, MotionParam=1  →  下发起立指令
3. Type=1002, Cmd=6  →  查看运动状态是否进入 RL 控制状态（MotionState = 17）
4. Type=2,   Cmd=23, GaitParam=0x1001  →  切到目标步态
5. Type=1002, Cmd=6  →  查看步态 Gait
6. Type=2,   Cmd=21 (20Hz)  →  下发轴指令
7. 停止  →  停止发送轴指令即可
```

### Python 示例

```python
import json
import socket
from datetime import datetime

def build_motion_command(motion_param):
    """下发起立/趴下/软急停指令"""
    return {
        "PatrolDevice": {
            "Type": 2,
            "Command": 22,
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Items": {"MotionParam": motion_param}
        }
    }

def build_gait_command(gait_param):
    """下步态切换指令"""
    return {
        "PatrolDevice": {
            "Type": 2,
            "Command": 23,
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Items": {"GaitParam": gait_param}
        }
    }

def build_axis_command(x=0.0, y=0.0, yaw=0.0):
    """下发轴指令（常规/辅助模式）"""
    return {
        "PatrolDevice": {
            "Type": 2,
            "Command": 21,
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "Items": {"X": x, "Y": y, "Z": 0.0, "Roll": 0.0, "Pitch": 0.0, "Yaw": yaw}
        }
    }

def build_speed_command(x=0.0, y=0.0, yaw=0.0):
    """下发速度指令（导航模式）"""
    return {
        "PatrolDevice": {
            "Type": 2,
            "Command": 25,
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Items": {"X": x, "Y": y, "Z": 0.0, "Roll": 0.0, "Pitch": 0.0, "Yaw": yaw}
        }
    }
```

---

## 7. 注意事项

1. **状态机约束：** 仅在 RL 控制状态（MotionState=17）下可执行步态切换和运动控制指令。
2. **频率要求：** 轴指令建议 20Hz，速度指令建议 10Hz。
3. **超时保护：** 超过 500ms 未收到速度指令，机器人自动减速进入安全状态。
4. **步态生效：** 当前步态下仅有 X、Y、Yaw 三个参数项生效。
5. **模式限制：** Cmd=21 仅常规/辅助模式可用，Cmd=25 仅导航模式可用。

---

**文档版本：** V1.0.0  
**更新日期：** 2026-06-18  
**版权归属：** 杭州云深处科技
