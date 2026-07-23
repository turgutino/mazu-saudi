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

```bash
conda run -n ml python -m pip install -e .
conda run -n ml python scripts/train_mcr_precip_smoke.py \
  --output /private/tmp/mcr_precip_smoke.pt --steps 5
```

## 下一数据阶段

当前沙特 2025 指标文件适合做适配器烟测，但不能单独支撑跨区域论文结论。下一步应按 `valid_time / availability_time / forecast_origin` 建立 Historical Common-Core，生成事件级冻结切分，再分别实现 IMERG、历史 forecast/reforecast、地形和 MAZU 的数据适配器。模型核心不应随具体数据源字段变化。
