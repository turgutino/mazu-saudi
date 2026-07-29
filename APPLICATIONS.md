# MAZU 应用与运行入口

本仓库只有一个当前产品入口，其余可视化界面是研究原型或历史归档。开发、演示和提交比赛
时，以本文件为应用生命周期的唯一说明。

## 1. 比赛主应用：Historical Warning Console

**状态：当前产品 / 唯一比赛入口**

| 层 | 位置 | 职责 |
|---|---|---|
| React 前端 | `competition_app/` | 预警演练、事件诊断、证据网络、决策简报和提交材料 |
| FastAPI 后端 | `src/mazu_saudi/competition/` | 历史演练 API、审计、报告、CAP Exercise 和前端托管 |
| 启动入口 | `scripts/start_competition_app.sh` | 前端构建、制品预检和统一启动 |
| 运行状态 | `runtime/competition_app/` | SQLite、报告、证据包和 CAP；不进入 Git |

```bash
./scripts/start_competition_app.sh
```

默认访问 `http://127.0.0.1:8765`。比赛演示、截图、视频和功能开发都应从这里开始。

## 2. MCR-Precip 研究原型：MAZU Atlas

**状态：冻结的研究原型 / 非比赛入口**

`src/mazu_saudi/service/` 是较早建立的 MCR-Precip API 与静态界面垂直切片。它使用
确定性 demo backend，只用于保留未来 MCR 产品化的接口设计，不提供比赛当前的真实历史
推理、审计、证据图谱或报告能力。

如需专门研究该原型，可显式启动：

```bash
PYTHONPATH=src python -m mazu_saudi.service.server \
  --host 127.0.0.1 --port 8766
```

它默认使用 `8766`，避免与比赛应用冲突。新的比赛功能不得加入这个目录。

## 3. Legacy Archive 与科学资产

**状态：只读展示归档 + 被主应用复用的科学资产**

`warning_demo/` 同时包含两类内容：

- `index.html`、`kg_view.html`、`agent_view.html`：旧版静态研究展示，由比赛应用挂载在
  `/legacy`，不再承担首页职责。
- `agent/tools.py`、`agent/saved_models/`、`data/`、`kg/`、`model/`：经过核验的模型、
  工具、数据和证据资产，比赛后端通过适配器读取。

因此 `warning_demo/` 不能整体删除，但新的产品页面也不应继续写入这里。

## 不是应用的目录

- `src/mazu_saudi/mcr_precip/`：科研模型内核。
- `analysis/`：数据分析脚本与已生成洞察。
- `scripts/`：训练、对比、启动和维护入口。
- `experiments/`：冻结实验结果。
- `docs/`：论文、架构决策、比赛和产品文档。
- `competition_app/dist/`、`runtime/`、`node_modules/`：本地生成物，均不进入 Git。

## 依赖方向

```text
competition_app
  → /api/v1
  → mazu_saudi.competition
  → warning_demo/agent/tools.py
  → warning_demo/{data, saved_models, kg}

mazu_saudi.competition
  → runtime/competition_app

mazu_saudi.service
  → DemoForecastService
  → 独立研究原型页面
```

比赛前端不直接读取 NetCDF、模型文件或知识图谱；研究原型也不应反向依赖比赛应用。
