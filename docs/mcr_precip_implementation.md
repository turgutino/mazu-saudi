# MCR-Precip 本地实现说明

## 当前交付

本仓库已经提供论文 1 的可训练核心。实现位于 `src/mazu_saudi/mcr_precip/`，包含稳定张量合同、四类传播专家、机制路由、概率与分位数输出、机制适用性软先验、反事实方向损失、训练步骤和版本化模型包。

这是一条经过自动测试的工程垂直切片。合成数据仅证明前向、反向、参数更新和制品保存可运行，**不构成任何论文结果或科学证据**。

## 输入合同

- `dynamic [B,T,C,H,W]`：起报时刻前可用的降水和大气动态场；
- `static [B,S,H,W]`：地形等静态场，第一通道约定为高程；
- `mechanism [B,8]`：`motion_u, motion_v, transport_strength, instability, moisture, upslope_flow, terrain_slope, recent_persistence`；
- `availability [B,3]`：近期降水、大气场、地形的可用程度；
- `lead_hours [B]`：仅允许 1、3、6 小时；
- 训练标签为极端事件发生图和未来窗口累计降水图。

缺测值必须先由数据适配器填充为有限数，并同时写入 `availability`；不可观测标签使用 NaN，在损失中被排除，不能转成普通负例。模型接口没有区域 ID，防止路由器记忆大陆身份。

## 四类专家

1. 平流专家用机制状态中的运动向量对最近时刻隐场作可微上游采样；
2. 对流生成专家组合局地卷积、空洞卷积和局地最大值，并受不稳定度/水汽调制；
3. 地形专家显式计算高程梯度，并用迎风分量调制地形响应；
4. 持续—衰减专家融合最近隐场和历史均值，并随预报时效学习衰减。

路由器只使用机制状态、模态可用性和时效。模态门控在 softmax 前抑制不具备输入条件的专家。输出包括极端发生概率、单调非交叉降水分位数、正值不确定性和专家权重。

## 与参考工程的关系

本实现从参考工程继承的是设计经验：时间因果、特征分组、时空编码、概率评估和模型元数据。由于部分参考仓库没有许可证，代码为 clean-room 实现，没有复制其源码。同日规则标签、随机格点切分、测试集选阈值和区域身份特征不进入正式方法。

## 工程烟测

工程烟测脚本 `scripts/train_mcr_precip_smoke.py` 已移除（未接入真实数据前价值有限）；`tests/test_mcr_precip_training.py` 已覆盖训练步骤更新和模型包保存/加载的等价测试，可通过以下命令验证核心训练闭环：

```bash
conda run -n ml python -m pip install -e .
conda run -n ml python -m unittest tests.test_mcr_precip_training -v
```

## 下一数据阶段

当前沙特 2025 指标文件适合做适配器烟测，但不能单独支撑跨区域论文结论。下一步应按 `valid_time / availability_time / forecast_origin` 建立 Historical Common-Core，生成事件级冻结切分，再分别实现 IMERG、历史 forecast/reforecast、地形和 MAZU 的数据适配器。模型核心不应随具体数据源字段变化。

## 2025 沙特真实数据代理任务对比

仓库已增加一个严格收敛的 24 小时真实数据实验：

```bash
conda run -n ml python scripts/compare_mcr_real_data.py \
  --orography-source /Volumes/E/气象数据/saudi_region_output/indicators/saudi_indicators_20250823.nc \
  --stride 4 \
  --seeds 42,43,44 \
  --epochs 20 \
  --hidden-channels 8
```

协议为 2025 年 1–5 月训练、6 月验证、7–12 月测试。概率 Platt 校准和 CSI
阈值均只在 6 月拟合。任务标签是 `flash_flood_risk>=2` 的内部代理标签，不是独立
山洪真值。对比使用相同的 stride=4 网格和输入，包含匹配 HGB、无机制先验 MoE 和
机制先验 MCR；MCR 只启用适用性先验，没有在本次有限实验中加入真实反事实训练。

正式三种子结果位于：

- `experiments/mcr_precip_2025_proxy/results.json`
- `experiments/mcr_precip_2025_proxy/report.md`

结果不支持将 MCR 作为比赛性能贡献：HGB、普通 MoE、MCR 的平均 PR-AUC 分别为
0.0759、0.0590、0.0542；MCR 的 FAR 为 0.9502。机器可读状态固定为
`research_only_not_adopted`。MCR 仍可作为已实现研究原型展示，但比赛主结果继续
使用经过验证的轻量 HGB，并明确其单年代理标签边界。
