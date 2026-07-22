# 发现记录：沙特区域数据裁剪脚本

## 数据目录发现

- 数据根目录存在：`/Volumes/E/气象数据`。
- 顶层实际数据目录包括：
  - `1_NAFP_ART_ATM_GLB_MONTH_PROD`
  - `2_NAFP_ART_SFC_GLB_DAY_PROD`
  - `3_NAFP_ART_SFC_GLB_MONTH_PROD`
  - `4_OCEA_FUS_DAY_PRO`
  - `5_OCEA_GLB_MUL_FTM_DATA`
  - `8_SURF_CLI_GLB_1991_2020`
  - `9_SATE_CLOUD_PRODUCT_AWX`
  - `10_SATE_PRECIPITATION_PRODUCT_2025`
  - `11_TCGD_MON_GLB_PROD`
- 顶层还存在 macOS AppleDouble 元数据文件/目录，如 `._10_SATE_PRECIPITATION_PRODUCT_2025`，脚本需要跳过所有 basename 以 `._` 开头的路径。
- DS1 目录按月份组织，如 `202501` 到 `202512`。
- DS2 目录按日期组织，如 `20250101`、`20250601` 等。
- DS4 目录按日期组织，如 `20250101` 到 `20251231`。
- DS10 目录按月份组织，如 `202501` 到 `202509`。
- DS11 目录同时出现 `2025` 年目录和 `202510DD` 日期目录。
- DS11 日期目录下一层为预报/分析时次目录，例如 `t00z.20251001`、`t06z.20251001`、`t12z.20251001`、`t18z.20251001`。
- DS11 时次目录内包含大量 `track_*.txt` 文本轨迹文件，也包含 `*_map.png` 图片文件。

## 文件格式发现

- DS1 样例文件为 `.grib2`，命名包括：
  - `ART_SINGLE_GLB_0P10_MONTH_SFC_202501.grib2`
  - `ART_SINGLE_GLB_0P10_MONTH_AVG_202501.grib2`
  - `CRA_RT_TEM_202501_GLB_MONTH_V1_0_0.grib2`
- DS10 样例文件为 `.h5`，命名如 `FYMERG_S_202509022230_E202509022259.h5`，看起来是 30 分钟卫星降水反演产品。
- DS11 样例文件为 `.txt` 轨迹文件，目录中也有 `.png` 地图产品；脚本需要优先解析文本轨迹，地图图片可先跳过或只复制元数据索引。
- `file` 确认 DS1/DS2/DS3 样例均为 `Gridded binary (GRIB) version 2`。
- `file` 确认 DS4 `.nc` 样例实际是 HDF5 容器，DS10 `.h5` 也是 HDF5 容器。
- 样例文件大小：
  - DS1 `ART_SINGLE_GLB_0P10_MONTH_SFC_202506.grib2`: 15,207,403 bytes
  - DS2 `ART_SINGLE_GLB_0P10_DAY_SFC_20250601.grib2`: 17,587,246 bytes
  - DS3 `ART_SINGLE_GLB_0P10_MONTH_SFC_202506.grib2`: 15,207,403 bytes
  - DS4 `Z_OCEN_C_BABJ_20250601180000_P_CODAS_GLB_0P10_6HOR_SST.nc`: 6,507,789 bytes
  - DS10 `FYMERG_S_202509302330_E202509302359.h5`: 3,073,163 bytes
  - DS11 `track_99_0.txt`: 281 bytes
- DS11 文本表头为 `Ini Fcst Lat Lon Vmax Pmin`，可按列名解析并过滤经纬度。
- 真实 DS10 FYMERG HDF5 样例内部结构：
  - `Pre_cal shape=(1, 3600, 1800) dtype=float32`
  - `lat shape=(1, 1800) dtype=float32`
  - `lon shape=(1, 3600) dtype=float32`
- DS10 裁剪后 smoke test 输出范围：
  - `lat`: 16.05 到 31.95，160 个格点
  - `lon`: 34.05 到 55.95，220 个格点
  - `Pre_cal`: `(1, 220, 160)`
- 宽泛递归 `find` 会产生巨大输出，后续必须按具体目录使用 `-print -quit` 或小样例列表。

