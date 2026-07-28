# 进度记录：沙特区域数据裁剪脚本

## 2026-07-03

- 收到用户请求：查看 `/Volumes/E/气象数据` 全量目录的结构和少量样例，规划脚本以批量裁剪 DS1-DS4，并新增支持 DS10-DS11。
- 创建规划文件，准备进行轻量目录探查。
- 完成第一轮顶层目录探查；发现宽泛递归输出过大，后续改为每个子数据集只抽取少量文件名与元数据。
- 抽样确认 DS1/DS2/DS3 使用 GRIB2，DS4 使用 NetCDF，DS10 使用 HDF5，DS11 使用文本轨迹和 PNG 地图的混合目录结构。
- 读取 DS11 文本样例前 40 行，确认可通过 `Lat`、`Lon` 列做沙特区域过滤。
- 阅读现有 `saudi_data_extract.py`；确认它适合作为裁剪函数原型，但需要扩展为批量数据发现、DS10/DS11 适配和测试驱动的新结构。
- 创建正式实施计划：`docs/plans/2026-07-03-saudi-data-extraction.md`。
- 用户确认使用 conda `ml` 环境执行项目并要求按计划实现脚本。
- 创建隔离 worktree：`.worktrees/saudi-data-extraction`，分支为 `codex-saudi-data-extraction`。
- 完成 Task 1-6 实现并逐步提交：路径工具、数据发现、网格裁剪、DS10 HDF5、DS11 文本轨迹过滤、批处理 CLI。
- 由于 `ml` 环境没有 `pytest/xarray/cfgrib/netCDF4`，测试改用标准库 `unittest`；网格提取依赖改为按需导入，缺依赖时给出明确错误。
- 真实 DS10 FYMERG HDF5 样例结构为 `lat=(1,1800)`、`lon=(1,3600)`、`Pre_cal=(1,3600,1800)`，已补测试并支持 lon-lat 轴顺序裁剪。
- 真实 DS10 smoke test 输出：`output_saudi_smoke/ds10/202501/saudi_ds10_FYMERG_S_202501010000_E202501010029.npz`，包含 `lat=(160,)`、`lon=(220,)`、`Pre_cal=(1,220,160)`。
- 真实 DS11 smoke test 处理 5 个轨迹文件，均未穿过沙特 bbox，按设计记录为 `skipped_empty`。
- 用户安装了 `ml` 环境缺少的依赖后，确认 `xarray/cfgrib/netCDF4/h5py/numpy/pandas` 均可导入。
- 真实 DS1 GRIB2 smoke test 首次发现 cfgrib 会尝试在原始数据目录写 `.idx` 索引；已补测试并设置 `backend_kwargs["indexpath"] = ""` 禁用源目录旁索引写入。
- 真实 smoke test 结果：
  - DS1 输出 `latitude=160`、`longitude=220`，范围约 `16.0..31.9N`、`34.0..55.9E`。
  - DS4 输出 `lat=160`、`lon=221`，范围约 `16.05..31.95N`、`34.0..56.0E`。
  - DS10 输出 `lat=(160,)`、`lon=(220,)`、`Pre_cal=(1,220,160)`。
  - DS11 抽样轨迹未穿过沙特 bbox，记录为 `skipped_empty`。

## 2026-07-06

- 收到用户请求：建立一个子文件夹，对已裁剪沙特区域数据做洞察分析、初步可视化，并撰写图文并茂的数据分析报告。
- 读取现有规划文件、README、脚本和测试，确认仓库当前以 `/Volumes/E/气象数据/saudi_region_output` 作为已裁剪数据输出。
- 轻量查看分析输入目录，确认总量约 58G，包含 2025 年 `ds1` 月尺度、`ds2` 日尺度、`ds4` 海温和 `ds10_daily` 卫星降水聚合数据。
- 默认 Python 缺少 `xarray`；使用项目既有 conda `ml` 环境验证 `xarray/numpy/matplotlib` 可导入，并运行现有测试通过。
- 抽样读取 NetCDF/NPZ 元数据；发现 DS10 `npz` 中存在字符串字段，直接对所有数组求均值会触发类型错误，后续脚本只统计数值变量。
- 更新 `task_plan.md` 和 `findings.md`，新增阶段 7：数据洞察分析与图文报告。
- 按 TDD 新增 `tests/test_saudi_data_analysis.py`，覆盖数值摘要、填充值清洗、网格方向归一、真实布局聚合和 Markdown 报告生成。
- 新增 `analysis/analyze_saudi_region_output.py`，可读取已裁剪 `ds1/ds2/ds4/ds10_daily` 输出，生成 `summary.json`、4 张 PNG 图和 `saudi_data_insights_report.md`。
- 首次真实运行发现 DS1 多数月份 `prate` 全为缺测或填充值，补充测试和清洗逻辑，避免全 NaN、除零和超大填充值污染统计。
- 使用真实数据刷新报告：月尺度 12 个、DS2 日尺度 364 天、SST 365 天、DS10 日聚合 273 天；报告记录最高温日、最湿日和 DS1 月降水有效月份提示。

