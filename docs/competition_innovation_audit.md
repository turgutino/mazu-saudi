# 竞赛创新性与工程完成度审计

## 1. 结论

当前方案**足以形成一套有竞争力的本地化工程作品，但尚不足以把“已验证的算法突破”
作为唯一卖点**。

真正的问题不是没有继续接入通用大模型或盲目融合更多外部数据，而是当前最强的
“真实证据”和最强的“原创方法”分属两条尚未接通的链：

- `warning_demo` 使用真实 2025 数据完成了数据、指标、`t→t+1` 模型、知识证据、
  Agent、CAP 和审计闭环，但模型标签主要是规则代理标签，只有单年季节外推证据。
- MCR-Precip 已实现机制约束四专家路由、模态可用性、不确定性和反事实损失，
  但只完成合成训练闭环，尚无真实样本外性能结果。
- 早期 MAZU Atlas 合成演示服务已从仓库删除；MCR-Precip 只保留科研内核、真实对比
  负结果和论文资产，不作为第二套产品能力展示。

因此，比赛主叙事应从“我们训练了一个更大的模型”改为：

> 面向单年、小样本和传感器缺测的沙特场景，构建一条物理可解释、证据可追溯、
> 失败会拒识、可离线部署的多灾种早期预警原型。

这是一项成立的**系统与可信工程创新**。MCR-Precip 是其中的**方法创新候选**，
必须明确标为已实现核心、待真实数据验证，不能宣称已经优于基线。

## 2. 比赛硬性交付物

依据 `docs/requirement/` 四张要求图，英文主件至少包括：

| 必交件 | 格式 | 当前状态 |
|---|---|---|
| Application Solution Report | Word | 尚无正式 `.doc/.docx` |
| Product Prototype and Model Design | Word | 尚无正式 `.doc/.docx` |
| Presentation Deck | PPT | 尚无正式 `.ppt/.pptx` |
| Prototype Demonstration Video | 视频，不超过 3 分钟 | 尚无视频 |

中文对应版本是可选补充。现有论文 Markdown、分析报告和中期 PDF 是内容资产，
不能直接替代上述上传字段。

参赛承诺还要求数据来源合法且在材料中说明、作品原创且不侵犯第三方权益；涉及地图
时需使用审核地图来源并遵守地图表示规定。当前仓库未发现完整的数据授权清单、数据卡、
项目许可证或地图合规记录，这些属于提交前阻断项。

## 3. 已有能力的证据分级

| 能力 | 状态 | 可用于比赛的表述 |
|---|---|---|
| 沙特区域数据裁剪与指标计算 | 已实现、真实数据运行 | 真实工程能力 |
| 2025 数据覆盖 | DS1 12 月、DS2 364 天、SST 365 天、DS10 273 天 | 单年本地化数据底座 |
| 高温 `t→t+1` | 2025 上半年训练、下半年测试；PR-AUC 0.795、CSI 0.552 | 代理标签上的季节外推结果 |
| 山洪 `t→t+1` | PR-AUC 0.089、POD 0.100、FAR 0.803、CSI 0.071 | 有排序信号，未达运营可靠 |
| 沙尘 `t→t+1` | PR-AUC 0.164、FAR 0.865、CSI 0.121 | 研究型演示结果 |
| 阈值重校准与 STGNN 融合 | 跨测试半期不泛化，未采用 | 可信治理与负结果 |
| DeepSeek Agent + KG + CAP | 已实现，真实工具调用和静态回放 | 受证据约束的解释/交付层 |
| MCR-Precip | 核心代码与自动测试完成 | 原创方法原型，尚无真实效果结论 |
| MCR-Precip研究线 | 科研内核与真实负结果保留，demo产品已删除 | 未来研究资产，不进入比赛界面 |

`warning_demo` 的 “121/121 audit passed” 只说明现有数字可回溯到数据和制品，
不证明代理标签等于真实灾害，也不证明跨年、跨区域或业务泛化。

## 4. 创新性是否充分

### 4.1 足以成立的三项比赛创新

1. **干旱区本地化物理指标链**
   从全球多源产品裁剪沙特及红海/波斯湾邻域，构建短历时降水、水汽输送、
   对流不稳定、热胁迫、距平和数据可用性等可追溯指标。亮点不是变量数量，
   而是填充值清洗、网格对齐、缺测状态和指标复算审计。

