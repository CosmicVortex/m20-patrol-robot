# 数尔安防吊舱 WEB 通讯协议

**文档版本**: V1.0
**更新日期**: 2026-04-12
**设备型号**: SR-UPA810T609

---

## 1. 登录认证

### 1.1 命令格式

- 命令字: `Login.cgi`
- Method: POST
- URL: `http://admin:123456@192.168.1.101/merlin/Login.cgi?Type=WEB&Expires=30`

### 1.2 请求包

querystring参数：
- Type: WEB
- Expires: 30（会话有效期，分钟）

请求包包体：根据用户名密码组POST请求

### 1.3 应答包包体格式

```json
{
  "Session": "0x7f74105010",
  "result": {
    "message": "OK",
    "num": 200
  }
}
```

---

## 2. 心跳包

### 2.1 命令格式

- 命令字: `Heartbeat.cgi`
- Method: GET
- URL: `http://192.168.1.101/merlin/Heartbeat.cgi`

### 2.2 应答包包体

```json
{
  "result": {
    "message": "OK",
    "num": 200
  }
}
```

---

## 3. RPY三轴角度控制

### 3.1 命令格式

- 命令字: `SetPtzangle.cgi`
- Method: POST
- URL: `http://192.168.1.108/merlin/SetPtzangle.cgi`

### 3.2 请求包包体

```json
{
  "Angle": {
    "yaw": 5,
    "pitch": 5,
    "roll": 0
  }
}
```

### 3.3 参数说明

| 索引 | 名字 | 类型 | 长度 | 说明 |
|------|------|------|------|------|
| 1 | yaw | int | 4 | 航向轴角度，（-280°，280°） |
| 2 | pitch | int | 4 | 俯仰轴角度，（-115°，40°） |
| 3 | roll | int | 4 | 不支持，默认0 |

---

## 4. 状态反馈

### 4.1 命令格式

- 命令字: `GetFlyStateInfo.cgi`
- Method: GET
- URL: `http://192.168.1.108/merlin/GetFlyStateInfo.cgi`

### 4.2 应答包包体格式

```json
{
  "CamerInfo": {
    "zoom": 1
  },
  "FlyInfo": {
    "pitch": 0,
    "roll": 0,
    "yaw": 0
  },
  "result": {
    "message": "OK",
    "num": 200
  }
}
```

### 4.3 参数说明

| 索引 | 名字 | 类型 | 长度 | 说明 |
|------|------|------|------|------|
| 1 | Zoom | int | 4 | 当前倍率 |
| 2 | yaw | int | 4 | 航向轴角度，（-280°，280°） |
| 3 | pitch | int | 4 | 俯仰轴角度，（-105°，40°） |
| 4 | roll | int | 4 | 不支持，默认0 |

---

## 5. 变倍控制

### 5.1 命令格式

- 命令字: `PtzCtrl.cgi`
- Method: GET
- URL: `http://192.168.1.108/merlin/PtzCtrl.cgi?operation=10&speed=5&channelno=0&value=0`

### 5.2 参数说明

| 索引 | 名字 | 类型 | 长度 | 说明 |
|------|------|------|------|------|
| 1 | operation | int | 4 | 操作命令，参考枚举CMS_PTZ_TYPE |
| 2 | speed | int | 4 | 速度1-8 |
| 3 | channelno | int | 4 | 通道号，从0开始 |
| 4 | value | int | 4 | 预置点或者其他操作的值 |

### 5.3 枚举定义

```c
enum CMS_PTZ_TYPE {
    CMS_PTZ_OPT_STOP = 0,      // 停止云台操作
    CMS_PTZ_OPT_LEFTUP = 1,    // 左上
    CMS_PTZ_OPT_UP = 2,        // 上
    CMS_PTZ_OPT_RIGHTUP = 3,   // 右上
    CMS_PTZ_OPT_LEFT = 4,      // 左
    CMS_PTZ_OPT_RIGHT = 5,     // 右
    CMS_PTZ_OPT_LEFTDOWN = 6,  // 左下
    CMS_PTZ_OPT_DOWN = 7,      // 下
    CMS_PTZ_OPT_RIGHTDOWN = 8, // 右下
    CMS_PTZ_OPT_ZOOM_WIDE = 9, // 变倍-
    CMS_PTZ_OPT_ZOOM_TELE = 10,// 变倍+
    CMS_PTZ_OPT_FOCUS_FAR = 11,// 变焦+
    CMS_PTZ_OPT_FOCUS_NEAR = 12,// 变焦-
};
```