## 2026-07-07

- 收到用户请求：围绕 `compute_indicators.py` 撰写指标报告，说明每个指标含义、计算方法和计算后分布洞察。
- 读取规划文件、`compute_indicators.py`、`VARIABLES.md` 和仓库状态；确认已有真实指标输出位于 `/Volumes/E/气象数据/saudi_region_output/indicators`。
- 新增阶段 8：极端事件指标方法与分布洞察报告。
- 扫描 365 个 `saudi_indicators_YYYYMMDD.nc` 文件，确认单文件最多 73 个指标变量。
- 汇总核心指标年度分布：日累计降水、温度、湿度、CAPE、PWAT、IVT、风切变、SST 和 `flash_flood_risk`。
- 曾发现 DS10 卫星降水指标在指标 NetCDF 中全 NaN，但上游 `ds10_daily` NPZ 存在有效值；后续已修复为最近邻网格对齐并重算全年指标。
- 发现 `vpd_kpa` 与 `apparent_temp_c` 在 20250102、20250130 被派生异常值污染；报告中标为缺测值质控问题。
- 新增 `docs/saudi_extreme_event_indicator_report.md`，逐项说明指标含义、公式、单位、使用解释和 2025 年分布洞察。
- 用户要求修复 DS1 月降水指标来源；按 TDD 新增测试，要求加载 `ds1_acc` 并用 `MONTH_ACC tp/acpcp/ncpcp` 计算月降水指标。
- 修改 `compute_indicators.py`：新增 `ds1_acc` 加载、`days_in_month()` 和 `add_monthly_accumulation_indicators()`，保留 `MONTH_AVG` 用于辐射/热通量等月背景。
- 使用真实 20250101 数据输出到 `/private/tmp/saudi_indicator_smoke` 验证，`monthly_precip_total/monthly_precip_mmday/monthly_convective_precip/monthly_large_scale_precip/monthly_convective_precip_ratio` 均恢复有效。
- 用户指出图文分析报告仍显示“202511 为最高且只有 11 月有值”；排查发现 `analysis/analyze_saudi_region_output.py` 仍直接使用 `MONTH_AVG prate * 86400`。
- 按 TDD 修改分析脚本，优先使用 DS1 `MONTH_ACC tp / 当月天数`，并刷新 `analysis/summary.json`、`analysis/saudi_data_insights_report.md` 和月降水图。
- 刷新后月降水 12 个月均有效，最高月份为 202512，区域平均约 0.03 mm/day。
- 用户指出指标说明报告仍像旧版；同步更新 `docs/saudi_extreme_event_indicator_report.md`，将 DS1 月降水描述改为已按 `MONTH_ACC` 重跑且 365 个日指标文件均有效。
- 用户要求修复 DS10 卫星降水指标并做交叉验证；定位到 DS10 NPZ 半格偏移/纬度方向差异导致 xarray 精确坐标对齐成全 NaN。
- 按 TDD 修改 `compute_indicators.py`：DS10 指标最近邻对齐到指标网格，新增 DS10-DS2 降水差值、比值和强降水重叠标志，并限制 `flash_flood_risk` 只使用二维水平网格指标。
- 已重算 `/Volumes/E/气象数据/saudi_region_output/indicators` 全年 365 个指标文件；验证 DS10 指标 273 天有效，`flash_flood_risk` 365 天均为二维。
- 收到用户请求：指标将作为后续分析基础，需要确认指标确实针对沙特区域且计算准确；新增阶段 9：指标可信度质检。
- 使用 `conda run -n ml` 确认 `xarray/numpy/netCDF4` 可用，并确认 `/Volumes/E/气象数据/saudi_region_output` 当前挂载可读。
- 扫描 365 个指标 NetCDF：主网格均为 `latitude=160`、`longitude=220`，范围 `16.0..31.9N`、`34.0..55.9E`。
- 汇总源数据覆盖：`ds1=12` 个月、`ds2=364` 天、`ds4=365` 天、`ds10_daily=273` 天、`indicators=365` 天。
- 抽样复算 20250101、20250102、20250823、20251231 的关键指标；日/月降水、2m 温度、10m 风速和 DS10 对齐降水均与上游变量最大绝对误差 `0.0`。
- 定位当前不宜直接用于后续分析的指标问题：20250102/20250130 热湿变量填充值污染，以及 `cape` 为三维导致 `flash_flood_risk` 实际未使用 CAPE 项。
- 收到用户请求：确认 DS10 缺测是否可替代，并执行下一步指标质控修复。
- 按 TDD 新增两个回归测试：热湿派生指标计算前屏蔽填充值；三维 CAPE 折算为二维并参与 `flash_flood_risk`。
- 实现 `compute_indicators.py` 质控修复：新增统一数值清洗，清理地面温湿风和体感温度输入；新增稳定度变量二维化逻辑。
- 真实数据烟测写入 `/private/tmp/saudi_indicator_fix_smoke`：20250102/20250130 的污染热湿指标变为 NaN；20250823 的 `cape` 为二维，`flash_flood_risk` 仍为二维评分。
- 完整测试 `conda run -n ml python -m pytest -q` 通过：39 passed，1 个 numpy warning。
- 经用户授权，正式重算 `/Volumes/E/气象数据/saudi_region_output/indicators` 全年 365 个指标文件。
- 重算后 QA：365 个文件仍为 `latitude=160`、`longitude=220`，范围 `16.0..31.9N`、`34.0..55.9E`；热湿物理范围异常天数为 0；`cape` 293 天有效且二维；`flash_flood_risk` 365 天有效且最高分为 4。
- 收到用户请求：同步更新指标报告。已刷新 `docs/saudi_extreme_event_indicator_report.md` 中的指标数、空间范围、DS10 缺测替代口径、CAPE 二维化说明、热湿填充值修正、`flash_flood_risk` 年度统计和后续建议。
- 收到用户请求：检查数据 8 是否为多年气候态，并补充降水距平、SPI、500 hPa 高度距平、热浪持续天数等异常类预警指标。
- 探查 DS8：确认 `/Volumes/E/气象数据/8_SURF_CLI_GLB_1991_2020` 下有 PRE/TAVG/TMAX/TMIN 的逐日和逐月 1991-2020 normals 文本表；它是全球站点气候态，不是格点数据。
- 发现 DS8 文本行尾多一个逗号，pandas 默认读取会错位；正确解析需要 `index_col=False` 或等价的稳健 CSV 解析。
- 重新按正确列统计沙特 bbox 站点覆盖：逐日 PRE 7 个有效站点、逐日 TAVG 45 个有效站点、逐日 TMAX 11 个有效站点、逐日 TMIN 0 个有效站点。
- 形成实现口径：新增 DS8 站点 normals 最近邻映射后的降水和温度距平、热浪日标志及跨日连续日数；SPI 和 500 hPa 高度距平不伪计算，只在属性和报告中说明缺少所需历史分布/压力层气候态。
- 按 TDD 新增 `tests/test_compute_indicators.py` 用例，覆盖 DS8 尾逗号站点表解析、单日距平/热浪标志写出和多日热浪持续天数累加。
- 修改 `compute_indicators.py`：新增 DS8 自动发现、CSV 解析、逐日 365 天气候态选择、站点最近邻映射、降水距平、TAVG/TMAX 距平、热浪日标志、热浪持续天数回写，以及 `--climatology-root` CLI 参数。
- 使用真实 20250601 写入 `/private/tmp/saudi_indicator_ds8_smoke` 验证 DS8 自动发现和新增变量；降水气候态站点平均最近距离约 768 km，TMAX 约 346 km，提示报告需标注站点代表性限制。
- 正式重算 `/Volumes/E/气象数据/saudi_region_output/indicators` 全年 365 个指标文件，并回写 363 个有 TMAX 的 `heatwave_duration_days`。
- 年度 QA：指标文件仍为 365 个，统一网格 `latitude=160`、`longitude=220`，范围 `16.0..31.9N`、`34.0..55.9E`；单文件变量数更新为 26-91；365 天均带 DS8 气候态状态、SPI 未计算状态和 500 hPa 高度距平未计算状态。
- 新增异常指标覆盖：`daily_precip_anomaly` 363 天、`t2m_anomaly_c` 362 天、`tmax_anomaly_c` 363 天、`heatwave_duration_days` 363 天；局地最大热浪持续天数为 72 天，发生在 20250816。
- 更新 `docs/saudi_extreme_event_indicator_report.md`，加入 DS8 数据性质、异常类指标方法、2025 年统计、站点代表性限制、SPI 和 500 hPa 高度距平未计算原因。
- 最终验证 `conda run -n ml python -m pytest -q` 通过：42 passed，1 个已知 numpy warning。