2. **灾种差异化且会暴露失败的可信预警链**
   系统不以 ROC-AUC 掩盖稀有事件操作点，公开 POD、FAR、CSI、校准和失败案例；
   山洪阈值重校准、STGNN 融合不泛化时不部署。对比赛而言，这比继续堆一个
   没有可靠证据的大模型更能体现工程成熟度。

3. **预测—证据—行动分层的轻量产品闭环**
   核心预测不依赖 LLM；知识图谱和 DeepSeek 只读取冻结预测与证据，CAP 负责结构化
   交付，离线页面仍可运行。这个边界适合“可嵌入 MAZU、可审计、可降级”的定位。

### 4.2 只能作为候选的算法创新

MCR-Precip 的机制状态路由、机制适用性先验、物理反事实方向约束和缺测拒识，
比普通 GBDT 或“多尺度 + MoE”更有原创潜力。但目前没有真实训练、强基线、
反事实消融或 OOD 结果，只能写成：

> We implemented a trainable mechanism-constrained routing core and verified
> its software contracts on synthetic data; real-data comparative validation
> remains future work.

不能写成 “outperforms existing models”“improves cross-region generalization”
或“operational 1/3/6-hour forecast”。

### 4.3 不值得为了比赛临时追加的内容

- 不要仅为显得先进再接一个通用大模型。`warning_demo` 已有 DeepSeek 工具编排，
  再增加模型不会补上气象真值和泛化证据。
- 不要在来源、许可和时间语义未解决时临时融合外部数据。新增数据会扩大合规、
  对齐和泄漏风险。
- 不要恢复已删除的合成 Atlas 概率，或与`warning_demo`的真实回顾性结果混在一张图中。
- 不要把山洪风险分数称为真实山洪概率，把规则引擎称为 ground truth。
- 不要使用“提前 3 小时”“85% 概率”“零人员伤亡”等虚构场景数字作为已实现结果。

## 5. 比赛前的最小增强路线

### P0：先消除提交阻断

1. 为 DS1–DS11、人口、文献、案例和第三方代码建立来源—许可—用途—是否可再发布清单。
2. 明确团队对 `warning_demo` 子树、图片、模型制品和 DeepSeek 输出的原创/授权边界。
3. 对所有正式图片做地图合规检查；无法确认来源的国界图改为无国界经纬网格图。
4. 从现有材料生成两份英文 Word、英文 PPT 和不超过三分钟的英文演示视频。

### P1：把产品故事接成一条真实链

选择一个高温回放作为主案例，因为它是当前最强结果；选择一个山洪失败案例作为
“模型拒识/人工复核”的次案例。演示顺序固定为：

```text
数据来源与起报时刻
→ 指标和缺测状态
→ warning_demo 的真实 T+1 回放
→ 概率、POD/FAR/CSI 与失败边界
→ 证据检索和 CAP Exercise 输出
→ 明确MCR真实对比未通过采用门，当前产品不展示MCR
```

### P2：只做一个能增强创新证据的实验

若时间允许，不追求完整 MCR 论文实验，只做一个预注册的小实验：

- 同一 2025 blocked split；
- HGB、固定邻域、STGNN、MCR 核心四个同口径对照；
- 只报告高温与强降水代理标签；
- 固定训练/验证/测试，阈值只在验证集确定；
- 报告 PR-AUC、CSI、POD、FAR、Brier/ECE 和按日期 bootstrap；
- 若 MCR 无稳定提升，仍保留为可解释的下一代原型，不修改主结果叙事。

## 6. 推荐的三条贡献表述

英文材料中建议只保留三条主贡献：

1. **A quality-controlled Saudi multi-source hazard indicator pipeline**
   with traceable provenance, missingness states and reproducible audits.
2. **An honestly verified lightweight multi-hazard warning prototype**
   that separates forecast probability, physical evidence and alert policy.
3. **A trainable mechanism-constrained routing design**
   for interpretable degradation under sensor missingness, presented as an
   implemented research prototype rather than a validated operational model.

## 7. 最终判断

- 如果目标是“按时提交并形成完整、有说服力的比赛作品”：**创新性基本够，
  但必须以本地化可信系统创新为主，并立即补齐四件英文交付物与合规附件。**
- 如果目标是“以新模型性能作为核心获奖理由”：**目前不够。** MCR-Precip
  缺真实实验，`warning_demo` 又受单年代理标签限制。
- 没有继续引入外部大模型不是主要短板；真正短板是新方法、真实结果和产品页面
  尚未接成同一条可审计证据链。
