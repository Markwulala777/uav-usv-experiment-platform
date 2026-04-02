# 更新日志

本文件记录此仓库的所有重要变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

本日志只记录 `uav-usv-experiment-platform` 平台仓库本身的变更，不转录 vendored 第三方子项目各自独立的更新日志。

未发布的变更应先写入 `[Unreleased]`；发版时将其归档为 `## [0.x.y] - YYYY-MM-DD`，并同步创建对应的 Git tag `v0.x.y`。

## [Unreleased]

本节记录尚未发布的变更。

### 新增

- 新增 `AGENT.md`，为 Codex 等代码代理补充仓库级操作指南，覆盖优先阅读文档、默认改动区域、mixed-stack 启动顺序、frame/time 硬约束以及验证与排障入口。

## [0.2.1] - 2026-04-01

### 新增

- 补充 Phase 1 工件与验证支撑，包括 frame audit、experiment manager、deck description、时间基准说明和验收清单。
- 新增 `stop_platform.sh`，用于本地运行时环境的一键停机，并将其纳入 bootstrap 安装出来的脚本集合。

### 变更

- 将平台目标收敛到已验证的 mixed ROS1/ROS2 组合，明确 Ubuntu 20.04、Gazebo Classic 11、ROS Noetic、ROS 2 Foxy 和 PX4 v1.14.0 的协作基线。
- 冻结 Phase 1 的坐标与时间约定，明确研究层保持 `world` ENU，`use_sim_time` 以 Gazebo 为准，并把 PX4 坐标转换边界限定在 `landing_guidance/px4_offboard_bridge`。
- 更新 mixed-stack bring-up、PX4 启动流程和仓库文档，使运行步骤、接口边界与验证口径保持一致。

### 修复

- 稳定 PX4 local-origin reset 场景下的 OFFBOARD 行为，桥接节点在重新解析本地原点期间持续发送心跳并保持最后有效的本地 NED 设定值，降低控制掉线风险。

## [0.2.0] - 2026-03-30

### 新增

- 新增 mixed ROS1/ROS2 runtime 支持，包括 `ros2_research_ws_src/`、`ros2_px4_ws.repos`、混合栈 bootstrap 入口以及分终端运行脚本。
- 新增 truth-level 研究层基础包与 ROS 1/ROS 2 桥接链路，包括 `deck_interface_ros1`、`deck_interface`、`relative_estimation`、`landing_guidance`、`safety_manager`、`touchdown_manager` 和 `joint_bringup`。

### 变更

- 更新 landing workflow 和实验运行路径，使 Gazebo/VRX、PX4、MicroXRCEAgent、`ros1_bridge` 与 ROS 2 研究层能够按新的联合架构协同启动。
- 调整 README、PX4 overlay 和 XTDrone 任务脚本，使仓库说明与 mixed-stack 运行方式对齐。

## [0.1.0] - 2026-03-30

### 新增

- 初始化 `uav-usv-experiment-platform` 仓库，纳入 ROS catkin workspace source snapshot、PX4/XTDrone overlay、基础 bootstrap 与运行脚本。
- 建立面向迁移部署的仓库骨架，明确通过 bootstrap 在仓库外构建运行时工作区，并从上游获取 PX4 与 XTDrone。
- 收录平台相关基础文档与依赖说明，形成可归档、可在另一台 Ubuntu 机器上复现实验环境的最小基线。

[Unreleased]: https://github.com/Markwulala777/uav-usv-experiment-platform/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/Markwulala777/uav-usv-experiment-platform/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Markwulala777/uav-usv-experiment-platform/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Markwulala777/uav-usv-experiment-platform/releases/tag/v0.1.0
