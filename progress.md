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