## 2026-07-22

- 收到用户请求：先理解新建的参考工程目录与 GitHub 项目 `turgutino/mazu-saudi-warning`，为后续构建自有竞赛和论文方法做准备。
- 确认本地目录实际名为 `reference_code/`，包含三个已解压工程及对应 zip；本轮仅做只读分析，不修改参考代码。
- 在现有文件化计划中追加阶段 12：参考工程逆向理解与横向对比。
- 盘点 `reference_code/` 三个解压工程的目录、README、训练入口、标签构建、数据分割、评估脚本、知识图谱、Agent 和预报服务链路。
- 确认 LightGBM 工程主要是同日规则复现，其高 CSI 和 bbox 级“真实事件命中”不能作为提前预测证据。
- 确认 XGBoost V12 使用过去 24 日预测下一日，但存在高度重叠样本随机分割和城市阈值测试集调优问题；其 GSOD+ERA5 2015-2024 线路更有科研价值。
- 确认小组 3 代码主预报源已转为 ECMWF IFS，README 的 FourCastNet 说明已过时；复核了 EVT/分位门控的方向、百分位缩放和预报 lead-time fallback 风险。
- 通过 GitHub 公开 API 验证并临时读取 `turgutino/mazu-saudi-warning`；确认其核心是 `t→t+1` 的 HGB 次日预测、半年时序留出、灾种差异化空间特征和更完整的稀有事件/校准指标。
- 新增 `docs/reference_projects_review.md`，记录四个工程的方法、完成度、可复用资产、科研风险和自有方法的初步起点。
- 用户新增 `reference_code/吴诗华-刘贤君-报告+代码+PPT`；开始阶段 13，将其按相同评估口径纳入参考工程横向对比。
- 完成新增工程审查：确认其展示/服务闭环完整，但当前正式训练入口为同日随机切分 Random Forest，T+1 实现在 backup 文件中；现存模型与旧阈值混用，高温案例回退还存在未来日期泄漏。
- 已将第五个工程加入 `docs/reference_projects_review.md`，明确其适合作为行政区聚合、Agent 编排和解释服务参考，不适合作为未经修复的论文预测基线。
- 收到用户请求：综合五个参考工程的优点重新设计自有框架；启动阶段 14，采用文件化规划和领域建模，目标是产出竞赛与论文双轨、可直接实施的架构设计。
- 完成自有框架设计：建立 `CONTEXT.md` 统一时间、标签、概率、风险和预警术语；新增 `docs/own_warning_framework.md`，覆盖能力分级、领域边界、HAMF-Light、无泄漏评估、模型/政策制品、仓库结构和 P0-P4 路线。
- 记录四项架构决策：科学预报与预警决策分离、时间因果实验契约、模型包与政策包独立版本化、多灾种共享契约而不共享空间假设。
- 在 README 增加框架设计入口，使领域词汇、自有方案和参考工程评估可直接发现。
- 文档结构和本地链接检查通过；根目录 pytest 因收集未跟踪参考工程的需联网/需外部数据测试而失败，已记录并改用本仓库 `tests/` 作为适用测试范围。
- 本仓库适用测试 `conda run -n ml python -m pytest -q tests` 通过：42 passed，1 个既有 NumPy 二进制兼容 warning。

