# MAZU Saudi Arabia Multi-Hazard Early Warning Agent

面向沙特的 MAZU 多灾种早期预警智能体算法研发项目。

本项目围绕中国气象局 MAZU 系列早期预警系统“多灾种、预警、零差距、普惠”的核心定位，以沙特阿拉伯为目标合作国家，针对热带沙漠气候下的突发性暴雨、极端高温干旱、沙尘和沿海风浪等高影响灾害，构建从全球多源气象数据中提取沙特区域数据、生成轻量化预警特征、并服务 MAZU 系统嵌入式部署的算法原型。

当前仓库首先解决数据工程基础问题：从海量全球气象产品中裁剪沙特阿拉伯及周边关键区域，为后续多灾种预警模型、知识图谱和大模型决策模块提供统一的数据底座。

## Framework Design

基于八个参考工程的横向审查，本项目已经形成面向竞赛与论文的自有框架设计：

- [领域词汇表](CONTEXT.md)：统一预报起报时刻、有效时刻、标签、灾害概率、风险和预警等级等概念。
- [自有预警框架](docs/own_warning_framework.md)：定义 MAZU-Saudi HAMF 的领域边界、科研核心、无泄漏评估、服务架构和实施路线。
- [参考工程评估](docs/reference_projects_review.md)：记录八个参考工程可吸收的资产和不能直接继承的结论。
- [参考资产迁移蓝图](docs/reference_asset_migration_blueprint.md)：将八个工程的思想映射到自有模块、合同、制品、测试和分批实施顺序。
- [干旱区短历时极端降水论文包](docs/manuscript/README.md)：英文结果就绪稿、补充方法、证据矩阵和发表路线。
- [双论文组合与贡献边界](docs/paper_portfolio.md)：区分 MCR-Precip 计算机方法论文与 AI4Science 机制发现论文的问题、证据和发表顺序。
- [AI4Science 论文包](docs/ai4science_manuscript/README.md)：跨尺度机制图谱、物理验证、预报盲区及分阶段试验计划。
- [MCR-Precip 本地实现](docs/mcr_precip_implementation.md)：论文 1 的四专家机制路由、输入合同、训练闭环和烟测命令。
- [MAZU Atlas 产品界面](docs/product_interface.md)：本地预测 API、现代化科研预报页面、演示边界与启动方式。

当前开发原则是先建立可信的高温/山洪 `t→t+1` 科研基线，再扩展到高频预报场、HAMF-Light、多灾种风险决策和 Agent 交付。

## Competition Topic

**参赛题目：面向沙特的 MAZU 多灾种早期预警智能体算法研发**

联合北京化工大学人工智能团队、国家卫星气象中心国际用户服务中心，依托全球大气再分析、地表实况、海表温度、卫星云图等多源气象数据资源，研发面向沙特本地化应用的轻量化、智能化、可嵌入 MAZU 系统的多灾种早期预警算法。

项目强调两点：

- **算法创新**：提取水汽输送、对流初生、海温距平、热力胁迫等具有物理意义的灾害触发特征，支撑轻量化时空 AI 模型。
- **场景落地**：面向沙特气象、应急、农业、港航等部门，输出可部署、可迭代、可解释的预警服务能力。

## Target Region

当前数据裁剪范围覆盖沙特阿拉伯及红海、波斯湾周边关键区域：

| Item | Range |
|------|-------|
| Latitude | 16.0N - 32.0N |
| Longitude | 34.0E - 56.0E |
| Grid resolution | 0.1 degrees, about 10 km |

该范围既覆盖沙特本土，也保留红海水汽输送、波斯湾海温背景、吉达港等沿海灾害风险分析所需的周边信息。

## Data Resources

本项目面向以下 11 类全球气象数据产品开展沙特区域提取与特征构建。大数据原始目录位于本机：

```text
/Volumes/E/气象数据
```

数据清单：

1. 全球大气再分析产品 V1.5
2. 全球表面实况分析产品 - 逐日产品
3. 全球表面实况分析产品 - 逐月产品
4. 全球海表温度实况融合分析产品
5. 全球海表观测定时值数据集 V3.0
6. 全球地面积雪深度日值数据集 V1.0
7. 全球 10km/3h 有效波高多源融合实况分析产品 V1.0
8. 全球地面气候标准值（1991-2020）
9. 全球卫星云图拼图产品
10. 卫星反演天气数据
11. 气象站报告天气情况数据

