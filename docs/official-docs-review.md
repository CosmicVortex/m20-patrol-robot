# 官方文档核对记录

核对日期：2026-08-06

## 使用手册文件记录

| 文件名称 | 文件版本 | 文件日期 | 使用方式 | 原文存放 |
|---|---:|---|---|---|
| 山猫 M20 Pro 软件使用手册 | V0.0.1 | 2025-07-31 | 用于核对主机职责、SSH/VNC、建图、地图包和 RViz 定位步骤 | 用户已明确授权上传至本项目私有仓库 |
| 山猫 M20 Pro 产品手册 | V1.1.0 | 2026-04-15 | 用于核对 APP 控制界面、标点工具、导航模式、软硬急停与自主充电操作 | 本地受控资料；引用摘要，不复制原文 |
| 山猫 M20 系列软件开发手册 | V0.1.0 | 2025-09-16 | 用于核对 basic_server APDU/ASDU、导航任务和任务状态接口 | 本地受控资料；引用摘要，不复制原文 |

> 本文件只保存摘要、链接和项目判断，不复制厂商原始文档。

## 本阶段相关官方页面

- [软件系统架构说明](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/AR4GpnMqJzM30KZ3UklzoGBLVKe0xjE3)
- [计算平台与资源分配](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/Gl6Pm2Db8D30AMZ0Se3l4Re6JxLq0Ee4)
- [运行服务与系统监控](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/XPwkYGxZV3RbA43bU9znqRd5WAgozOKL)
- [系统时间与时间同步](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/P7QG4Yx2Jp7mXxnmiQa3A1DDV9dEq3XD)
- [网络配置](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/93NwLYZXWyg6Rxw6tNR75MABJkyEqBQm)
- [对外通信方式](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/gvNG4YZ7JnemNxlmiNv35roGV2LD0oRE)
- [basic_server 通信协议](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/gwva2dxOW4Kb6v3btk13Eplv8bkz3BRL)
- [相机与视频流](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/2Amq4vjg89gGAj5Gtmg0OlzjV3kdP0wQ)
- [建图与地图管理](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/ZgpG2NdyVXrbZRzbCPKNgMK18MwvDqPk)
- [定位模块](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/Qnp9zOoBVBZwADmwhPMDzZPlV1DK0g6l)
- [导航任务下发](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/KGZLxjv9VG3OAkQOS6ALOK6PV6EDybno)
- [Python 二次开发教程](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/dpYLaezmVNLdDRkdFgp471d68rMqPxX6)
- [软件更新说明](https://alidocs.dingtalk.com/i/p/OlnXRl7ed542DGLp/docs/6LeBq413JAz3A9Y3CZL1A6O98DOnGvpb)

## 文档摘要

### 软件系统架构说明

- **适用范围：** M20 系列；三主机内容以 M20 Pro 为例。
- **结论：** AOS 负责运动控制，NOS 负责建图、定位和导航，GOS 是用户二次开发的部署位置。
- **项目处理：** Web、视频和 AI 业务不部署到 AOS/NOS；现场地址、服务和资源仍需核验。

### 计算平台与资源分配

- **适用范围：** M20 系列；GOS 仅 M20 Pro 提供。
- **文档摘要：** GOS 为 RK3588、16 GB 内存、128 GB eMMC。
- **项目处理：** 双路视频转码前先核验真实 CPU、内存、磁盘、硬件编解码插件和温升。

### basic_server 通信协议

- **适用范围：** M20 系列；具体能力受型号限制。
- **接口：** UDP `10.21.31.103:30000`，TCP `10.21.31.103:30001`。
- **结构：** 16 字节 APDU + JSON/XML ASDU；长度和报文 ID 为小端，JSON 格式位为 `0x01`。
- **连接要求：** 文档建议至少 1 Hz 心跳；服务端 2 秒无请求停止主动上报，客户端 3 秒无响应判定断线。
- **项目处理：** 当前实现只做离线编解码，不建立连接或发送心跳。真实接入前确认权限、固件和样本。

### APP 标点工具与导航模式

- **产品手册页码：** 第 11、13、15–18 页。
- **已核对功能：** 控制界面的“使用模式”支持常规模式、导航模式、辅助模式；“设置 → 辅助功能”可启用标点工具；路线支持新增、编辑、删除、循环次数、执行/停止和保存；点位支持获取当前坐标、过渡点/任务点/充电点、基础/楼梯步态、直线/自主导航、低速/正常/高速、前进/后退和障碍物检测。
- **自主充电边界：** “一键充电”会自动切换导航模式并执行自主充电任务。本次只标记自主充电点，不执行一键充电。
- **项目处理：** 下午先用遥控器/APP 完成导航模式和门口拍照点单点基线；APP 实际版本、菜单显示和路线结果仍须现场记录。

### 相机与视频流

- **来源：** 前后本体相机通过 AOS 的 RTSP 提供视频；资料记录 `video1`、`video2`，端口 `8554`。
- **默认资料：** H.265、1280×720、30 fps、约 1.8 Mbps/路。
- **项目处理：** 浏览器端需要 GOS 转换为 WebRTC/H.264 或 HLS/H.264。实际 RTSP、GOS 转码能力和延迟尚未验证。
- **限制：** 不修改 AOS 原厂推流脚本。

### 建图、定位与导航

- **适用范围：** 导航相关能力仅 M20 Pro 支持。
- **地图：** NOS 原生维护 `/var/opt/robot/data/maps/active`。
- **定位：** `localization` 使用 LiDAR 与 IMU；地图坐标和感知状态接口需按现场版本确认。
- **导航接口：** 单点下发 `1003/1`，取消 `1004/1`，查询导航任务执行状态 `1007/1`；查询地图坐标使用 `1007/2`。`1003/1` 的任务字段包括目标点、地图编号、坐标、朝向、点位类型、步态、速度、运动方向、避障模式和导航方式；响应包含 `Value`、`Status`、`ErrorCode`。
- **项目处理：** 先由官方 APP/遥控器完成单点基线验证。当前仓库只实现通用离线 APDU/ASDU 编解码，没有真实 TCP 客户端或命令级导航实现；自研程序和 Web 当前不开放导航。

### 软件更新说明

- **已见版本：** V1.1.2、V1.1.4、V1.1.6、V1.1.7、V1.1.8。
- **风险：** V1.1.6 修改步态等接口；V1.1.7/V1.1.8 包含控制保护、网络、导航、定位、相机和 APP 标点相关变化。
- **项目处理：** 不混用旧 PDF 与在线接口值；以当前《软件开发指南》文件版本和现场固件确认结果为准。

## 已知差异

| 项目 | 旧 PDF V0.1.0 | 在线开发资料 | 项目处理 |
|---|---:|---:|---|
| 平地敏捷步态 | `12` | `0x3002` | 绑定现场版本，不硬编码通用值 |
| 楼梯敏捷步态 | `13` | `0x3003` | 第一阶段不开放楼梯 |
| Sleep | bool | V1.1.7 改为 int | 解析按版本处理，控制保持门控 |
| GOS 点云/IMU | 旧文档受限 | V1.1.7 新增 | 确认版本后再使用 |
| ROS2 跨版本 | 有兼容风险 | V1.1.8 修复相关问题 | 业务首选 basic_server |

## 仍需厂商或现场确认的事项

1. basic_server 导航命令字典与具体导航页面的差异；
2. TCP 上导航响应与主动状态帧的交织方式；
3. GOS 的官方视频转码方案和硬件插件；
4. 当前固件对第三方 basic_server 长连接的许可；
5. Web 控制的权限、并发和审计要求。

## 版本与文件核验补充

- 产品手册缓存文件 SHA-256：`7a115c7c82becf709971f1e84dcb86caa0bdcf0438df240165c62c6ac07d59b1`。
- 软件开发手册缓存文件 SHA-256：`7f816a52e647db21bddcf06a1df93728b8b8891ec317b9d5cb77217edd8bb540`；两份缓存副本哈希一致。
- 上述两份原始 PDF 未上传仓库，仅保存受控本地资料的摘要和哈希；如需上传，须由用户另行明确授权仓库范围。