## 现有脚本发现

- `saudi_data_extract.py` 当前定义沙特 bbox：`LAT_MIN=16.0`、`LAT_MAX=32.0`、`LON_MIN=34.0`、`LON_MAX=56.0`。
- 已有函数：
  - `extract_grib2(grib_file_path, output_name, level_type="surface")`
  - `extract_netcdf(nc_file_path, output_name)`
  - `extract_all(data_root)`
  - `demo()`
- 当前 `extract_all()` 只处理硬编码的 202506/20250601 样例路径，且文件名仍使用 `*_AVG_*`，但实际样例中 DS1/DS2/DS3 也存在 `*_SFC_*` 等产品类型。
- 当前脚本没有目录发现器，没有日期范围参数，没有 dry-run，没有跳过已存在输出，没有错误日志。
- 当前脚本不支持 DS10 HDF5 卫星反演降水，也不支持 DS11 文本轨迹数据。
- 当前脚本导入 `xarray`、`cfgrib`、`netCDF4`、`numpy`；本机当前默认 Python 和 Codex 捆绑 Python 都没有 `xarray/cfgrib/netCDF4/h5py`，实现需要在 README/依赖中明确安装。

## 风险与注意事项

- 原始数据超过 2T，探查时应限制深度和样例数量。
- 需要兼容不同数据源的经纬度命名、经纬度方向、时间维度和文件格式。
- 需要过滤 `._*` 元数据文件，否则 HDF5/GRIB/NetCDF 打开时可能报错。
- DS11 的“沙特区域提取”不应按网格裁剪理解，而应按文本轨迹中的经纬度点过滤，保留与沙特 bbox 相交的 track 文件或 track 点。

## 数据洞察分析发现

- 本次分析输入目录为 `/Volumes/E/气象数据/saudi_region_output`，目录总量约 58G。
- 已裁剪输出包含 `ds1`、`ds2`、`ds4`、`ds10`、`ds10_daily` 等目录。
- `ds1` 存在 202501-202512 月目录，样例月平均文件网格为 `latitude=160`、`longitude=220`。
- `ds2` 存在 2025 年日目录，样例日地表文件包含 `t2m`、`d2m`、`u10`、`v10`、`r2` 等变量，日累计文件包含 `tp`、`acpcp`、`ncpcp`。
- `ds4` 样例 SST 文件网格为 `lat=160`、`lon=221`，变量为 `analysed_sst`。
- `ds10_daily` 样例文件包含 `daily_total`、`max_30min`、`max_1h`、`max_3h`、`max_6h`、`rainy_steps` 等数值变量，也包含 `date`、`source_files` 等字符串字段；分析脚本必须跳过非数值数组。

## 指标报告发现

