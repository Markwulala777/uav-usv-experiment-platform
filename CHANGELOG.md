# 更新日志

本文件记录此仓库的所有重要变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

本日志只记录 `uav-landing-experiment-platform` 平台仓库本身的变更，不转录 vendored 第三方子项目各自独立的更新日志。

未发布的变更应先写入 `[Unreleased]`；发版时将其归档为 `## [0.x.y] - YYYY-MM-DD`，并同步创建对应的 Git tag `v0.x.y`。

## [Unreleased]

本节记录尚未发布的变更。

### 变更

- 仓库名称由 `uav-usv-experiment-platform` 调整为 `uav-landing-experiment-platform`，默认运行时目录同步调整为 `~/uav-landing-experiment-platform-runtime`，默认实验输出目录同步调整为 `~/uav-landing-experiment-runs`。
- 加固 fresh Ubuntu 20.04 部署链路：README 补充 `python3-colcon-common-extensions` 与 `MicroXRCEAgent v2.4.3` 安装说明，`bootstrap_mixed_stack.sh` 新增 `MicroXRCEAgent` 早期预检，并将 `px4_msgs` / `px4_ros_com` 默认 ref 固定为已验证 commit SHA。
- 强化 `scripts/apply_overlay.sh` 的安全保护：在执行 overlay 与遗留路径清理前，显式校验 PX4 与 XTDrone 目标路径不是危险路径、是 git worktree，且带有项目标记文件。

## [0.3.0] - 2026-04-05

### 新增

- 新增 `AGENT.md`，为 Codex 等代码代理补充仓库级操作指南，覆盖优先阅读文档、默认改动区域、mixed-stack 启动顺序、frame/time 硬约束以及验证与排障入口。
- 新增研究层统一接口包与 baseline 架构骨架：`mission_stack_msgs`、`platform_interface`、`mission_manager`、`landing_decision`、`trajectory_planner`、`controller_interface`。
- 新增 `mission_stack_minimal.launch.py`、`mission_stack_full.launch.py` 以及三场景 launch 入口；保留 `baseline_minimal.launch.py`、`phase_b_minimal.launch.py` 和 `full_landing_mission.launch.py` 作为兼容入口。
- 新增 `scripts/run_chain_validation.sh` 与 `scripts/run_ugv_motion_baseline.sh`，为场景 1/2/3 提供单一真入口，其中场景 2 使用固定 `ugv_0` 低速运动基线。
- 新增 `metrics_evaluator/geometry_consistency` 节点与 `geometry_consistency_report.json` 产物，用于验证 platform、landing zone 与 relative state 的几何一致性。

### 变更

- 将接口包命名统一为 ROS 1 `platform_interface_ros1` 与 ROS 2 `platform_interface` / `mission_stack_msgs`，同时完成相关脚本、launch 入口和仓库级文档对齐。
- 将研究层主链收敛为单一 active state 和 active reference：`/relative_state/active` 与 `/controller/reference_active`。
- 将 PX4/NED 输出边界从 `landing_guidance/px4_offboard_bridge` 迁移并固定到 `controller_interface/px4_offboard_bridge`。
- 将 `deck_description` 职责并入 `platform_interface`，并将旧 `frame_audit` 逻辑迁入 `metrics_evaluator` 内部 debug helper。
- 更新 README、CHANGELOG、baseline 相关设计文档与包级 README，使当前实现与文档表述对齐。
- 将场景 1/2/3 验收口径收敛为链路验证而非 touchdown success，并在 `summary.json` 中显式区分 `mission_outcome` 与 `chain_validation_passed`。
- 冻结场景 1 的 canonical target 为 `zhihang1.world` 中的 `landing1`，冻结场景 2 的 canonical dynamic baseline 为 `outdoor2_precision_landing.launch` 中 `ugv_0` 的 10 Hz 低速脚本运动。
- 将 ROS 1 world bring-up 收敛为单一高层入口 `run_ros1_world.sh --scenario <scenario_id>`，并将场景 1/2/3 的 world launch/world file 映射集中到共享 registry 中维护。
- 将场景 3 `maritime_usv_qr` 也纳入 `run_chain_validation.sh` 的单一真入口，并补齐 `frame_audit`、`geometry_consistency` 与 `summary_writer` 的链路验证配置。
- 将场景 2 的链路验证 world 收敛为 `ugv_0` + static `iris_0` truth carrier，并在 `run_ugv_motion_baseline.sh` 中保留受控的 Gazebo model-state fallback；当前 runtime 还额外补齐了 `ros_controllers/velocity_controllers` 与 `effort_controllers`，使纯 `catvehicle` 控制链成为 canonical 验证路径。
- 完成一次基于 `baseline_minimal` 的 Gazebo/PX4/`ros1_bridge`/ROS 2 research 全栈联调，确认主链能够产出 `run_metadata.json`、`events.jsonl`、`summary.json` 和 `frame_audit_report.json`。
- 完成场景 1 与场景 2 的 canonical chain-validation 运行，最新通过 run 分别为 `scenario_1_static_ground_qr/run_20260405_113721` 与 `scenario_2_ground_moving_qr/run_20260405_115811`。
- 将场景 3 `maritime_usv_qr` 也纳入 canonical chain-validation，并验证 `run_chain_validation.sh --scenario scenario_3_maritime_usv_qr` 能以同口径产出 `chain_validation_passed=true`，对应 run 为 `scenario_3_maritime_usv_qr/scenario3_chain_pass_164525`。
- 复跑场景 1/2/3 的单一真入口并确认 shell 级退出码为 `0`；其中场景 2 在 `UGV_GAZEBO_FALLBACK_MODE=never` 条件下仍通过链路验证，对应 run 为 `scenario_2_ground_moving_qr/catvehicle_only_160526`。

