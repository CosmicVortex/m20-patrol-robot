# 山猫 M20 ROS2 / DDS 接口总览

**文档版本：** V1.0.0  
**适用型号：** 山猫 M20、山猫 M20 Pro  
**适用软件包版本：** V1.1.7 及以后  
**更新日期：** 2026-06-18

---

## 前置阅读

[对外通信方式](./communication-overview.md)

---

## 1. ROS2/DDS 接口简介

机器人内部使用 **DrDDS**（基于 FastDDS 的中间件）进行跨进程通信，部分常见必要话题已对外开放，以供开发者在 GOS 主机或外接主机上使用。

> **注意：** 出于计算资源和系统完整性的考虑，开发者应尽量避免在 AOS 或 NOS 主机上开发。

### 1.1 版本兼容说明

山猫 M20/M20 Pro 使用的操作系统版本为 **Ubuntu 20.04**，其上运行的 DDS 为 **DrDDS**（基于 FastDDS 封装），ROS 版本均为 **ROS 2 Foxy**。

如果想让外部主机和山猫 M20 正常通信，需保证底层都使用 **Fast DDS** 作为通信标准：

**方式一：直接使用 Fast DDS 通讯**
- 目前适配版本为 Fast DDS v2.14，支持向下兼容，高版本未测试

**方式二：使用 ROS 2 通讯**
- 在 ROS 2 中配置 Fast DDS 作为底层中间件（RMW）
- 但机器人本体主机的 ROS 2 Foxy 版本可能会与外部主机的 ROS 2 版本存在兼容性差异，导致看不到话题或数据解析错误
- 如必须使用 ROS 程序，需参考以下 ROS 版本兼容关系

| 山猫 M20/M20 Pro 版本 | 外部主机 ROS 版本 |
|---|---|
| V1.1.7 以前版本 | ROS 2（Foxy、Humble） |
| V1.1.7 及以后版本 | ROS 2（Foxy、Humble、Jazzy） |

### 1.2 外接主机环境配置

```bash
# 确保 DDS domain ID 与机器人一致（同一网络下所有设备必须相同，否则互相不可见）
export ROS_DOMAIN_ID=0
```

---

## 2. 常见运维指令

> **注意：** 在机器人内部主机上使用 ROS2 工具接收话题、查看频率等前，需要 `source /opt/robot/scripts/setup_ros2.sh` 环境变量。
>
> **注意：** 建议使用 ROS2 工具接收话题、查看频率等前，通过 `su` 获取管理员权限，以确保相关指令可正常执行。

### 2.1 节点监控

```bash
ros2 node list          # 列出当前运行的所有节点
ros2 node info <name>   # 查看节点详细信息
```

### 2.2 话题运维

```bash
ros2 topic list         # 列出所有活跃话题
ros2 topic echo <name>  # 实时打印消息内容
ros2 topic hz <name>    # 显示发布频率
ros2 topic info <name>  # 查看发布者和订阅者
```

### 2.3 服务运维

```bash
ros2 service list       # 列出所有可用服务
ros2 service info <name>            # 查看服务类型
ros2 service call <name> <type> "{}"  # 调用服务
```

### 2.4 守护进程与环境

```bash
ros2 daemon start       # 启动守护进程
ros2 daemon stop        # 停止守护进程
echo $ROS_DOMAIN_ID     # 检查 domain ID
```

---

## 3. 完整话题列表

完整话题列表参见 [ROS 2 / DDS 话题速查](./ros2-topic-reference.md)。

---

**文档版本：** V1.0.0  
**更新日期：** 2026-06-18  
**版权归属：** 杭州云深处科技