- 已计算指标输出位于 `/Volumes/E/气象数据/saudi_region_output/indicators`，覆盖 20250101-20251231 共 365 个日文件。
- 单个指标文件最多包含 73 个指标变量，覆盖月尺度地表背景、云量、日降水、热湿、稳定度、多层动力、水汽输送、SST、DS10 卫星降水和山洪筛查分数。
- `daily_precip_total` 有效 363 天，区域日均值全年平均约 0.23 mm，局地最大值 254.9 mm，发生在 20250823。
- `t2m_c` 有效 362 天，区域日均值全年平均约 27.09 degC，最高日区域均值 35.98 degC，局地最大值 45.90 degC，发生在 20250717。
- `sst_celsius` 全年 365 天有效，区域均值约 27.78 degC，局地最大值 36.90 degC，发生在 20250822。
- 曾发现 `ds10_daily_total`、`ds10_max_1h` 等 DS10 指标在指标 NetCDF 中 0 天有效，但上游 `ds10_daily/*.npz` 存在有效数据；现已定位为坐标对齐问题并修复。
- `vpd_kpa` 和 `apparent_temp_c` 在 20250102、20250130 出现明显派生异常，说明后续需要在派生指标前统一清理 GRIB 缺测值。
- DS1 月降水只有 202511 有效的问题来自旧版指标脚本使用 `MONTH_AVG prate/cpr`；原始 `MONTH_AVG` 多数月份本身缺测，但裁剪后的 `MONTH_ACC tp/acpcp/ncpcp` 12 个月都有有效值。
- `compute_indicators.py` 已改为加载 `ds1_acc` 并使用 `MONTH_ACC` 计算月累计降水、月平均降水强度和月对流降水比例；20250101 真实数据 smoke test 输出月降水相关指标均有 35200 个有效网格。
- `analysis/analyze_saudi_region_output.py` 也曾使用 `MONTH_AVG prate` 生成图文报告中的月平均降水率，已改为优先使用 `MONTH_ACC tp / 当月天数`；刷新后 12 个月均有效，最高月份为 202512，区域平均约 0.03 mm/day。
- DS10 指标全 NaN 的根因是 DS10 NPZ 网格相对 DS2/指标网格有半格偏移且纬度方向不同，xarray 按精确坐标对齐时把 DS10 数组对齐为空；已改为最近邻对齐到指标网格。
- 重算后 DS10 卫星降水指标 273 天有效，有效日每个 DS10 变量均为 35200 个网格；新增 `ds10_ds2_precip_diff`、`ds10_ds2_precip_ratio`、`ds10_ds2_heavy_rain_overlap` 做 DS10 与 DS2 降水交叉验证。
- `flash_flood_risk` 曾被带 `pressureFromGroundLayer` 的三维变量广播为三维；已限制为只使用二维 `latitude/longitude` 指标，重算后 365 天均为二维评分。

## 指标可信度质检发现

- 当前 `/Volumes/E/气象数据/saudi_region_output/indicators` 下有 365 个指标文件，文件名覆盖 `saudi_indicators_20250101.nc` 到 `saudi_indicators_20251231.nc`。
- 365 个指标文件的主网格完全一致：`latitude=160`、`longitude=220`，纬度范围 `16.0..31.9N`，经度范围 `34.0..55.9E`。这与 `saudi_data_extract.py` 中的沙特裁剪 bbox `16.0..32.0N, 34.0..56.0E` 一致。
- 该区域是沙特 bbox 裁剪框，不是行政边界 land-only mask；网格中会包含红海、波斯湾和边界附近非沙特陆地区域。
- 源数据覆盖：`ds1=12` 个月、`ds2=364` 天、`ds4=365` 天、`ds10_daily=273` 天、`indicators=365` 天。
- 核心覆盖率：`monthly_precip_total/monthly_precip_mmday` 365 天全网格有效；`daily_precip_total` 363 天有效，缺 `20250818`、`20250820`；`sst_celsius` 365 天有效；`ds10_daily_total` 273 天有效，缺口主要是 `20251001..20251231` 无 DS10 日聚合源数据；`ivt` 291 天有效，缺口来自多层分析变量覆盖不足。
- 抽样复算 `20250101`、`20250102`、`20250823`、`20251231`：`daily_precip_total == ds2_acc tp`、`monthly_precip_total == ds1_acc tp`、`t2m_c == ds2_sfc t2m - 273.15`、`wind10_speed == sqrt(u10^2+v10^2)`、可用日期的 `ds10_daily_total` 与对齐后的 NPZ 日聚合值最大绝对误差均为 `0.0`。
- 明确问题：`t2m_c`、`heat_index_c`、`apparent_temp_c` 在 `20250102`、`20250130` 被填充值污染；`vpd_kpa` 在这两天全网格异常，另外 `20250212`、`20250306`、`20251216` 有少量接近 0 的负值。
- 明确问题：`cape` 在样例文件中维度为 `pressureFromGroundLayer, latitude, longitude`，不是二维水平网格；当前 `flash_flood_risk` 只接收二维指标，因此实际评分未使用三维 CAPE 项。
- DS10 缺测替代口径：`ds10_daily_total` 缺测时可用 DS2 `daily_precip_total` 作为日总降水替代参考；但 DS10 的 `max_30min/max_1h/max_3h/max_6h` 是短历时峰值，DS2 日累计产品不能真实替代，只能在解释 `flash_flood_risk` 时说明该短时项不可用。
- 已修复 `compute_indicators.py`：计算热湿派生指标前清理超大填充值和明显非物理值；`cape/cin/lifted index` 等带额外层维度时折算为二维水平网格。真实烟测中 `20250102/20250130` 的污染热湿值变为 NaN，`20250823` 的 `cape` 变为二维且可参与 `flash_flood_risk`。
- 正式重算 `/Volumes/E/气象数据/saudi_region_output/indicators` 后，365 个指标文件仍为同一沙特 bbox 网格；`t2m_c/vpd_kpa/heat_index_c/apparent_temp_c` 的物理范围异常天数均为 0；`cape` 293 天有效且维度为 `latitude, longitude`；`flash_flood_risk` 365 天有效且最高分为 4。

