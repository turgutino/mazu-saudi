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