当前脚本已实现 DS1-DS4 的沙特区域裁剪，并新增 DS10 卫星反演降水 HDF5 与 DS11 气象站/热带气旋轨迹文本的沙特区域提取能力。DS5-DS9 将作为后续多源融合、灾害标签构建和承灾体关联分析的数据扩展方向。

## Repository Structure

```text
.
|-- README.md                    # Project overview and usage
|-- AGENTS.md                    # Repository development guidelines
|-- CONTEXT.md                   # Domain vocabulary (forecast origin, valid time, labels...)
|-- VARIABLES.md                 # DS1 variables and Saudi extreme weather relevance
|-- saudi_data_extract.py        # Saudi region extraction script (DS1-DS4, DS10, DS11)
|-- compute_indicators.py        # Extreme-event indicator computation from clipped data
|-- analysis/                    # Data insight analysis, figures, and report
|-- docs/                        # ADRs, framework design, manuscripts, product interface
|   |-- adr/                     # Architecture decision records
|   |-- manuscript/              # Paper A: MCR-Precip method manuscript package
|   `-- ai4science_manuscript/   # Paper B: AI4Science mechanism-discovery manuscript
|-- src/mazu_saudi/               # Installable package
|   |-- mcr_precip/              # MCR-Precip model, losses, training, evaluation
|   `-- service/                 # Local forecast API service and web UI
|-- tests/                       # Unit and contract tests
`-- reference_code/               # Untracked, read-only reference projects (design input only)
```

## Current Capabilities

`saudi_data_extract.py` 提供三类能力：

- 从 CMA GRIB2 文件中裁剪沙特区域并保存为 NetCDF。
- 从 NetCDF 文件中自动识别经纬度坐标并裁剪沙特区域。
- 生成 30 天沙特合成样例数据，用于在真实数据准备完成前调试模型流程。

支持的数据示例：

| Dataset | Format | Current use |
|---------|--------|-------------|
| DS1 全球大气再分析产品 V1.5 | GRIB2 | 降水、辐射、热通量等极端天气特征 |
| DS2 全球表面实况分析产品 - 逐日产品 | GRIB2 | 日尺度地表实况特征 |
| DS3 全球表面实况分析产品 - 逐月产品 | GRIB2 | 月尺度气候背景与异常分析 |
| DS4 全球海表温度实况融合分析产品 | NetCDF | 红海、波斯湾 SST 背景信号 |
| DS10 卫星反演天气数据 | HDF5 | 高频卫星降水反演 |
| DS11 气象站报告天气情况数据 | TXT | 轨迹点按沙特 bbox 过滤 |

## Installation

建议使用 Python 3.10+ 环境。本项目当前按 conda `ml` 环境执行：

```bash
conda activate ml
pip install xarray cfgrib netCDF4 h5py numpy
```

GRIB2 读取依赖 `cfgrib` 和 ECMWF ecCodes。如果本机缺少 ecCodes，需要先按操作系统安装对应运行库。DS11 文本轨迹过滤只依赖 Python 标准库；DS10 HDF5 提取需要 `h5py` 和 `numpy`。

## Usage

### Run demo data generation

无需真实数据即可生成沙特区域 30 天合成样例数据：

```bash
python saudi_data_extract.py demo
```

输出：

```text
output_saudi/saudi_sample_30days.npz
```

### Discover supported files without extracting

```bash
python saudi_data_extract.py discover /Volumes/E/气象数据 \
  --datasets ds1,ds2,ds3,ds4,ds10,ds11 \
  --limit 3 \
  --dry-run
```

### Batch extract supported datasets

```bash
python saudi_data_extract.py batch /Volumes/E/气象数据 \
  --datasets ds1,ds2,ds3,ds4 \
  --start 202501 \
  --end 202512 \
  --output output_saudi
```

```bash
python saudi_data_extract.py batch /Volumes/E/气象数据 \
  --datasets ds10 \
  --start 202501 \
  --end 202509 \
  --output output_saudi