## 2026-07-23

- 收到用户请求：对 HAMF 创新假设进行文献查新，重点判断计算机技术/方案能否形成论文突破；启动阶段 15。
- 完成六组文献查新：多尺度/图 MoE、多灾种融合、物理图与神经算子、缺失模态、弱监督标签、尾部概率与空间事件验证。
- 确认 HAMF 原三分支、灾种门控、物理方向图、缺测降权和 EVT/校准均有强近邻，不能分别作为主要原创点。
- 新增 `docs/hamf_novelty_review.md`，给出近邻工作、创新矩阵、可发表性分层、最小论文问题、三个可证伪假设、实验基线与决策门。
- 将计算机方法候选收敛为 MCR-Hazard：可观测机制状态驱动路由、机制适用性软先验、物理反事实一致性，以及缺失关键模态时的选择性可靠退化。
- 修订 `docs/own_warning_framework.md`，将 HAMF-Light 明确降为强基线，避免继续以“多尺度 MoE + 物理图”作原创声明。
- 收到用户请求：评估还需哪些数据，并规划一个能够支撑 Nature Communications 级研究的数据集；启动阶段 16。
- 核对当前 2025 单年指标底座与 Nature Communications 对概念/方法推进、可复现数据和代码的要求，确认变量堆叠不能替代多年独立真值与科学问题。
- 检索 ERA5/ERA5-Land、IMERG、ISD、Sentinel-1、Global Flood Database、HydroSHEDS/MERIT、TIGGE/GEFS、GHSL/WorldCover、GloFAS、CAMS 和 OISST 等一手数据说明。
- 将第一主线收敛为 `AridFlash-MENA`：2001–2025 多区域干旱 Wadi 山洪数据，2014 年后增加 SAR 高分辨率子集，建立经过人工核验的 ephemeral-wadi graph。
- 新增 `docs/nature_communications_dataset_blueprint.md`，覆盖数据层、标签体系、规模目标、冻结切分、基准任务、质量控制、双论文策略和 Gate 0–3 执行路线。
- 更新 `docs/own_warning_framework.md`，加入 Nature Communications 级数据扩展入口；热浪仅在获得健康/影响数据后升级为主线。
- 用户确认无法稳定获取山洪独立真值，将论文主线调整为“干旱区短历时极端降水的跨区域可靠预测”。
- 启动阶段 17：将产出英文结果就绪稿、补充方法、参考文献、证据矩阵、图表计划、审稿风险和发表路线；所有未完成结果保留显式占位符。
- 新增 `docs/manuscript/` 论文包：英文主稿、补充方法、BibTeX 文献库、claim–evidence 矩阵、图表计划、审稿风险和 Gate 0–5 发表工作计划。
- 主稿标题 10 词、摘要 159 词，包含 62 个独立 `TODO-RESULT-*` 占位符；每类主张均有冻结产物、统计规则和降级条件。
- 新增 `tests/test_manuscript_contract.py`，覆盖 Nature Communications 标题/摘要限制、章节完整性、结果占位符、内部链接、科学边界和参考文献库。
- 同步更新 README、自有预警框架和旧 Nature Communications 数据蓝图，明确 Wadi 山洪已降为将来有独立真值时的下游扩展。
- 聚焦合同测试通过：`6 passed`。完整适用测试 `conda run -n ml python -m pytest -q tests` 通过：`48 passed`，仅 1 个既有 NumPy 二进制兼容 warning。
- 用户要求同时保留“预测方法论文”与“AI4Science 机制发现论文”两组初稿和后续试验计划，启动阶段 18。
- 根据近期一手文献收窄 AI4Science 问题：不重复已知 Rossby wave breaking 的日尺度贡献，而是研究大尺度强迫转化为 1–6 小时局地极值的机制类型及其对预报误差的解释。
- 新增 `docs/ai4science_manuscript/`：英文初稿 *Cross-scale atmospheric regimes govern sub-daily rainfall extremes across global drylands*、Experiment 0–6 试验计划、科学主张—证据矩阵和工作 BibTeX 文献库。
- AI4Science 稿标题 10 词、摘要 149 词、全稿约 3146 词，包含 41 个 `TODO-RESULT-AI4S-*` 结果占位符；明确区分发现、关联、物理一致、机制支持和因果声明。
- 新增 `docs/paper_portfolio.md`，规定论文 A 主张预测方法/校准/可靠性，论文 B 主张跨尺度机制图谱/物理验证/预报盲区；同一主要图表或统计比较不得同时成为两篇的标题结果。
- 新增 `tests/test_ai4science_manuscript_contract.py`，检查标题/摘要、章节、结果占位符、科学因果边界、Experiment 0–6、双论文非重叠条款、链接和文献库。
- 两套论文聚焦合同测试通过：`12 passed`。完整适用测试 `conda run -n ml python -m pytest -q tests` 通过：`54 passed`，仅 1 个既有 NumPy 二进制兼容 warning；7 个变更文档的本地链接检查通过。
- 用户选择实现论文 1（MCR-Precip 计算机方法线），启动阶段 19：参考现有工程的优点，从头实现本地四专家机制路由模型、损失、训练闭环和合同测试。
- 新增 `pyproject.toml`，将本仓库测试收集限制在 `tests/`，并建立 `src/mazu_saudi/mcr_precip/` 包。
- 完成稳定样本/输出合同、四传播专家、无区域 ID 的机制路由、可用性门控、单调分位数和不确定性输出。
- 完成机制适用性先验、KL 正则、反事实方向约束、稀有事件概率指标、risk–coverage、训练步骤和版本化模型包。
- 新增工程合成批次与 `scripts/train_mcr_precip_smoke.py`；3 步烟测成功保存模型包，明确标记 `scientific_evidence=false`。
- 新增 `docs/mcr_precip_implementation.md` 和 13 项 MCR-Precip 聚焦测试；聚焦测试 `13 passed`，全仓测试 `67 passed`，仅 1 个既有 NumPy 二进制兼容 warning。
- 用户希望进一步借鉴参考工程的工程化代码与页面，但认为现有前端简陋；启动阶段 20，采用文件化规划与网站构建规范，目标是独立的 MCR-Precip 服务层和现代化科研预警界面。
- 首轮盘点确认自有仓库没有前端/API；参考工程使用 Flask、Streamlit 和单文件知识图谱页，已记录其模型加载、场景预设、历史、Agent/KG 等可复用模式及科研语义风险。
- 新增标准库本地 HTTP 服务、版本化 forecast API 合同和离线前端，支持四区域、1/3/6 小时、概率/不确定性图层、四专家路由、数据可用性与审计轨迹。
- 首次 HTTP 集成测试因执行沙箱禁止绑定本地端口而出现 2 个 setup error；已改为对 API 分发与静态路径解析做无网络纯函数测试，保留独立的实际监听烟测。
- 以允许本地端口的环境完成真实监听烟测：`/api/v1/health`、阿拉伯半岛 +6h 预报（432 cells、跨日 valid time）和首页资源均正常返回，随后关闭临时服务。
- 新增 `docs/product_interface.md`，说明 API、启动方式、科学边界、从参考工程吸收/拒绝的模式和真实模型接入路线；阶段 20 首个产品垂直切片完成。