### 修复

- 修复在 `set -u` 严格 shell 环境下 source ROS Noetic setup 脚本时触发的 `ROS_DISTRO: unbound variable` 问题，统一为 `run_sim.sh`、`run_mission.sh` 和 `bootstrap.sh` 增加安全的 `source_setup()` 包装，避免运行与部署入口在新终端环境中启动失败。
- 更新 `stop_platform.sh` 的目标进程匹配规则，使其与当前 baseline launch 名、控制接口包拆分以及新的 research-layer 可执行入口保持一致。
- 修复 `run_chain_validation.sh` 在预清理和退出 cleanup 阶段误杀自身及其父 shell 的问题，为 `stop_platform.sh` 增加多 PID 排除逻辑，使 chain-validation 真入口可直接挂入自动化而不会被预清理误杀。
- 修复 XTDrone `outdoor2_precision_landing.launch` 在当前 Noetic/PX4 runtime 下的兼容性问题，包括 `catvehicle` 包搜索路径、`xacro` 调用方式、旧版 `mavros` 参数、以及 `catvehicle` Python 2 shebang。

## [0.2.1] - 2026-04-01

### 新增

- 补充 baseline 工件与验证支撑，包括 frame audit、experiment manager、deck description、时间基准说明和验收清单。
- 新增 `stop_platform.sh`，用于本地运行时环境的一键停机，并将其纳入 bootstrap 安装出来的脚本集合。

### 变更

- 将平台目标收敛到已验证的 mixed ROS1/ROS2 组合，明确 Ubuntu 20.04、Gazebo Classic 11、ROS Noetic、ROS 2 Foxy 和 PX4 v1.14.0 的协作基线。
- 冻结 baseline 坐标与时间约定，明确研究层保持 `world` ENU，`use_sim_time` 以 Gazebo 为准，并把 PX4 坐标转换边界限定在 `controller_interface/px4_offboard_bridge`。
- 更新 mixed-stack bring-up、PX4 启动流程和仓库文档，使运行步骤、接口边界与验证口径保持一致。

### 修复

- 稳定 PX4 local-origin reset 场景下的 OFFBOARD 行为，桥接节点在重新解析本地原点期间持续发送心跳并保持最后有效的本地 NED 设定值，降低控制掉线风险。

## [0.2.0] - 2026-03-30

### 新增

- 新增 mixed ROS1/ROS2 runtime 支持，包括 `ros2_research_ws_src/`、`ros2_px4_ws.repos`、混合栈 bootstrap 入口以及分终端运行脚本。
- 新增 truth-level 研究层基础包与 ROS 1/ROS 2 桥接链路，包括 `platform_interface_ros1`、`platform_interface`、`relative_estimation`、`landing_guidance`、`safety_manager`、`touchdown_manager` 和 `joint_bringup`。

### 变更

- 更新 landing workflow 和实验运行路径，使 Gazebo/VRX、PX4、MicroXRCEAgent、`ros1_bridge` 与 ROS 2 研究层能够按新的联合架构协同启动。
- 调整 README、PX4 overlay 和 XTDrone 任务脚本，使仓库说明与 mixed-stack 运行方式对齐。

## [0.1.0] - 2026-03-30

### 新增

- 初始化 `uav-usv-experiment-platform` 仓库（现 `uav-landing-experiment-platform`），纳入 ROS catkin workspace source snapshot、PX4/XTDrone overlay、基础 bootstrap 与运行脚本。
- 建立面向迁移部署的仓库骨架，明确通过 bootstrap 在仓库外构建运行时工作区，并从上游获取 PX4 与 XTDrone。
- 收录平台相关基础文档与依赖说明，形成可归档、可在另一台 Ubuntu 机器上复现实验环境的最小基线。

[Unreleased]: https://github.com/Markwulala777/uav-landing-experiment-platform/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Markwulala777/uav-landing-experiment-platform/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Markwulala777/uav-landing-experiment-platform/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Markwulala777/uav-landing-experiment-platform/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Markwulala777/uav-landing-experiment-platform/releases/tag/v0.1.0