## DS8 气候态数据发现

- DS8 目录为 `/Volumes/E/气象数据/8_SURF_CLI_GLB_1991_2020`，文件名和字段均表明它是 1991-2020 多年气候态 normals。
- DS8 不是 NetCDF/GRIB 网格产品，而是全球站点 ASCII 表，包含 `PRE`、`TAVG`、`TMAX`、`TMIN` 四类变量，每类有逐日 `MDAY` 和逐月 `MMON` 两种表。
- 逐日表字段为 `id,wmo_id,lat,lon,alt,normals_number,001d..365d`；逐月表字段为 `id,wmo_id,lat,lon,alt,normals_number,001m..012m`，`PRE/MMON` 额外有 `annual`。
- 缺测码为 `-999`。文件每行末尾有多余逗号，使用 pandas 读取时必须指定 `index_col=False`，否则第一列会被误当索引并导致字段错位；脚本实现应清理列名空白并忽略多余空列。
- 按当前指标 bbox `16.0..32.0N, 34.0..56.0E` 统计，逐日 PRE 有 7 个有效站点，逐日 TAVG 有 45 个有效站点，逐日 TMAX 有 11 个有效站点，逐日 TMIN 没有有效站点。
- DS8 可支撑站点气候态映射后的降水距平、TAVG/TMAX 温度距平和基于 TMAX 的热浪日/连续日数；但不能单独支撑正式 SPI，因为 SPI 需要多年降水序列或分布参数，而 DS8 仅提供均值 normals。
- DS8 也不能支撑 500 hPa 位势高度距平，因为它是地面站点气候态，缺少压力层位势高度气候场。该指标需要压力层历史或气候态基线。

## 参考工程初步盘点（2026-07-22）

