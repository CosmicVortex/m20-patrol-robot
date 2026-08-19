# Changelog

所有版本变更记录遵循 [Keep a Changelog](https://keepachangelog.com/) 规范。

## [Unreleased]

### 新增
- 支持M20 Pro机器狗安保巡逻监控系统
- 实现状态监控、视频回传、运动控制、导航管理功能

### 修复
- 修复代码块污染问题
- 修复gimbal/connect缺少username参数
- 补充紧急停止接口文档

## [V1.2] - 2026-08-18

### 优化
- 文档体系规范化，编号00-08连续
- API路径与router.py对齐
- 统一版本号V1.2
- 交叉引用有效性验证

### 修复
- 修复故障排查命令错配（navigation/status → motion/status）
- 修复gimbal关键方法格式不统一
- 补充work-orders/create和update路径说明

## [V1.1] - 2026-08-16

### 新增
- 实现basic_server协议通信层
- 实现运动控制服务
- 实现导航控制服务

### 修复
- 修复心跳禁用问题（P0）
- 修复状态映射字段缺失问题（P1）

## [V1.0] - 2026-08-14

### 新增
- 初始项目结构
- Web UI基础框架
- 配置文件管理