## 2026-07-26

- 用户新增多组参考程序并要求分析可借鉴点；启动阶段 21，继续使用统一科研/工程审计口径。
- 根据顶层修改时间和既有记录，初步锁定三组此前未审计工程；记录其规模并决定先做轻量目录/文本入口审计，不读取大模型或大数据制品。
- 完成新增“风险研判”工程的文档/源码边界审计，确认其预注册锁、真值隔离、双轨预测、停止状态和制品 Schema 是目前最值得借鉴的工程资产。
- 初审“生产实习最终报告”数据集、Analog Ensemble、评估与最终优化代码；确认多时效/可靠性诊断有价值，但随机格点切分、同日样本交叉污染、测试集校准和阈值优化使自报成绩不能直接继承。
- 补充确认该工程还把不可观测的末端未来标签填为负例，并把 climatology 误写成 persistence；这些实现不能直接复用。
- 一次尝试用 `tail` 查看 292 MB 单行 JSON 时仍触发了整行读取，已停止此类读取方式，后续改用流式键级检查。
- 完成 `计科2304` 推理代码、特征合同与报告核对：其分灾种轻量模型、失败记录和标准 JSON 值得借鉴，但全年事件模板包含未来事件/目标日场，高温标签统计矛盾且无训练源码，不能复用自报指标。
- 将三组新增工程加入 `docs/reference_projects_review.md`，把横向地图扩展为八个工程，并给出面向 Historical Common-Core、MCR-Precip 和 MAZU Atlas 的分级吸收顺序。
- 新增 `tests/test_reference_projects_review_contract.py`，锁定工程名称、预注册/不可观测/测试污染/未来模板边界及自有框架映射；聚焦测试 `3 passed`。
- 全仓适用测试通过：`76 passed`，仅保留 1 个既有 NumPy 二进制兼容 warning；阶段 21 完成。

