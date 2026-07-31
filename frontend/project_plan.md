# 极端天气预测智能体应用

## 1. Project Description
一个由预测模型产生数值结果、预测智能体负责编排、解释引擎生成可验证解释、知识图谱保存推理证据链的极端天气预测应用。

核心原则：智能体负责组织和解释，预测模型负责计算。大模型不直接编造降水量、概率或预警等级。

## 2. Page Structure
- `/` — 预测仪表盘（概览、近期预测、统计数据）
- `/workspace` — 预测工作台（选择区域、灾种、时效、模型，发起预测）
- `/prediction/:id` — 预测结果 + 解释页面（风险概率、等级、特征贡献、命中规则、物理机制、相似历史事件）
- `/prediction/:id/graph` — 解释证据图谱（围绕当前预测的局部子图）

## 3. Core Features
- [ ] 预测工作台：区域选择 → 灾种选择 → 时效选择 → 模型选择 → 发起预测
- [ ] 预测结果展示：风险概率、风险等级、时空范围、不确定性、模型版本
- [ ] 模型解释：SHAP 特征贡献图、关键变量排序、与正常值偏差
- [ ] 物理机制解释：气象因果链（可降水 → CAPE → 对流 → 强降水）
- [ ] 风险决策解释：命中规则列表、阈值对比、区域敏感度
- [ ] 解释证据图谱：ForecastCase → Prediction → RiskAssessment → Warning 链路可视化
- [ ] 相似历史事件查询与对比
- [ ] 预测报告生成（智能体编排）

## 4. Data Model Design
（前端展示用，实际数据由后端 Python 服务提供）

### ForecastCase
| 字段 | 说明 |
|------|------|
| case_id | 预测案例唯一标识 |
| initial_time | 起报时间 |
| target_time | 目标时间 |
| lead_time_hours | 预报时效（小时） |
| region_id | 区域标识 |
| feature_version | 特征版本 |
| input_hash | 输入数据哈希 |

### PredictionResult
| 字段 | 说明 |
|------|------|
| prediction_id | 预测唯一标识 |
| model_id / model_version | 模型标识与版本 |
| hazard | 灾种类型 |
| probability | 原始概率 |
| calibrated_probability | 校准后概率 |
| predicted_class | 预测类别 |
| uncertainty | 不确定性 |
| important_features | 重要特征贡献 |

### RiskAssessment
| 字段 | 说明 |
|------|------|
| risk_level | 风险等级（绿/黄/橙/红） |
| triggered_rules | 触发的规则列表 |
| region_sensitivity | 区域敏感度 |
| confidence | 置信度 |

### PredictionExplanation
| 字段 | 说明 |
|------|------|
| feature_contributions | 特征贡献列表 |
| rule_hits | 命中规则 |
| physical_mechanisms | 物理机制链 |
| similar_events | 相似历史事件 |
| supporting_evidence | 支持证据 |

## 5. Backend / Third-party Integration Plan
- 当前阶段：纯前端 Mock 数据展示，不连接后端
- 后续可接入 Python 后端 API（FastAPI/Flask）提供真实预测数据
- 知识图谱可视化使用前端图库（vis-network 或 d3-force）

## 6. Development Phase Plan

### Phase 1: 核心页面 UI 框架 + Mock 数据 ✅ 已完成
- 目标：完成四个核心页面的 UI 框架和交互流程
- 交付物：
  - ✅ 预测仪表盘首页（统计概览 + 近期预测列表 + 本周趋势图 + 动态记录）
  - ✅ 预测工作台（5 步向导：区域 → 灾种 → 时效 → 模型 → 确认，含模拟执行流程）
  - ✅ 预测结果 + 解释页面（概率概览、SHAP 特征贡献、命中规则、物理机制链、相似历史事件 — 5 个 Tab）
  - ✅ 解释证据图谱页面（力导向布局、拖拽交互、缩放平移、边标签、节点高亮关联）
  - ✅ StyleSystem 色彩体系（暖琥珀主色 + 暖青绿强调色 + 暖石辅助色）
  - ✅ 完整的 Mock 数据体系（区域、灾种、模型、预测结果、解释、知识图谱）
  - ✅ DM Sans + DM Serif Display 字体系统

### Phase 2: 智能体交互
- 目标：加入智能体对话式预测编排
- 交付物：智能体聊天界面 + 工具调用可视化 + AgentRun 记录

### Phase 3: 数据对接
- 目标：对接真实 Python 后端 API
- 交付物：API 层替换 Mock 数据