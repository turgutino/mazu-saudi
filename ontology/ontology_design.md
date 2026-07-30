# MAZU 全球观测机制适用性本体设计

## 1. 目的与边界

本体规定全球天气机制知识中允许出现的指标、天气状态、天气过程、适用环境、统计断言、
反例和预测约束类型。它是语义模式，不包含“某时某地出现了某个天气过程”之类的全球
观测实例。

本体规范名称为 **MAZU 天气机制本体**（MAZU Weather Mechanism Ontology，MWMO）。
后续依照该本体、从全球 2025 观测提取的实例集合才称为 **全球观测机制适用性知识图谱**
（Global Observational Mechanism Applicability Graph，GOMAG）。

| 层次 | 包含内容 | 不包含 |
|---|---|---|
| 本体 | 类、属性、关系类型、受控概念、SHACL 约束 | 全球观测实例、统计发现 |
| 本体关系视图 | 本体资源的可视化投影 | 知识图谱实例 |
| 知识图谱 | 状态实例、天气过程实例、证据断言、反例、来源 | 未经数据提取的虚构关系 |

不可违反的边界：

- `ExtremeWeatherState` 是气象极端状态，不是灾害影响事件。
- `HazardFavourableState` 是灾害有利气象条件，不是 `ObservedHazardEvent`。
- `ProxyLabel` 不能标记为独立灾害真值。
- 自动提取的 `EvidenceAssertion` 默认
  `eligibleForCausalExplanation=false`。
- 每条观测断言必须记录适用环境、来源运行、支持过程、反例和版本。
- 图谱提取本身属于从数据学习，必须在沙特测试期之前冻结。

## 2. 标准复用