- 本地参考目录实际名为 `reference_code/`，三个已解压工程的文件数约为 92、550、47；同目录 zip 为重复副本，分析以已解压目录为准。
- `mazu_saudi_ewai_deploy` 自述为三层混合架构：四灾种独立 LightGBM 预测、NetworkX 空间传播知识图谱、OpenAI 兼容 LLM Function Calling，并用 Gradio 交付。输入直接是当前仓库产生的 2025 年指标 NetCDF。
- 该 LightGBM 工程的 README 声称 6–8 月训练、10 月测试时四灾种 CSI 约 0.99–1.00，全年留一月交叉验证 CSI `0.932±0.042`。这些远高于常见灾害预测表现，需重点审计标签是否由同日特征规则生成、空间邻近格点是否被随机分到训练/测试集，以及真实事件验证是否仅使用年内同源指标。
- `孙佳斌-张恒卓-代码-saudi_mazu_agent` 是迭代最多的工程：七灾种 XGBoost、规则标签、逐灾种排除直接标签特征、7/14 日时序统计特征、城市阈值、Flask Web、LLM 报告，另含 ERA5/GSOD 外部数据管线。文档主动承认仅一年数据、规则派生标签、0.1°日尺度无法捕捉对流降水极值等局限。
- 该 XGBoost 工程自述最佳为 V12：21 变量的 7/14 日统计扩展到 210 维，12 城 F1=0.792；RotatE KG 嵌入、物理交互特征、LightGBM 和按月时序分割均未改善。其“随机时序分割最优、按月分割不适用”的结论在科研上不能直接接受，更可能揭示分布偏移与随机分割的高估风险。
- `小组3-项昱翔-戚语轩-黄兴民` 偏规则和知识工程：DMDO-OWL/RDF/SPARQL 知识图谱、91 指标 DAG、四灾种加权规则与六区域校准、FourCastNet 1–7 天预报、DeepSeek Agent、Flask+Streamlit 服务。
- 小组 3 的特色是 GPD POT、Gamma CDF 和经验联合分布门控，但气候态同样只用 2025 单年估计。文档将 `min(F1,...,F4)` 称为“Copula min”并又说“假设变量独立”，概念上需严格复核；湿热联合指标的方向与 `<=0.05` 规则也可能不一致。
- GitHub 项目 `turgutino/mazu-saudi-warning` 无法通过网页直接打开（cache miss），搜索也未收录该仓库；搜索命中的是同一作者的通用 AI coding-agent 项目 `turgutino/Mazu`，与沙特天气工程不同，不应混为一谈。下一步将用 GitHub 公开 API 核实目标仓库是否存在/可见。
- GitHub API 已确认目标仓库存在且公开，创建于 2026-07-08，最近推送为 2026-07-21，默认分支 `main`，未声明开源许可证。因此可学习方法，但不应直接复制代码进入自有参赛/论文仓库。
- `turgutino/mazu-saudi-warning` 与其他工程共用当前仓库生成的 2025 年指标，但任务定义更严格：用第 `t` 日 17 个核心指标+空间/季节特征预测 `t+1` 日的规则派生标签，1–6 月训练、7–12 月测试，主模型为 `HistGradientBoostingClassifier`。
- 该 GitHub 项目对热浪的结果相对有效：加四邻域均值后 ROC-AUC=0.971、PR-AUC=0.795；对山洪 ROC-AUC=0.873 但 PR-AUC=0.089，在 0.5 阈值下 POD=0.10、FAR=0.803、CSI=0.071，说明排序有信号但远不足以运营部署。沙尘预测 ROC-AUC=0.887、PR-AUC=0.164，同样存在高 FAR。
- GitHub 项目的 ST-GNN 在山洪 ROC-AUC 上提升、但 PR-AUC 下降且静稳日风险溢出；固定邻域均值提升热浪、伤害山洪。这是一个可复用的科研命题：空间平滑适合大尺度持续灾害，但会抹平局地对流极值，需要灾种感知的自适应空间机制。
- `mazu_saudi_ewai_deploy` 的正式 `train_all()` 直接在 6–8 月全数据拟合并保存，没有内部验证/测试；全年留一月 CV 也只验证山洪标签。山洪标签是同日 `flash_flood_risk>=1`，特征又是组成该指标的同日降水/CAPE/湿度等；沙尘和风浪标签更直接由入模变量规则生成。因此高 CSI 是规则复现能力，不是真实灾害预报能力。
- 该 LightGBM 工程的“10 次真实事件验证”仅用事件当日的同源指标进行检测，并以全 bbox 高风险格点比例 `>5%` 为“命中”，未验证事件地点空间重合；不可称为独立 ground truth 预测验证。
- XGBoost V12 的特征窗口确实是过去 24 天预测第 25 天，但正负格点样本打乱后 85/15 分割，临近时间和空间样本高度相关；12 城评估又直接在全年城市输出上取 P95 阈值。所以 V12 F1 可用于工程比较，不能当作严格样本外证据。
- XGBoost 工程的 GSOD+ERA5 线路更值得继承：标签是站点实测温度/风速，特征是前 24 日 ERA5，2015–2023 训练、2024 测试。其 AUC 具有真实跨年意义，但报告的最优 F1 阈值是直接在 2024 测试预测上搜索，需重分训练/验证/测试年份。
- 小组 3 的实际主预报管线已改为 ECMWF IFS 0.25°，README 仍声称 FourCastNet，本地交付包也不含 README 中的 `run_fcn.py`。其 IFS 管线能从地面/压力层场派生指标并执行规则，但有多个近似：用单时次 2m 温度代替日最高温、用区域场均值代替格点气候态计算温度距平、预报小时缺失时默认取任意可用文件。
- 小组 3 的最新 `rules.json` 已将湿热联合门控从错误的 `<=0.05` 改为 `>=0.95`，但 IFS 两条路对湿热风速方向仍不一致：一处仅用 RH+T，另一处用未取反的风速 CDF，会把高风而非低风视为更湿热。此外 `_lookup_percentile()` 输入百分位 50–99 却裁剪到 `[0,1]`，可能使联合门控大面积饱和为 1。

