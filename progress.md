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