| 关注点 | 采用标准 | 本项目用法 |
|---|---|---|
| 观测、属性、结果、采样 | [W3C SOSA/SSN](https://www.w3.org/TR/vocab-ssn/) | 复用 `Observation`、`ObservableProperty`、`FeatureOfInterest`、`Procedure` 和 `Result` |
| 观测概念模型 | [OGC OMS 3.0 / ISO 19156:2023](https://www.ogc.org/standards/om/) | 校验观测对象、观测属性、过程、结果、现象时间和结果时间的分离 |
| 空间对象和关系 | [OGC GeoSPARQL 1.1](https://www.ogc.org/standards/geosparql/) | 表达网格、区域、天气过程覆盖区及相交、包含等关系 |
| 时间与时段 | [W3C OWL-Time](https://www.w3.org/TR/owl-time/) | 表达天气过程、过程阶段、时刻、时段和滞后 |
| 来源追溯 | [W3C PROV-O](https://www.w3.org/TR/prov-o/) | 追溯数据、指标过程、提取运行、断言和预测约束 |
| 物理量与单位 | [QUDT](https://qudt.org/doc/2026/02/DOC_SCHEMA-QUDT.html) | 统一数量类型、单位和维度 |
| 气象变量名称 | [CF Metadata Conventions](https://cfconventions.org/) | 为指标保存 CF Standard Name，保留项目内部变量名映射 |
| 气象主题分类 | [WMO Codes Registry](https://codes.wmo.int/wis/topic-hierarchy/earth-system-discipline/weather) | 后续为数据源和制品绑定 WMO 稳定主题 URI |

SOSA 与 OMS 概念接近。本体 RDF 表达以 SOSA 为主，不复制一套 `MAZUObservation`；OMS
用于概念校验。GeoSPARQL、OWL-Time、PROV-O 和 QUDT 只复用所需部分，避免导入不必要的
完整推理负担。

## 3. 命名空间与制品

| 制品 | 路径 | 职责 |
|---|---|---|
| JSON-LD 本体真源 | `ontology/mazu_weather_ontology.jsonld` | 类、属性、标准映射和首批受控概念 |
| SHACL 约束 | `ontology/mazu_weather_shapes.ttl` | 断言、指标状态和预测约束的最小完整性要求 |
| SQLite 物化库 | `runtime/ontology/mazu_weather.sqlite3` | 本体物化表；后续知识图谱使用同一数据库中的独立实例表，不进入 Git |
| 构建脚本 | `scripts/build_ontology_db.py` | 校验 JSON-LD 并原子重建数据库 |
| 查询接口 | `mazu_saudi.ontology.OntologyStore` | 资源、模块、三元组和邻接查询 |

本项目命名空间使用稳定的本地 URN：

```text
urn:mazu-saudi:ontology:   类与属性
urn:mazu-saudi:concept:    指标、状态、机制和环境受控概念
```

未来若注册可长期解析的公共 URI，可发布等价映射，但不能在没有注册的情况下伪装成
`w3id.org` 永久标识符。

## 4. 模块设计

### 4.1 Observation

| 类 | 含义 |
|---|---|
| `DataSource` | 产生观测或指标的版本化产品 |
| `DerivedIndicator` | 由声明过程从源观测计算的物理指标 |
| `GriddedObservation` | 以网格或网格单元为直接对象的观测 |
| `ProxyLabel` | 由指标或规则得到的弱监督目标 |

全球数值数组仍保存在 NetCDF/Zarr。图数据库保存变量定义、状态、过程摘要、断言和源制品
指针，不为每个全球格点复制一条 RDF 记录。

本体 `1.3.0` 保留四个受控 `DataSource` 概念。DS2 日产品派生动力和地面状态；DS4
海温与 DS10 卫星降水在逐季覆盖率达标时可以形成独立观测状态，同时继续提供天气过程
背景和跨源一致性证据。DS1 月背景不变成逐日事件状态，任何单一降水源也不能冒充独立真值。

### 4.2 State

| 类 | 含义 |
|---|---|
| `AtmosphericState` | 有时间范围的大气条件分类 |
| `IndicatorState` | 由绝对阈值、当地百分位或气候距平定义的指标状态 |
| `ExtremeWeatherState` | 达到已声明气象极端判据的状态 |
| `HazardFavourableState` | 有利于灾害形成、但不证明灾害发生的状态 |
| `ObservedHazardEvent` | 有独立可追溯事件来源支持的灾害事件 |

状态转换必须保留：

```text
数值指标
  → 指标定义与单位
  → 阈值定义版本
  → IndicatorState
```

例如 `HighIVTState` 连接 `IntegratedVaporTransport`，具体百分位和物理阈值由每次冻结的
图谱提取运行提供，而不是写死在本体概念中。

### 4.3 Episode

`WeatherEpisode` 是时空连续的天气过程，也是统计检验、Bootstrap 和数据切分的最小独立
单元。`EpisodePhase` 表达初生、增强、成熟和衰减阶段。禁止将数百万个相邻格点日当成
独立证据数。

### 4.4 Context

| 类 | 例子 |
|---|---|
| `ClimateRegime` | `AridCoastal`、`AridInterior` |
| `TerrainContext` | `MountainWindward` |
| `SeasonalContext` | 暖季、Shamal 季节 |
| `DataAvailabilityContext` | 卫星降水缺测、压力层不完整 |

国家名称不是天气机制。`Saudi Arabia` 应拆成干旱沿海、干旱内陆、红海邻近、山地迎风、
季节和数据可用性等可迁移环境。

### 4.5 Mechanism

首版机制概念包括：

- `MoistureAdvection`
- `LocalConvection`
- `OrographicLift`
- `ThermalPersistence`
- `DryWindDustMobilization`

`compatibleWithMechanism` 只表示观测证据与机制相容。自动提取流程不使用 `causes`。

### 4.6 Assertion

关系必须实体化为断言，不能只写一条缺少上下文的裸边。

| 类 | 含义 |
|---|---|
| `EvidenceAssertion` | 带来源、范围、证据类别和审核状态的主张 |
| `LaggedAssociationAssertion` | 某状态在指定滞后与环境下统计先于另一状态 |
| `MechanismApplicabilityAssertion` | 某机制与指定状态和环境相容 |
| `CounterexampleAssertion` | 记录关系失效、反向或不适用的环境与过程 |

典型滞后断言至少包含：

```text
sourceState
targetState
lagHours
applicableUnder
supportEpisodeCount
supportedByEpisode
contradictedByEpisode
evidenceClass
eligibleForCausalExplanation
prov:wasGeneratedBy
```

后续实例还应保存条件发生率、同范围基础发生率、Lift、置信区间、稳定性、留一地区结果和
数据版本。

### 4.7 Forecast

| 类 | 含义 |
|---|---|
| `GraphDerivedFeature` | 查询适用断言后得到的数值特征 |
| `ForecastConstraint` | 图谱派生的软先验、方向约束或复核规则 |

图谱不能直接覆盖模型概率。所有图谱输出都必须携带适用度和来源断言。

### 4.8 Literature evidence

文献层是统计图谱的一次独立、不可变增强运行，不修改原全球数据提取构建。它区分：

| 类 | 含义 |
|---|---|
| `ScholarlyPublication` | 由题名、作者、年份、DOI或稳定地址标识的学术来源 |
| `LiteratureEvidenceRecord` | 能在保存的可访问正文快照中精确回定位的原文证据 |
| `LiteratureEvidenceAugmentationRun` | 针对一版冻结统计图谱运行的版本化文献抽取活动 |
| `MechanismApplicabilityAssertion` | 将统计断言解释为与某机制相容的非因果主张 |

连接结构为：

```text
MechanismApplicabilityAssertion
  ├─ sourceState / targetState → 状态概念
  ├─ applicableUnder → 原统计断言的环境
  ├─ interpretsAssociation → LaggedAssociationAssertion
  ├─ compatibleWithMechanism → WeatherMechanism
  └─ supportedByLiteratureEvidence → LiteratureEvidenceRecord

LiteratureEvidenceRecord
  ├─ groundedByPublication → ScholarlyPublication
  └─ prov:wasGeneratedBy → LiteratureEvidenceAugmentationRun
```

文献只支持状态组合与机制的相容性，不自动支持原统计断言中的季节、滞后、Lift，也不能
使统计断言进入生产预测。大模型输出必须通过受控概念、候选统计断言、原文精确包含和
来源定位校验；未通过人工审核的断言保持 `eligibleForCausalExplanation=false`。

## 5. 指标、图谱与沙特预测

### 5.1 指标进入图谱

```text
IVT/CAPE/PWAT/降水/SST/地形等数值
  → 当地百分位、气候距平和物理阈值
  → HighIVTState、HighCAPEState、MoistAtmosphereState
  → WeatherEpisode
  → LaggedAssociationAssertion
  → MechanismApplicabilityAssertion
```

本体首版内置日降水、IVT、CAPE、PWAT、最高温、VPD、10 米风速和地形概念。更多指标必须
先建立 CF 名称、QUDT 单位、来源和计算过程映射，再加入本体。

### 5.2 第一阶段：HGB 图谱特征

针对沙特某次预测，将当前指标转换成状态，并查询环境匹配的断言，生成：

```text
moisture_advection_support
convection_support
orographic_support
persistence_support
relation_stability
domain_applicability
counterexample_rate
evidence_completeness
```

这些特征与原有物理指标共同输入 HGB。必须与“仅物理指标 HGB”在相同冻结切分上比较。

### 5.3 第二阶段：MCR 路由软先验

图谱生成机制先验 \(\pi\)，MCR 路由器输出 \(q\)：

\[
L_{\text{graph-prior}}
=
\lambda \cdot a
\cdot D_{KL}(\pi \parallel q)
\]

其中 \(a\) 是图谱断言对当前沙特案例的适用度。适用度低时，图谱约束自动减弱，而不是
强迫沙特模型服从不适用的全球关系。

### 5.4 第三阶段：反事实约束与预测复核

- 移除高 IVT 状态后，水汽平流专家权重不应增加。
- 移除迎风坡环境后，地形专家权重应下降。
- 降低 CAPE 后，对流专家权重不应增加。
- 模型概率与图谱支持强烈冲突时，标记人工复核，不自动篡改概率。

## 6. 图谱提取和防泄漏

图谱提取不是“无训练”，而是知识学习活动。推荐冻结协议：

```text
全球图谱构建：2025-01 至 2025-05，排除阿拉伯半岛
全球关系验证：2025-06，留出完整气候区和天气过程
沙特最终测试：2025-07 至 2025-12
```

所有阈值、环境分类、关系筛选、Lift 门槛和适用度算法必须在打开沙特测试结果前冻结。
图谱版本、本体 SHA、输入清单 SHA、状态规则和统计筛选配置写入 `ExtractionRun`。

文献增强同样记录文献清单 SHA、正文快照 SHA、提示词版本、模型名称和原始响应 SHA。
文献增强只解释冻结统计断言，不改变统计构建的候选等级；沙特验证仍是独立的后续阶段。

### 6.1 数据关系的分层与晋级

本体允许表达关系，不代表从数据中统计出的每一条关系都已经成为可迁移知识。自动构图必须
保留证据，同时把关系用途分开：

| `relation_role` | 含义 | 默认用途 |
|---|---|---|
| `state_persistence` | 同一状态跨日持续 | 诊断时间自相关 |
| `measurement_agreement` | 两种数据源同日测量同一现象 | 诊断数据一致性 |
| `cross_source_persistence` | 同一现象跨数据源、跨日延续 | 诊断产品和过程持续性 |
| `contemporaneous_association` | 不同指标同日共现 | 一般诊断证据 |
| `lagged_cross_indicator` | 不同指标之间的跨日关系 | 统计证据或预测候选 |

自动生成断言使用三级 `validation_stage`：

1. `diagnostic_evidence`：测量一致性、状态持续性和同日关系；
2. `statistical_evidence`：尚未通过预测候选门槛的跨指标滞后关系；
3. `candidate_for_saudi_evaluation`：只允许进入沙特离线增量实验，不代表已经迁移成功。

候选必须同时满足：

- 源和目标属于不同物理量；
- 滞后天数大于零；
- 目标是 `ExtremeWeatherState`；
- 源、目标均通过逐季覆盖门控；
- 支持过程数、Lift 和过程支持率均达到构建配置门槛。

默认过程支持率门槛为 `0.25`。关系的每项晋级检查、策略版本和未通过项写入断言属性与
`kg_evidence`。自动提取不得设置 `eligible_for_causal_explanation` 或
`eligible_for_production_prediction`。`transferability_status` 在沙特留出评估完成前固定为
`not_evaluated_on_saudi`。

`max_assertions` 仍用于控制单个构建批次的物化规模，但选择顺序改为：先按证据强度排列并
保留满足门槛的沙特离线评估候选，再按 Lift—支持数得分补充一般统计和诊断证据。这样高
自相关关系不能仅凭更高 Lift 把合格的极端天气预测候选挤出图谱。

### 6.2 后续验证，而不是自动补全

当前阶段不使用大模型或图谱嵌入自动补边。下一阶段应按气候区、海陆属性和季节进行环境
分层，使用时间块和留出区域验证候选关系；随后在沙特数据上比较“基线模型”和“加入图谱
候选特征模型”。只有对沙特留出集有稳定增益的关系，才能由独立验证脚本晋级为已验证规则。

大模型后续只用于从论文抽取候选机制、术语对齐和生成可审核解释。论文来源、原文证据、
模型版本、置信度和人工审核状态必须保存；大模型不得补造缺失观测，不得直接把语言模型
推断写成已验证气象事实。

## 7. SQLite 物化模型

数据库包含：

| 表 | 内容 |
|---|---|
| `ontology_documents` | 本体 IRI、版本、JSON-LD SHA、加载时间和完整源文档 |
| `namespaces` | JSON-LD 前缀与命名空间 |
| `resources` | 类、属性和受控概念的双语检索索引 |
| `statements` | 主语—谓词—宾语三元组，区分 IRI 与带语言/数据类型的字面量 |

`resources` 是查询优化索引，`statements` 是语义真值。数据库可重复构建，不作为手工维护
真源。

全球知识图谱写入同一个 SQLite 文件，但使用独立的 `kg_builds`、`kg_nodes`、
`kg_edges`、`kg_evidence` 和 `kg_thresholds` 表。`kg_evidence` 同时保存关系角色、验证
阶段、过程支持率、迁移状态和预测用途门控。本体重建只能清空本体四张表，不能清空知识图谱实例表；
知识图谱构建脚本也不能改写本体表。

构建：

```bash
PYTHONPATH=src conda run -n ml python scripts/build_ontology_db.py
```

检查一个概念：

```bash
PYTHONPATH=src conda run -n ml python scripts/build_ontology_db.py \
  --inspect urn:mazu-saudi:concept:HighIVTState
```

Python 查询：

```python
from pathlib import Path
from mazu_saudi.ontology import OntologyStore

store = OntologyStore(Path("runtime/ontology/mazu_weather.sqlite3"))
print(store.summary())
print(store.list_resources(module="mechanism"))
print(store.statements_for("urn:mazu-saudi:concept:HighIVTState"))
```

## 8. 后端服务与前端浏览

本体复用现有 `competition_app`，不建立第二个应用。FastAPI 在首次查询以及 JSON-LD SHA
变化时自动重新物化 SQLite，并提供以下只读接口：

| 接口 | 用途 |
|---|---|
| `GET /api/v1/ontology` | 查询版本、SHA、资源数、陈述数和模块统计 |
| `GET /api/v1/ontology/view` | 按中英文文本和模块查询本体资源及其一阶结构关系 |
| `GET /api/v1/ontology/resource?iri=...` | 查询单个资源及其出入陈述 |
| `GET /api/v1/knowledge-graph` | 查询最新图谱构建批次和真实性边界 |
| `GET /api/v1/knowledge-graph/view` | 查询一版实例图谱的节点、关系和构建元数据 |

`view` 接口支持 `query`、`module` 和 `limit` 参数。所有参数都有长度或数量上限，接口不
提供写操作。JSON-LD 仍是规范真源，SQLite 只是可重建的服务索引。

前端本体入口为 `/ontology`。页面直接调用 `view` 接口，支持：

- 中英文名称和定义搜索；
- observation、indicator、state、episode、context、mechanism、assertion、
  provenance、forecast 模块过滤；
- 关系类型开关；
- 鼠标或键盘选择节点；
- 双语定义、资源类型、IRI 和相邻关系检查；
- 桌面与移动端响应式布局。

本体关系视图必须显示节点文字、方向箭头，并在选中节点后显示关系谓词。页面必须明确
声明“本体关系视图不是知识图谱”。

`/knowledge-graph` 是 GOMAG 的独立入口。没有构建批次时只显示真实待构建状态；数据库
存在构建批次时，页面交互展示分层证据断言、上下文、证据过程和受控状态概念，不得生成
占位关系。默认“关系视图”把 `LaggedAssociationAssertion` 投影为从 `sourceState` 指向
`targetState` 的带文字关系边，边标签显示季节、滞后、证据用途和 Lift，点击边仍检查原始
断言属性。关系视图不得把断言画成普通天气节点。可选“审计结构”保留断言节点、技术谓词和
证据过程，用于追溯原始关系实体化模型。页面同时提供“预测候选、滞后统计、诊断关系”用途
筛选，并公开关系角色、验证阶段、晋级检查和迁移状态。

## 9. 当前版本和后续里程碑

本体 `1.3.0` 完成语义骨架、标准映射、首批指标/状态/机制/环境概念、四类数据源、多源
观测状态、SHACL 约束及 SQLite 物化。第一阶段统计构图脚本已经实现，读取每日指标 NetCDF
后生成天气过程、滞后关联断言、支持证据和反例；关系级逐季覆盖门控会抑制缺测动力状态，
但保留覆盖达标的可观测状态。全球原始数据到空间块指标的流式脚本也已实现，并在原始格点
聚合前排除沙特研究区域；正式全球图谱仍须由用户完成全年长任务后生成。

后续顺序：

1. 运行全球流水线，生成满足输入契约的 365 个沙特隔离日指标文件。
2. 审核 E 盘三个已知缺源日期及全年指标质量，再冻结空间块、分位数、滞后、支持数和 Lift。
3. 按关系策略完成分层证据构图，分别审核诊断关系、一般统计证据、预测候选及反例。
4. 补充气候型环境分层，并进行时间块、留出区域和多重检验校正，不在这一阶段引入论文结论。
5. 只从 `candidate_for_saudi_evaluation` 生成图谱候选特征。
6. 进行 Saudi HGB 基线/增量对照；只有留出集稳定增益关系才能晋级，再考虑 MCR 路由约束。
7. 数据驱动验证稳定后，再引入带来源和人工审核的大模型论文抽取，不自动补造关系。
