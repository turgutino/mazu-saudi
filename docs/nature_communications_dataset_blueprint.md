# Nature Communications 级数据与论文蓝图

> 版本：2026-07-23。本文给出研究与数据建设路线，不构成期刊录用保证。数据许可、伦理审批和国家机构合作须在正式采集前逐项确认。

## 1. 核心判断

当前 2025 沙特指标数据可以做原型，但不能单独支撑 Nature Communications 级论文。主要缺口不是变量数量，而是：

- 只有一个年份，无法估计稀有事件尾部和跨年稳定性；
- 多数标签由输入变量规则派生，缺少独立事件真值；
- 日尺度和约 0.1°网格会抹掉短历时城市/Wadi 山洪；
- 只覆盖沙特，不能证明机制能否迁移；
- 缺少积水、伤亡、就诊、道路中断等影响数据；
- 缺少历史 forecast/reforecast，难以严格证明提前预警能力。

[Nature Communications](https://www.nature.com/ncomms/submit/content-types) 要求 Article 是对相应研究社区“novel and important”的高质量研究，编辑还会评估概念或方法推进和潜在影响，而不是只检查数据是否够大。因此，新数据集必须服务一个重要、可证伪的科学问题。

推荐主问题：

> **全球天气和水文产品为什么在干旱区短历时 Wadi 山洪上失效？显式表示临时河道、降水传播机制和观测可用性，能否产生可跨盆地迁移、概率可靠的提前预警？**

建议数据集工作名：**AridFlash-MENA**。热浪保留为机制迁移的辅助基准；四灾种系统继续服务竞赛，但不作为第一篇 Nature Communications 主线。

## 2. 为什么优先做干旱区山洪

### 2.1 科学空缺更明确

全球河网产品自己承认局地精度有限；[MERIT Hydro](https://developers.google.com/earth-engine/datasets/catalog/MERIT_Hydro_v1_0_1) 特别指出干旱内流盆地中偶发连通会造成流域边界不确定。[HydroSHEDS](https://www.hydrosheds.org/about) 也强调其全球产品不能达到局地高分辨率水系精度。

因此，新贡献不只是“又一个气象数据集”，而是：

1. 建立经过遥感和人工核验的 ephemeral-wadi graph；
2. 连接半小时降水、物理机制、积水范围、官方报告和实际影响；
3. 证明模型何时能跨盆地迁移、何时应拒识。

### 2.2 与现有框架匹配

MCR-Hazard 的风向/水汽平流、局地对流触发、地形汇流和缺测拒识，都可以在一个灾种内部得到检验，不必依靠四灾种拼装。Nature Communications 已有干旱 Wadi 灾害的综合机制研究，例如[Derna 洪灾重建](https://www.nature.com/articles/s41467-025-59261-9)结合卫星、洪水/水力模型、机器学习、目击证据和地形数据，说明综合证据链比单一预测分数更符合这一层级的研究形态。

## 3. 数据集总体范围

### 3.1 时间范围

建议采用三个嵌套层级：

| 子集 | 时间 | 用途 |
|---|---|---|
| 长期气候背景 | 1981–2025 | 极值气候态、SST、热浪辅助分析 |
| 统一动态主干 | 2001–2025 | ERA5/ERA5-Land、IMERG、站点和事件目录 |
| 高分辨率事件 | 2014–2025 | Sentinel-1 SAR、精细积水/Wadi 核验 |

公共主干优先冻结为 2001-01-01 至 2024-12-31，2025 年作为真正的时间外测试；如果事件标注需要更久，可将最终冻结年份顺延，但不能边看测试结果边改模型。

### 3.2 地理范围

第一版不要覆盖整个 MENA 每个网格，而要选择机制和数据质量互补的盆地/城市：

- 沙特西部：Jeddah–Makkah–Madinah/Hejaz Wadi；
- 沙特西南：Asir/Jazan 山地对流；
- Oman/UAE：Hajar Mountains 到城市/海岸的快速汇流；
- Jordan：Dead Sea/Wadi Mujib 一类干旱峡谷；
- Egypt/Sinai 或 Red Sea coast；
- Morocco/Atlas 作为距离较远的干旱区 OOD 区域。

最低建议是 5 个气候—地形区域、10–20 个独立盆地。最终数量由事件覆盖和合作数据决定，不以行政边界数量充数。

### 3.3 研究对象

主数据以“独立天气过程/洪水事件”为单位，而不是把每个格点小时当独立样本：

```text
Event {
  event_id, basin_id, start_time, peak_time, end_time,
  rainfall_geometry, inundation_geometry,
  official_reports, observed_impacts,
  label_confidence, source_refs,
  observation_availability
}
```

每个事件再生成按 `forecast_origin` 组织的样本：

```text
ForecastSample {
  context: t-72h ... t,
  lead: 3h | 6h | 12h | 24h | 48h,
  predictors_available_at_t,
  event_occurrence,
  inundation_or_impact_target,
  missingness_pattern
}
```

负样本应按相同季节、盆地和相近天气背景匹配，避免用大量晴空格点制造虚高准确率。

## 4. 必须新增的数据

### 4.1 多年大气与陆面状态

| 数据 | 时间/分辨率 | 关键变量 | 角色 |
|---|---|---|---|
| [ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview) | 1940–今；逐小时；0.25° | 温湿风、CAPE、云、辐射、压力层、水汽输送 | 机制背景与统一输入 |
| [ERA5-Land](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview) | 1950–今；逐小时；约 9 km/0.1° | 土壤湿度、径流、地表温度、蒸发 | 前期土壤状态和热背景 |
| [NOAA OISST](https://www.ncei.noaa.gov/products/optimum-interpolation-sst) | 1981–今；逐日；0.25° | SST/SST anomaly | 红海/阿拉伯海水汽源和海陆耦合 |

ERA5 是同化后的再分析，不能充当独立观测标签。所有变量必须保留源版本、生成时间和可用时间。

### 4.2 高频降水

主干使用 [GPM IMERG Final](https://gpm.nasa.gov/data/imerg)：2000 年 6 月以来全球 0.1°、半小时降水。需要保留：

- 半小时原始序列，而不只是日最大值；
- precipitationCal、质量/误差和 microwave observation time；
- 1/3/6/12/24 小时滚动累计；
- 移动速度、方向、连通区域、峰值和降水质心轨迹；
- 与站点雨量的事件级偏差。

如果能获得 NCM/地方雷达和雨量站，应形成一个高分辨率 Saudi-Gold 子集；它可能比新增网络层更重要。

### 4.3 站点独立真值

[NOAA ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database) 提供全球逐小时温度、露点、风、能见度和多时段降水，并带质量标记。需逐站审计：

- 坐标、海拔、迁站和站号变更；
- 每年/每月完整率、连续缺口、时间分辨率；
- 降水累积周期和 trace precipitation；
- 极端值、单位、重复记录和质量旗标；
- 与 NCM 站点、IMERG 和 ERA5 的独立性/来源重叠。

热浪辅助标签使用站点 Tmax/Tmin、湿球或 UTCI/WBGT；山洪则优先使用逐小时/更短雨量和水位/流量站。

### 4.4 洪水范围和事件证据

| 来源 | 能提供什么 | 局限 |
|---|---|---|
| [Sentinel-1](https://sentinels.copernicus.eu/documents/247904/1653440/Sentinel-1_Data_Access_and_Products) | 全天候 SAR 积水变化，2014 年起 | 重访可能错过短命山洪；城市阴影/粗糙地表误差 |
| [Global Flood Database](https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1) | 2000–2018 全球事件范围、持续时间和云质量 | 大事件偏置；短历时 Wadi 漏检 |
| Landsat/Sentinel-2 | 高分辨率水体与冲刷痕迹 | 云、重访和事后时间错配 |
| 官方 NCM/民防/市政记录 | 告警、时间、地点、处置 | 获取和许可依赖合作 |
| [ReliefWeb](https://apidoc.reliefweb.int/endpoints)、新闻和社交媒体 | 事件发现、道路/社区影响证据 | 选择偏差；必须保存来源与人工核验 |

关键规则：SAR/光学未观测到水不能自动成为负标签。每个标签同时保存 `observed`, `not_observed`, `not_observable`, `conflicting` 状态。

### 4.5 Ephemeral-Wadi 图

基础数据可以来自 Copernicus DEM GLO-30、SRTM、HydroSHEDS/MERIT Hydro，并加入：

- flow direction、flow accumulation、HAND、坡度、曲率；
- 盆地边界、上游面积、travel-time 和城市出口；
- Sentinel-1/2 历史积水或冲刷痕迹；
- OpenStreetMap culvert/bridge/road crossing；
- 市政排水、涵洞和防洪设施（若能合作获得）；
- 人工核验的 `edge_confidence` 和季节性/临时连通属性。

独特性来自“干旱区临时连通、城市排水与 Wadi 汇流”的核验，而不是从 DEM 自动跑一次 D8。

### 4.6 土地、土壤与暴露

- [ESA WorldCover](https://esa-worldcover.org/en/about/about)：10 m 土地覆盖；
- SoilGrids：土壤纹理、渗透相关属性和不确定性；
- [GHSL](https://human-settlement.emergency.copernicus.eu/dataToolsOverview.php)：多时相人口、建成区和城市分类；
- 道路、医院、学校、电力、水务和港口等关键设施；
- 事件时点对应的人口/建成区版本，避免用 2025 暴露解释 2001 影响。

这些数据构成 `Exposure`，不能混入气象事件是否发生的金标签。

### 4.7 历史预报与再预报

如果摘要使用 forecast/early warning 字样，必须加入真实预报语义：

- [TIGGE](https://confluence.ecmwf.int/spaces/TIGGE/pages/40798066/Project)：2006 年起多中心集合预报；
- [NOAA GEFSv12 reforecast](https://psl.noaa.gov/news/2022/042122a.html)：2000–2019 的一致回报资料；
- NCM/ECMWF IFS 历史预报：若能通过合作或研究协议获得；
- 当前 ECMWF/AIFS Open Data 只适合未来前瞻验证，因为[开放滚动档案只保留最近约 2–3 天](https://www.ecmwf.int/en/forecasts/datasets/open-data)。

需要分别报告：reanalysis-to-observation、reforecast-to-observation 和 operational forecast-to-observation，禁止混在一个指标里。

## 5. 标签体系

### 5.1 三层标签

| 层 | 内容 | 示例 | 用途 |
|---|---|---|---|
| Hazard Gold | 独立气象/水文观测 | 站点短时雨量、水位、SAR 积水 | 主训练锚点和最终测试 |
| Event Evidence | 官方/人工核验事件 | NCM 告警、民防记录、道路积水报道 | 事件时空确认 |
| Impact Gold | 实际损失或健康影响 | 伤亡、急诊、断路、停电、建筑积水 | 影响预测子任务 |

规则风险分数、ERA5 降水和模型输出全部属于 proxy，不能进入 Gold。

### 5.2 标注流程

1. 自动发现候选：IMERG 极值、站点、SAR 变化、报告检索；
2. 两名标注者独立标注开始/结束、几何、证据与置信度；
3. 第三名专家处理冲突；
4. 抽样邀请水文/气象专家复核；
5. 发布标注指南、版本和 inter-annotator agreement；
6. 保留负例候选的“可观测性”，避免未报道即负例。

推荐置信度：

```text
A: independent gauge/SAR + official/event evidence
B: two independent observational/evidence sources
C: one credible source or coarse satellite evidence
P: proxy-only candidate, excluded from final test
```

最终测试以 A/B 为主，C/P 只用于弱监督或敏感性分析。

## 6. 数据规模目标

以下是项目设计目标，不是期刊硬性门槛：

- 20–25 年统一动态主干；
- 10–20 个盆地、至少 5 个地理机制区域；
- 300–500 个候选洪水过程；
- 其中尽量达到 150–250 个 A/B 级独立事件；
- 每个事件至少 72 小时前情和 48 小时后情；
- 2014 年后事件尽量提供 SAR/高分辨率子集；
- 每个 OOD 区域有足够事件独立计算 PR-AUC/CSI/校准置信区间。

如果沙特官方数据能提供 50–100 个极高质量事件，也比数千个规则伪标签更有价值。深度模型的样本行数不是关键，独立天气过程数量和标签可信度才是关键。

## 7. 冻结切分和基准任务

### 7.1 切分

- `train`：早期年份和部分盆地；
- `validation`：后续年份，允许模型/阈值选择；
- `temporal test`：冻结最新完整年份；
- `geographic OOD`：完整留出至少一个国家/机制区域；
- `sensor-shift test`：按 IMERG/站点/SAR 缺失模式冻结；
- 同一天气系统影响多个盆地时，所有关联样本必须同 split。

### 7.2 官方基准任务

1. `T1 Event occurrence`：3/6/12/24/48 小时事件概率；
2. `T2 Peak rainfall`：短历时降水尾部分布；
3. `T3 Inundation/wadi activation`：盆地出口或积水几何；
4. `T4 Cross-basin transfer`：留一地区泛化；
5. `T5 Missing-sensor selective prediction`：风险—覆盖与拒识；
6. `T6 Impact-linked forecast`：仅在高质量影响子集评估。

Nature Communications 主文只需围绕 T1/T3/T4/T5 建立一个清晰机制结论；不必把所有任务都写成模型排行榜。

## 8. 技术验证与质量控制

### 8.1 数据级

- 坐标、单位、UTC、日界线、累计量重置和闰年测试；
- 站点迁移、完整率、异常值和质量旗标；
- IMERG–站点事件级 bias、POD/FAR 和强度分层；
- SAR 前后景、永久水、城市阴影和可观测性掩膜；
- Wadi graph 的上游—下游方向、出口和 travel-time 人工抽检；
- 每个变量记录 source DOI、license、version、processing commit 和 checksum。

### 8.2 科学级

- 与普通邻域、全球河网和无地形模型对照；
- 按对流/平流/地形汇流机制分层；
- 物理反事实：旋转水汽输送、切断上游边、扰动土壤湿度；
- OOD 最坏区域与最坏季节；
- 独立事件 block bootstrap；
- 校准、空间容差和对象级评估，不只报告逐像元 ROC-AUC。

## 9. Nature Communications 论文应证明什么

数据集本身不是主结论。建议论文形成三层证据：

1. **新发现**：全球产品在干旱 Wadi 山洪上的误差与某些机制/可观测性状态系统相关；
2. **方法推进**：机制约束路由或显式 Wadi 图显著改善跨盆地尾部预测和校准；
3. **实际意义**：在固定 FAR 或风险预算下增加有效预警时间/覆盖，并识别模型应拒识的情形。

论文不能只说“MCR-Hazard 比 XGBoost 高 3%”。更强的结论应类似：

> 在未见盆地和传感器缺失条件下，机制约束模型保持可靠概率；性能增益主要来自正确表示临时汇流连通，而非参数规模，并揭示当前全球产品在某类干旱机制中的系统性盲区。

## 10. 热浪辅助路线

热浪数据容易获得，但单纯预测 Tmax 的新颖性较弱。只有拿到以下至少一种影响数据时，建议升为主线：

- 分城市日死亡或超额死亡；
- 急诊/住院、热射病或肾损伤；
- 用电峰值/停电；
- 劳动伤害、缺勤或生产率；
- 经伦理审查的个体或聚合健康记录。

[WHO](https://www.who.int/news-room/fact-sheets/detail/climate-change-heat-and-health)指出热相关死亡和住院可能在同日及随后数日发生，影响还取决于昼夜高温、湿度、风、辐射、适应和脆弱性。没有这些影响数据时，只能称气象热浪预测，不能称热健康预警。

## 11. 数据发布与双论文策略

建议发布四层产品，而不是只发布处理后的特征矩阵：

```text
raw_index/       # 原始来源索引、许可、checksum，不重复分发受限原始数据
harmonized/      # 对齐后的可开放动态/静态变量
events/          # 事件表、几何、证据、置信度和标注历史
benchmarks/      # 冻结 split、样本 manifest、baseline 和 evaluation code
```

- 公共数据和代码使用 DOI 仓库、版本化和机器可读元数据；
- 受限健康/官方数据只发布聚合结果、访问流程和可复现实验接口；
- 核心代码在投稿时即可供审稿人访问，[Nature Communications 要求核心自定义代码可审查](https://www.nature.com/ncomms/submit/how-to-submit)；
- 数据集若先投 [Scientific Data](https://www.nature.com/sdata/aims-and-scope)，Data Descriptor 只写构建、记录和技术验证，不检验 MCR 假设；Nature Communications 论文再使用该冻结数据回答科学问题。

应在投稿前核对两篇稿件的重叠和数据版本，避免把同一贡献拆分成重复发表。

## 12. 分阶段执行与停止条件

### Gate 0：可行性审计，4–6 周

- 盘点 MENA ISD 站点连续性；
- 从 ReliefWeb/官方资料建立 50 个事件样例；
- 下载 10 个事件的 IMERG 和 Sentinel-1；
- 对 3 个盆地生成初版 Wadi graph；
- 联系 NCM/民防/市政/医院，确认能否提供事件或影响数据。

停止条件：若无法找到至少两个区域的高置信事件和可靠时间位置，就不要立即扩展全 MENA。

### Gate 1：Pilot，2–3 个月

- 3 个盆地、2018–2024；
- 50–100 个候选事件；
- 完成标签指南、双人标注和可观测性掩膜；
- 用 HGB/XGBoost、固定邻域和普通图模型建立基线。

成功条件：高置信事件足以复现“普通空间平滑/全球河网在哪些机制下失败”。

### Gate 2：完整数据，4–8 个月

- 扩展至 2001–2025、10–20 盆地；
- 引入 GEFS/TIGGE reforecast；
- 冻结时间和 geographic OOD split；
- 发布 dataset card、DOI、baseline 和质量报告。

### Gate 3：机制论文，3–6 个月

- 实现 MCR-Hazard；
- 完成反事实、OOD、缺测拒识和影响子集实验；
- 用独立事件 bootstrap 报告不确定性；
- 形成数据论文和科学论文的明确边界。

## 13. 当前最先需要的数据清单

按价值/难度排序：

1. **NCM/站点多年逐小时雨量、温湿风及质量标记**；
2. **带日期、地点和证据的官方 Wadi/城市积水事件表**；
3. **2001–2025 IMERG 半小时降水**；
4. **2001–2025 ERA5/ERA5-Land 小范围必要变量**；
5. **2014–2025 事件前后 Sentinel-1 SAR**；
6. **30–90 m DEM + 人工核验 Wadi graph**；
7. **GEFS/TIGGE 历史再预报**；
8. **道路中断、伤亡、急诊、停电等影响记录**；
9. GHSL/WorldCover/SoilGrids 等静态暴露和地表属性；
10. CAMS dust/OISST 等扩展机制数据。

优先争取第 1、2、8 项的机构合作。公开 ERA5/IMERG 很容易下载，却无法替代独立真值和影响数据；真正决定论文上限的是后者。