## 新增工程初步盘点（吴诗华-刘贤君）

- 首次追加本节时因预期标题与文件实际标题不一致导致 `apply_patch` 校验失败；已读取文件尾部并改为以实际末行追加，未造成文件内容损坏。
- 工程同时提供 PDF 报告、PPTX、完整 Python 服务代码、示例/产出数据、两类模型产物，以及一个约 568MB 的 Windows `.venv`；目录体积主要不是业务代码。
- 业务链路初看包含区域代理映射、特征构建、极端高温/山洪模型、风险评分、案例检索、知识图谱校验、智谱 LLM 报告、FastAPI 与 Streamlit。
- 后续必须把材料中的效果与“真实代码到底使用何种数据、标签、切分和阈值”对齐，尤其避免把样例数据或同日规则拟合误当成可提前预报能力。
- PDF 报告共 18 页、PPT 共 26 页；两份材料一致声称两灾种、13 个代理区、连续分数、区×灾种×月百分位、KG 校验、案例检索、Agent 编排和 GLM 报告，并明确只有 2025 单年和伪标签。
- 当前入口 `scripts/02_train_models.py` 导入的是 `app/modeling/train.py`：它用 RandomForest、随机 80/20 行切分，并以同日输入特征的加权归一化构造同日目标；这不是 README 所述 D+1。
- 真正实现 `shift(-1)` 次日目标与日期前 80%/后 20%切分的是 `app/modeling/targets.py` + `train_backup.py`，但该文件名为 backup，当前训练入口没有调用它，且其中部分中文字符串已乱码。
- `OrchestratorAgent._load_row()` 取请求日期本身的区域行，随后把结果字段硬编码为 `lead_time: T+1`。在当前正式入口训练出的模型下，这是把同日诊断标成 T+1，属于关键任务定义错误。
- 模型目录同时残留两代互相冲突的元数据：`*_meta.json` 报告时序切分的山洪 R²=0.652、高温 R²=-1.151；`*_model_meta.json` 报告随机切分同日规则复现 R²≈0.994/0.996。极高者不代表次日预报能力，高温真正时序验证甚至劣于均值基线。
- PPT/报告只做定性“合理性、图谱、报告质量”描述，没有披露上述负 R²，也没有给出真实事件标签上的 POD/FAR/CSI/PR-AUC、概率校准或空间命中。
- PDF 文本提取首次指定的捆绑 `pdftotext` 路径不存在，已改用系统 `/opt/homebrew/bin/pdftotext` 成功；PPT 渲染工具默认在源文件旁生成预览目录，后续视觉核验后仅删除该临时目录。
- 当前两个 `.joblib` 在 17:59 随同日 Random Forest 训练被覆盖，但 `*_thresholds.json` 分别停留在 15:01/17:30 的旧次日模型；当前推理跨模型代际复用阈值，风险等级不可靠。
- 两张区域特征表都是 13 区×365 日=4745 行；每个区月仅约 28–31 个样本，单年 P90 既不稳定，又按构造保证约 10%日期进入 HIGH，不能解释为灾害概率。
- 高温案例回退不限制 `case_date < query_date`。交付示例查询 2025-07-15，却返回 2025-07-24、07-28、07-30 作为“历史参考过程”，存在明显未来信息泄漏。
- KG 校验实际是四项布尔规则完整度，案例检索是灾种/区域/月/关键词符号加权，证据置信度也是人工公式；它们适合可解释展示，不是语义推理、气象相似场检索或统计置信度。
- 业务代码目录约 328KB，Windows `.venv` 约 538MB；工程无测试文件，且文档 Python 3.11 与虚拟环境 3.12 不一致。
- 已完成 PPT 视觉核验并删除仅由本轮渲染产生的预览目录；原 PPTX、PDF 和参考工程内容未修改。