---

## 6. 直接变倍控制

### 6.1 命令格式

- 命令字: `ZoomCtrl.cgi`
- Method: GET
- URL: `http://192.168.1.108/merlin/ZoomCtrl.cgi?zoom=8&channelno=0`

### 6.2 参数说明

| 索引 | 名字 | 类型 | 长度 | 说明 |
|------|------|------|------|------|
| 1 | Zoom | int | 4 | 变倍倍数（1~N），N为可见光相机最大光学倍数 |
| 2 | channelno | int | 4 | 通道号，从0开始 |

---

## 7. 焦距控制

同变倍控制，使用`operation`参数：
- `operation=11`: 变焦+
- `operation=12`: 变焦-

---

## 8. 激光测距开关

### 8.1 命令格式

- 命令字: `SetLaserRanging.cgi`
- Method: POST
- URL: `http://192.168.1.108/merlin/SetLaserRanging.cgi?channel=0`

### 8.2 请求包包体

```json
{
  "Laser_ranging": {
    "Enable": 1
  }
}
```

### 8.3 参数说明

| 索引 | 名字 | 类型 | 长度 | 说明 |
|------|------|------|------|------|
| 1 | Enable | int | 4 | 0:Disable, 1:连续测距, 2:单次测距 |

---

## 9. 激光测距距离获取

### 9.1 命令格式

- 命令字: `GetLaserDistance.cgi`
- Method: POST
- URL: `http://192.168.1.108/merlin/GetLaserDistance.cgi?channel=0`

### 9.2 应答包包体

```json
{
  "Laser_ranging": {
    "Distance": 3.5,
    "Enable": 1
  }
}
```

### 9.3 参数说明

| 索引 | 名字 | 类型 | 长度 | 说明 |
|------|------|------|------|------|
| 1 | Distance | int | 4 | 测距距离，单位：米 |
| 2 | Enable | int | 4 | 测距类型 |

---

## 10. 运动控制

### 10.1 命令格式

- 命令字: `SetPtzDirection.cgi`
- Method: POST
- URL: `http://192.168.1.101/merlin/SetPtzDirection.cgi?channel=0`

### 10.2 请求包包体

```json
{
  "Direction": {
    "ptz_opt": "right",
    "speed": 5
  }
}
```

### 10.3 参数说明

| 索引 | 名字 | 类型 | 长度 | 说明 |
|------|------|------|------|------|
| 1 | ptz_opt | String | - | "left"/"right"/"up"/"down"/"stop" |
| 2 | speed | int | 4 | 1-20 |

---

## 11. 设备状态获取

### 11.1 命令格式

- 命令字: `GetDeviceState.cgi`
- Method: GET
- URL: `http://192.168.1.101/merlin/GetDeviceState.cgi`

### 11.2 应答包包体

```json
{
  "DeviceState": {
    "SystemState": {
      "CPU": 9,
      "MEM": 48,
      "bad": 0,
      "cpu": "40",
      "fan": 0,
      "portNum": 0,
      "state": 0,
      "totalvolume": "0GB",
      "undistributed": "0GB"
    }
  },
  "result": {
    "message": "OK",
    "num": 200
  }
}
```

### 11.3 参数说明

| 索引 | 名字 | 类型 | 长度 | 说明 |
|------|------|------|------|------|
| 1 | CPU | int | 4 | CPU利用率 |
| 2 | MEM | int | 4 | 内存利用率 |
| 3 | totalvolume | String | - | 存储卡总容量 |
| 4 | undistributed | String | - | 剩余容量 |
| 5 | state | int | 4 | 存储状态，0=OK, 1=Bad |

---

## 12. 焦距获取

### 12.1 命令格式

- 命令字: `GetFocusInfo.cgi`
- Method: GET
- URL: `http://192.168.1.108/merlin/GetFocusInfo.cgi?channel=0`

### 12.2 应答包包体

```json
{
  "Focus_info": {
    "Elf": 6144,
    "Index": 0
  },
  "result": {
    "message": "OK",
    "num": 200
  }
}
```

### 12.3 参数说明

| 索引 | 名字 | 类型 | 长度 | 说明 |
|------|------|------|------|------|
| 1 | Elf | int | 4 | 当前焦距，实际焦距为Elf/1000，单位：mm |
| 2 | Index | int | 4 | 通道号，从0开始 |

---

**协议版本**: V1.0
**更新日期**: 2026-04-12
**制造商**: 杭州数尔安防科技股份有限公司
