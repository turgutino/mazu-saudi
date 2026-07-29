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
构建需要先把全球原始产品转换为同一每日指标契约。

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

正式全球日指标目录准备好以后运行：

```bash
PYTHONPATH=src conda run -n ml python scripts/build_knowledge_graph.py \
  --input-dir /path/to/global_2025_daily_indicators \
  --scope-label global-2025 \
  --database runtime/ontology/mazu_weather.sqlite3
```

关键参数：

```text
--tile-degrees 10
--max-lag-days 3
--min-support-episodes 8
--min-lift 1.15
--max-assertions 160
--evidence-episode-limit 12
--min-indicator-file-coverage 0.50
```

脚本会先物化并核对当前本体，再原子写入一个新的不可变构建批次。构建结果以 JSON 输出
批次 ID、文件数、空间块数、节点数、关系数、断言数、证据过程数和阈值数。

## 6. 服务与展示

构建完成并重启应用后：

```text
GET /api/v1/knowledge-graph
GET /api/v1/knowledge-graph/view?limit=500
```

前端 `/knowledge-graph` 会从实例表读取真实节点和关系。没有正式构建批次时继续显示待构建
状态；不会用本体节点或合成关系填充页面。