## 2026-07-27

- 用户询问如何把全部新增代码和设计思想整理进自有工程；启动阶段 22，使用文件化规划形成可执行迁移蓝图。
- 恢复既有计划并盘点当前代码：确认数据脚本、MCR-Precip 科研内核和 MAZU Atlas demo 服务已存在，而数据契约、事件切分、实验注册、基线库和版本化结果制品仍未落地。
- 初步决策是不复制参考工程或一次性重排目录；先建立可信证据链和制品层，再把 Analog/机制原型作为独立基线接入，最后让服务与 Agent 只消费冻结结果。
- 使用领域建模补充实验锁、预报制品、评估制品和报告制品四个统一术语，并新增 ADR 0005，锁定“参考工程是设计输入而非代码依赖”。
- 新增 `docs/reference_asset_migration_blueprint.md`：包含现状缺口、八来源落位矩阵、目标目录、依赖方向、五类合同、基线/MCR/Atlas 接入方式、Slice 1–5 和推荐提交拆分。
- 更新 README 与自有框架入口；新增 `tests/test_reference_asset_migration_blueprint.py`，与参考审计合同一起聚焦测试 `7 passed`。
- 全仓适用测试通过：`80 passed`，仅保留 1 个既有 NumPy 二进制兼容 warning；阶段 22 完成。