```

```bash
python saudi_data_extract.py batch /Volumes/E/气象数据 \
  --datasets ds11 \
  --start 20251001 \
  --end 20251031 \
  --output output_saudi
```

批处理默认写入 `manifest.jsonl` 和 `errors.jsonl`，并跳过已存在输出文件。需要重跑时可以加 `--overwrite`。

### Extract all legacy sample datasets

```bash
python saudi_data_extract.py all /Volumes/E/气象数据
```

脚本会在数据根目录下查找当前已适配的 DS1-DS4 示例路径，并将沙特区域结果输出到 `output_saudi/`。

### Extract one GRIB2 file

```bash
python saudi_data_extract.py your_file.grib2
```

也可以指定 GRIB2 层级类型：

```bash
python saudi_data_extract.py your_file.grib2 surface
python saudi_data_extract.py your_file.grib2 isobaricInhPa
```

### Extract one NetCDF file

```bash
python saudi_data_extract.py your_file.nc
```

## Output

所有裁剪结果默认写入当前目录下的 `output_saudi/`：

```text
output_saudi/
|-- saudi_ds1_surface_avg_202506.nc
|-- saudi_ds2_surface_avg_20250601.nc
|-- saudi_ds3_surface_avg_202506.nc
|-- saudi_sst_20250601_0000.nc
|-- ds10/
|-- ds11/
|-- manifest.jsonl
|-- errors.jsonl
`-- saudi_sample_30days.npz
```

全球原始数据通常体量巨大。裁剪后仅保留沙特区域网格，可显著降低存储、训练和推理成本，为轻量化预警算法嵌入 MAZU 系统提供基础。

## Load Extracted Data

```python
import xarray as xr

ds = xr.open_dataset("output_saudi/saudi_ds1_surface_avg_202506.nc")

precip_rate = ds["prate"]      # kg/m^2/s
precip_mm_day = precip_rate * 86400

print(ds)
print(float(precip_mm_day.max()))
```

更多 DS1 变量解释见 `VARIABLES.md`。

## Warning Algorithm Roadmap

后续算法研发可以按以下链路推进：

1. **区域数据裁剪**：从全球产品中稳定提取沙特及周边关键区域，统一保存为 NetCDF 或面向训练的数据切片。
2. **物理算子构建**：围绕沙特灾害机理构建水汽通量散度异常、对流初生指数、红海/波斯湾 SST 距平、昼夜非对称热力胁迫指数、近岸风浪耦合算子等特征。
3. **轻量化时空模型**：使用轻量级 CNN、ST-LSTM、GNN 或注意力模型预测未来 3-24 小时极端降水、高温干旱、沙尘和沿海风浪风险。
4. **知识图谱与大模型决策**：将模型输出与沙特本地承灾体信息关联，生成面向气象、应急、农业、港航等部门的预警文本和处置建议。
5. **MAZU 系统嵌入**：以模块化方式输出风险概率、触发因子、影响区域和建议动作，满足快速部署与持续迭代要求。

## Saudi Disaster Focus

重点关注的灾害场景包括：

- **突发性沙漠暴雨与 Wadi Flash Floods**：关注红海水汽输送、强对流初生、短时强降水和地形汇流风险。
- **极端高温与干旱**：关注太阳辐射、感热通量、潜热通量、地表热储存、夜间高温维持和土壤干旱背景。
- **沙尘与强风过程**：关注近地面风场、动量通量、干旱裸地条件和能见度影响。
- **沿海港航风险**：关注红海和波斯湾沿岸的海温、风场、有效波高和风浪耦合风险。

## Development Notes

- 原始气象数据体量大，不应提交到 git。
- 生成结果默认位于 `output_saudi/`，建议按实验批次归档。
- 每次扩展新的数据产品时，应优先明确经纬度坐标、时间维度、变量单位和缺测值编码。
- 每个新增数据源建议配套一个小样本验证流程，确保裁剪范围、坐标方向和输出变量正确。
- 本仓库测试使用标准库 `unittest`，可在 conda `ml` 环境中运行：`python -m unittest discover -s tests -v`。
