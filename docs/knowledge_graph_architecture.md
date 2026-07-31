# 预测解释知识库与知识图谱架构

## 1. 建设目标

本系统的知识图谱不负责“替模型预测”，而负责把一次预测拆成可核验的问题：模型为什么给出该分数、当前气象条件与哪些机制相容、风险政策如何映射、哪些历史过程可类比、每条说明来自哪里且有什么限制。

当前实现覆盖暴雨、山洪、极端高温和沙尘暴。运行入口是 `POST /api/v1/predictions`，随后可用 `GET /api/v1/knowledge-graph/{prediction_id}` 查询该次预测的解释视图。

## 2. 三层模型

### 领域知识层

版本化知识包位于 `backend/data/knowledge/prediction_knowledge.json`，包含：

- 灾种专属相似度维度和权重；
- 机制、适用灾种/地域、所需指标信号和信号权重；
- 机制所引用的文献 ID；
- SWEET 对齐所使用的本地概念后缀。

文献元数据继续由 `ontology/literature_sources.json` 维护，SWEET 映射继续由 `ontology/sweet_alignment.json` 维护。运行时只投影与当前查询有关的来源和概念，不导入完整 SWEET。

### 历史案例层

案例保存事件时间、中心位置、适用灾种、气象指标剖面、核验状态、可靠度和来源。首批案例从 `reference_code/mazu-saudi-warning` 的结构化事件中裁剪而来，但明确区分：

- `reference-reviewed`：在参考工程中经过人工或站点回放审查；
- `proxy-weather-episode`：由气象极值识别的过程，不等同于独立核验灾情。

这些案例是种子库，不是完整沙特灾情档案。上线前应继续接入官方事件、站点记录和灾情影响数据，并保留来源快照与授权信息。

### 预测解释层

每次请求按 `prediction_id` 动态生成查询相关子图，不持久复制领域知识。图中证据身份保持分离：

| 证据类型 | 回答的问题 | 禁止解读 |
|---|---|---|
| 模型归因 | 哪些输入影响模型输出 | 物理因果 |
| 政策规则 | 为什么得到该风险等级 | 灾害发生概率 |
| 机制相容性 | 当前指标组合与什么过程一致 | 个例因果证明 |
| 文献/本体 | 机制概念从哪里来 | 本次天气事实 |
| 历史类比 | 过去什么过程在若干维度相似 | 当前结果必然复现 |

## 3. 推理语义

机制推理使用 `CONSISTENT_WITH` 和 `FAVOURS`，不使用 `CAUSES`。每个指标先依据自身物理方向归一化为相容度：温度、CAPE、降水等越高越有利；能见度、土壤湿度等越低越有利。机制得分是已获得信号的加权相容度，再乘数据覆盖率。适用地域约束在推理前执行。

边同时返回：

- `semantics`：`asserted`、`derived` 或 `computed`；
- `confidence`：存在量化结果时的 0–1 分数；
- `rationale`：为什么建立这条边；
- `evidenceIds`：可回溯文献或知识记录。

## 4. 相似案例算法

候选首先必须满足：灾种匹配且案例日期严格早于预报起报时刻。最终分数不使用当前模型概率，由三部分组成：

1. 天气形态：灾种配置的指标归一化距离；
2. 空间背景：案例中心与预测空间单元中心的 Haversine 距离，经 600 km 指数尺度转换；
3. 季节窗口：月份的循环距离。

随后应用两个透明惩罚：可比较气象指标覆盖率、案例可靠度。API 返回每个维度的分数、权重、解释、总覆盖率和核验状态，前端逐项展示。

当前的温度案例用“2 m 瞬时/目标温度”近似比较“日最高温”，知识包将该维度标为 `approximate` 并额外降权。这是已知数据契约缺口，后续应统一为同一时间聚合语义。

## 5. SWEET 与外部本体边界

SWEET 是约 200 个模块的中层地球科学本体，适合稳定概念对齐，不适合直接充当预测运行或证据模型。项目采用固定 commit 的 SKOS 映射：

- 精确语义才允许 `exactMatch`；
- 带高度、时间聚合或项目范围限定时使用 `closeMatch`/`broadMatch`；
- 有利状态不映射为已发生灾害事件；
- 预测、模型归因、风险政策、相似度和文献断言均使用 MAZU 本地语义。

灾害风险方面借鉴 DMDO/DPO 对 Hazard、Disaster、Intensity、Exposure、Vulnerability 等概念的分离。当前版本没有足够的暴露度与脆弱性数据，因此风险节点只声明现有政策实际使用的组成部分，不虚构社会影响知识。

## 6. 数据扩展流程

新增机制时：先确定灾种与适用环境，再配置可观测信号和权重，最后添加经过审核的文献 ID 与 SWEET 映射。新增案例时：必须提供事件时间、空间、核验状态、来源、可靠度；气象指标必须记录单位和聚合语义，不得从叙述中猜值。

建议下一批建设顺序：

1. 从 `/Volumes/E/气象数据/saudi_region_output` 生成统一的逐过程指标剖面；
2. 接入可追溯官方事件/告警记录，把气象代理过程与观测灾害事件连接但不合并；
3. 用历史预测归档建立“forecast-to-observation” analog，而不是混用分析场和预测场；
4. 用时间分块验证相似度权重，并报告案例召回稳定性；
5. 案例量达到数万后，再把当前仓内索引替换为 PostgreSQL/pgvector 或图库，保持 API 契约不变。

## 7. 研究依据

- [SWEET 官方说明](https://esipfed.github.io/sweet/)：模块化中层地球科学本体及 Turtle/OWL 发布方式。
- [A Formal Framework for Disaster Risk Properties](https://ceur-ws.org/Vol-3637/paper48.pdf)：DMDO/DPO 对灾害风险属性、SOSA/SSN、OWL-Time、GeoSPARQL 和 PROV-O 的建模建议。
- [Probabilistic Quantitative Precipitation Forecasts Based on Reforecast Analogs](https://journals.ametsoc.org/view/journals/mwre/134/11/mwr3237.1.xml)：基于多变量天气形态与受限时空窗口的类比预报思路。
- [Example-Based Concept Analysis Framework for Deep Weather Forecast Models](https://journals.ametsoc.org/view/journals/aies/aop/AIES-D-24-0079.1/AIES-D-24-0079.1.xml)：区分模型内部概念表示与领域机制解释的必要性。