## 2026-07-29

- 用户要求优先完成比赛，依据 `docs/requirement/` 四张要求图评估现有数据处理、
  指标、`warning_demo` 和论文框架的创新性与工程完成度。
- 恢复既有规划文件，确认四张 PNG 位于未跟踪的 `docs/requirement/`，本轮只读查看。
- 启动阶段 23：先提取比赛要求，再以仓库证据审计创新主张、完成度、风险和最小增强路线。
- 已查看前两张要求图并持久化要点：材料与数据合规/原创承诺，以及英文 Word 应用解决方案报告的必交要求。
- 已查看后两张要求图：英文产品原型与模型设计 Word、英文演示 PPT、三分钟内英文演示视频均为必交；中文对应版本为可选。
- 完成第一轮仓库与模型产物盘点：确认真实数据链、MCR-Precip 方法代码、两套前端/服务并存；记录 `warning_demo` 三灾种指标、代理标签边界和两项山洪未泛化负结果。
- 核对 MCR-Precip 源码与 MAZU Atlas 服务：原创机制路由核心确已实现且有测试，但只完成合成训练闭环；Atlas 为显式 demo backend，尚未连接真实模型与数据。
- 核对数据覆盖、正式交付文件、Agent 依赖和合规资产：四件英文主件均不存在；DeepSeek 工具编排实际已完成；数据授权清单/数据卡/项目许可证和地图合规证据尚缺。
- 完成 `docs/competition_innovation_audit.md`：将当前方案定位为“系统与可信工程创新已成立、MCR 方法创新仍待真实验证”，并给出 P0–P2 比赛最小增强路线。
- 新增 `tests/test_competition_innovation_audit_contract.py`，锁定四件英文交付物、代理标签/demo 边界、真实指标弱点和合规优先级。
- 首次 staged diff 检查发现审计文档三处行尾空格，已清理并记录；文件内容未受损。
- 用户确认实施 MCR-Precip 比赛版真实对比；启动阶段 24，限定为现有 2025 数据、
  同一 T+1 代理任务和公平时间切分，不扩展外部数据或通用大模型。
- 完成首轮数据与基线脚本审计：确认 228 MB 合并数据可直接使用；决定采用
  Jan–May/June/July–December 的 train/validation/test 切分，并继续核对地形通道。
- 核对实际变量与运行依赖：合并数据无地形、环境依赖齐全；识别 MCR 时效合同需从
  1/3/6 小时显式扩展到 24 小时，首版收敛到强降水代理任务。
- 确认同源地形文件可只读接入，并初步确定 stride=4、训练期归一化、验证集选阈值、
  同输入 HGB / 无约束 MoE / MCR 三方对比的实现方案。
