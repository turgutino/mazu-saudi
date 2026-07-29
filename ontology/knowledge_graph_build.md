# 2025 指标统计知识图谱构建

## 1. 第一阶段边界

第一阶段只使用一年每日指标数据和 MWMO 本体，不从论文导入关系，也不重新设计指标标准。
脚本的任务是把已有数值指标转换为可审计的状态、天气过程、统计断言、支持证据和反例。

自动生成的关系统一为 `LaggedAssociationAssertion`，并固定：

```text
evidence_class = observational-statistical
eligible_for_causal_explanation = false
```

它不生成 `MechanismApplicabilityAssertion`，不声称因果机制成立，也不把极端气象状态当作
独立灾害事件。

## 2. 输入契约

输入目录应包含同一年每日一个 NetCDF 文件，文件名包含 `YYYYMMDD`。每个文件至少包含：

| 指标变量 | 本体状态 |
|---|---|
| `ivt` | `HighIVTState` |
| `cape` | `HighCAPEState` |
| `pwat` | `MoistAtmosphereState` |
| `daily_precip_total` | `ExtremeRainfallState` |
| `tmax_c` | `ExtremeHeatState` |
| `wind10_speed` + `vpd_kpa` | `StrongDryWindState` |

变量必须是 `latitude × longitude` 二维网格。数值单位和计算过程由指标文件自身属性负责；
构图脚本不重新计算原始气象指标。单日缺少某指标时记为缺测，不当作状态未发生；某指标
全年完全缺失或出现文件比例低于默认 50% 时停止。实际有效样本数写入 `kg_thresholds`。
正式年度构建默认要求 365 个日期唯一的文件，缺日会停止，只有有意的开发验证才能使用
`--allow-incomplete-year`。

当前
`/Volumes/E/气象数据/saudi_region_output/indicators`
满足这个输入契约，但它是沙特区域指标，只能用于链路验证，不能冒充全球图谱。正式全球
构建由 `scripts/build_global_knowledge_graph.py` 直接读取 E 盘全球日 GRIB2 产品，先生成
满足同一契约的空间块指标文件。

### 2.1 多源全球数据入口与沙特隔离

全球流水线分层读取：

| 数据源 | 实际覆盖 | 图谱角色 |
|---|---:|---|
| DS1 月尺度大气产品 | 12 个月 / 365 日可对齐 | 月累计降水和月最高温背景 |
| DS2 日尺度大气产品 | 362 个完整日，3 个缺口日 | 日尺度主状态与滞后关系 |
| DS4 CODAS 海温 | 365 日，每日 4 个时次 | 海洋热力环境 |
| DS10 FYMERG 卫星降水 | 2025-01-01 至 2025-09-30，共 273 日 | 独立降水一致性证据 |

DS2 每天使用 `DAY_ANAL`、`DAY_ACC`、`DAY_MAX` 和 `DAY_SFC` 四类产品。流水线还读取
DS1 当月累计降水与最高温、DS4 每日四个海温文件，以及 DS10 每日 48 个半小时降水率文件。
它不会复制原始全球细网格，而是在原始格点计算或累计后立刻聚合到图谱空间块。

四类数据不被简单拼接成同一种状态：

- 只有 DS2 的日尺度动力、热力和地面指标参与 0–3 天状态滞后统计。
- DS1 的月尺度值和 DS4 海温写入天气过程的 `multi_source_context`。
- DS10 与 DS2 降水在时空对齐后计算差值、绝对差和比值，属于一致性诊断，不是真值标签。
- 图谱提取运行通过 `prov:used` 连接四个 `DataSource` 概念；状态实例通过
  `prov:wasDerivedFrom` 保留来源。
- 2025 年 10–12 月没有 DS10，明确记录为卫星证据不可用，不影响 DS2 日状态存在性。

沙特研究区域采用与区域提取脚本一致的保守边界框
`16–32°N, 34–56°E`。掩膜在空间聚合之前应用，因此框内原始格点不会参与全球阈值、
天气过程或滞后关系；不是在展示层删除沙特节点。输出批次范围必须标记为
`global-2025-excluding-saudi`。

当前 E 盘清单有 365 个日期目录，但原始产品存在三个已知缺口：

| 日期 | 缺少产品 |
|---|---|
| 2025-08-17 | `DAY_MAX` |
| 2025-08-18 | 四类必需产品全部缺少 |
| 2025-08-20 | `DAY_ACC` |

流水线会为这些日期保留显式缺测值，不会将缺测当作状态未发生。默认最多允许 5 个 DS2
日期存在源产品缺口，超过即停止；清单审计同时输出四个数据源的有效覆盖日数。

## 3. 统计方法

默认流程：

