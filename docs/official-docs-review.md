# 官方文档核对记录

核对日期：2026-08-05

> 本文件只保存摘要、链接和项目判断，不复制厂商原始文档。

## 1. 本阶段直接相关链接

- [软件系统架构说明](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/AR4GpnMqJzM30KZ3UklzoGBLVKe0xjE3)
- [计算平台与资源分配](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/Gl6Pm2Db8D30AMZ0Se3l4Re6JxLq0Ee4)
- [运行服务与系统监控](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/XPwkYGxZV3RbA43bU9znqRd5WAgozOKL)
- [系统时间与时间同步](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/P7QG4Yx2Jp7mXxnmiQa3A1DDV9dEq3XD)
- [网络配置](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/93NwLYZXWyg6Rxw6tNR75MABJkyEqBQm)
- [对外通信方式](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/gvNG4YZ7JnemNxlmiNv35roGV2LD0oRE)
- [basic_server通信协议](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/gwva2dxOW4Kb6v3btk13Eplv8bkz3BRL)
- [相机与视频流](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/2Amq4vjg89gGAj5Gtmg0OlzjV3kdP0wQ)
- [建图与地图管理](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/ZgpG2NdyVXrbZRzbCPKNgMK18MwvDqPk)
- [定位模块](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/Qnp9zOoBVBZwADmwhPMDzZPlV1DK0g6l)
- [导航任务下发](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/KGZLxjv9VG3OAkQOS6ALOK6PV6EDybno)
- [Python二次开发教程](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/dpYLaezmVNLdDRkdFgp471d68rMqPxX6)
- [软件更新说明](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/6LeBq413JAz3A9Y3CZL1A6O98DOnGvpb)

## 2. 摘要

### 软件系统架构说明

```text
文档名称：软件系统架构说明
版本：在线页未显示独立版本
更新时间：在线页未显示
适用型号：M20系列；三主机内容以M20 Pro为例
核心功能：AOS/NOS/GOS职责与DrDDS/ROS2 Foxy架构
可直接使用的接口：本页以架构为主
仅适用于特定型号的接口：GOS为M20 Pro二开主机
与本项目相关的内容：业务部署在GOS，避免占用AOS/NOS
安全风险：AOS承担运动控制，不应部署Web或转码业务
版本兼容风险：系统版本需现场确认
需要现场验证的内容：三主机地址、服务和资源
```

### 计算平台与资源分配

```text
文档名称：计算平台与资源分配
版本/更新时间：在线页未显示
适用型号：M20系列，GOS仅M20 Pro
核心功能：RK3588、16GB、128GB eMMC；CPU大小核说明
可直接使用：GOS作为二开部署目标
条件支持：taskset绑定4-7大核
与项目相关：双路视频转码资源评估
安全风险：不能挤占AOS/NOS实时任务
需要现场验证：真实CPU/内存/磁盘、硬编解码插件、温升
```

### basic_server通信协议

```text
文档名称：basic_server通信协议总览
版本/更新时间：在线页未显示
适用型号：M20系列；具体功能按型号
核心功能：16字节APDU头+JSON/XML ASDU
地址端口：10.21.31.103:30000 UDP；10.21.31.103:30001 TCP
数据类型：长度/消息ID为小端；JSON格式位0x01
心跳：至少1Hz；服务端2秒无请求停止主动上报；客户端3秒无响应判定断线
状态：1002/3、4、5、6
安全风险：同一协议包含运动与导航控制，必须权限隔离
版本风险：接口字典与具体导航页存在命令组织差异，应以具体功能页和现场版本为准
```

### 相机与视频流

```text
文档名称：相机与视频流
版本/更新时间：在线页未显示
适用型号：M20系列本体前后广角相机
核心功能：前后USB相机，H.265 RTSP
地址：video1/video2，AOS 8554
ROS2：不发布DDS数据
默认：1280x720、30fps、约1.8Mbps，RK3588 MPP H.265编码
安全风险：修改AOS推流脚本会影响手柄APP，本阶段不修改
需验证：实际RTSP、连续稳定性、GOS转码能力、浏览器端延迟
```

### 建图、定位与导航

```text
适用型号：相关导航和地图功能明确仅M20 Pro支持
地图：NOS /var/opt/robot/data/maps/active
定位：localization融合LiDAR+IMU；1007/2返回地图位姿；2002/1返回状态
导航：1003/1下发，1004/1取消，1007/1查询
依赖：planner/localization/passable_area/global_planner等
安全前置：定位正常、无现有任务、版本和地图一致
风险：自主导航会自动切换导航模式并起立；控制响应不能在未隔离场地测试
```

### 软件更新说明

```text
文档名称：软件更新说明
适用型号：M20和M20 Pro分别列出
已见版本：V1.1.2、V1.1.4、V1.1.6、V1.1.7、V1.1.8
关键事实：V1.1.7增加控制保护；V1.1.8增加全局规划、网络自恢复并修复多项导航/定位/相机问题
版本风险：V1.1.6修改步态接口值；旧PDF与在线文档不可混用
需验证：演示机当前版本及厂商推荐升级路径
```

## 3. 已发现的版本差异

| 项目 | 旧PDF V0.1.0 | 在线开发页 | 处理策略 |
|---|---|---|---|
| 平地敏捷步态 | 12 | `0x3002` | 现场版本绑定，不硬编码通用值 |
| 楼梯敏捷步态 | 13 | `0x3003` | 第一阶段不开放楼梯 |
| Sleep | bool | V1.1.7改为int | 解析兼容，控制仍按版本门控 |
| GOS点云/IMU | 旧文档称受限 | V1.1.7新增 | 仅在确认版本后使用 |
| ROS2跨版本 | 文档警告兼容性 | V1.1.8修复跨版本监听崩溃 | 业务首选basic_server |

## 4. 未说明或需要厂商确认

- basic_server在线“接口字典”的导航Command映射与具体导航页面不完全一致；项目使用具体导航页定义，但实机前需确认。
- TCP导航任务响应是否始终等任务结束才返回，以及同连接上主动状态帧与响应帧的交织方式。
- GOS浏览器视频转码的官方推荐实现与硬件插件。
- 当前固件是否允许第三方程序长期保持basic_server TCP订阅。
- Web控制功能的官方安全建议、并发客户端策略和权限边界。