1. 将每日指标按 `10° × 10°` 空间块求有效格点均值，避免把全球格点日全部复制入图谱。
2. 在每个空间块和 DJF/MAM/JJA/SON 季节内计算状态分位数。
3. IVT、CAPE、PWAT 使用 P90；降水和最高气温使用 P95；强风干燥要求风速和 VPD 同时超过 P90。
4. 常量序列不生成状态；缺测不视为未发生。
5. 同一空间块、同一状态、同一季节的连续日期合并成 `WeatherEpisode`。
6. 对状态对统计 0–3 天滞后，计算机会数、源/目标出现数、共同出现数、条件发生率、基线发生率和 Lift。
7. 默认至少 8 个支持天气过程且 `Lift ≥ 1.15` 才生成断言。
8. 每条断言保存支持过程、反例过程和季节环境；为控制图谱规模，默认各只展开 12 个证据过程节点。
9. 每个展开的天气过程附带 DS1 月背景、DS4 海温、DS10 可用性及 DS2–DS10 降水一致性摘要。

Lift 定义为：

\[
\mathrm{Lift}(A \rightarrow B_{\,+k})
=
\frac{P(B_{t+k}=1 \mid A_t=1)}
{P(B_{t+k}=1)}
\]

Lift 只是限定样本内的关联强度。第一阶段不计算显著性因果结论，也不做沙特预测增益声明。

## 4. SQLite 表

知识图谱与本体共用
`runtime/ontology/mazu_weather.sqlite3`
文件，但表完全分离：

| 表 | 内容 |
|---|---|
| `kg_builds` | 本体版本、输入清单指纹、日期、范围、完整构建配置和计数 |
| `kg_nodes` | 提取运行、季节环境、天气过程、状态实例和统计断言 |
| `kg_edges` | 本体谓词约束的实例关系 |
| `kg_evidence` | 每条统计断言的机会数、支持数、反例数、发生率和 Lift |
| `kg_thresholds` | 每个空间块、季节、状态和指标的分位数阈值及样本数 |

本体物化只替换 `ontology_documents/namespaces/resources/statements`，不会删除已经构建的图谱。

## 5. 构建命令

先只检查 E 盘文件清单，不计算数据：

```bash
PYTHONPATH=src conda run -n ml python scripts/build_global_knowledge_graph.py \
  --stage audit
```

建议先计算一天，验证运行环境、耗时和输出：

```bash
PYTHONPATH=src conda run -n ml python scripts/build_global_knowledge_graph.py \
  --stage indicators \
  --start 20250101 \
  --end 20250101
```

确认后执行全年指标与图谱构建：

```bash
PYTHONPATH=src conda run -n ml python scripts/build_global_knowledge_graph.py \
  --stage all
```

默认指标输出为：

```text
/Volumes/E/气象数据/global_excluding_saudi_2025/indicators/
```

每个日文件是已经排除沙特格点的 `10° × 10°` 图谱用指标，而不是原始全球细网格副本。
脚本逐日原子写入，并自动跳过结构完整的已有文件；中断后重复同一命令即可继续。运行记录
追加到 `indicator_build_manifest.jsonl`。单日错误默认记入清单后继续处理其他日期，但只要
存在错误就不会进入图谱构建阶段并以非零状态退出。每个输出还保存源文件路径、大小和修改
时间；如果之后补齐或替换了缺失源产品，断点续跑会自动重新计算受影响日期。

全球流水线版本现为 `3`，并与沙特指标共用公式版本 `1.0.0`。旧的全球 v2 日文件因缺少
当前流水线和公式版本会自动重新计算。共享公式统一了 Kelvin 转摄氏度、VPD、风速、六层
IVT 梯形积分，以及 FYMERG `mm/h × 0.5 h` 的半小时降水量换算；全球和沙特仍分别保留
空间块与细网格表示。

如果指标已全部生成，只重建图谱：

```bash
PYTHONPATH=src conda run -n ml python scripts/build_global_knowledge_graph.py \
  --stage graph
```

关键参数：

```text
--tile-degrees 10
--max-days-with-missing-sources 5
--max-lag-days 3
--min-support-episodes 8
--min-lift 1.15
--max-assertions 160
```

IVT 默认使用 1000、925、850、700、500、300 hPa 六层，在原始格点进行梯形压力积分，
再计算矢量模长和空间块面积加权均值。该层集合由共享公式模块固定，避免全球图谱与沙特
预测指标因命令行覆盖而再次产生口径分歧。

脚本会先核对原始清单，完成指标后物化并核对当前本体，再原子写入一个新的不可变构建批次。
构建结果以 JSON 输出批次 ID、文件数、空间块数、节点数、关系数、断言数、证据过程数和
阈值数。

## 6. 服务与展示

构建完成并重启应用后：

```text
GET /api/v1/knowledge-graph
GET /api/v1/knowledge-graph/view?limit=500
```

前端 `/knowledge-graph` 会从实例表读取真实节点和关系。没有正式构建批次时继续显示待构建
状态；不会用本体节点或合成关系填充页面。
