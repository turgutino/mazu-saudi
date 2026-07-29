# MAZU 应用与运行入口

本仓库只有一个可启动的产品入口。开发、演示和提交比赛时，以本文件为应用生命周期的
唯一说明。

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

## 2. 历史预警研究资产

**状态：非应用 / 主应用的只读科学依赖**

`research/historical_warning/` 保存经过核验的模型、工具、数据、证据、实验和报告。
比赛后端通过适配器读取 `agent/tools.py`，并仅把 `reports/` 挂载到
`/reports-static`。

旧静态页面、页面生成器和重复图片已经删除；有用的展示内容和媒体由
`competition_app/` 统一维护。该研究目录没有 HTML 入口、服务启动脚本或独立端口，
不得在其中新增产品页面。

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
  → research/historical_warning/agent/tools.py
  → research/historical_warning/{data, agent/saved_models, kg}

mazu_saudi.competition
  → runtime/competition_app
```

比赛前端不直接读取 NetCDF、模型文件或知识图谱。

## 已删除的产品原型

早期 `mazu_saudi.service` / MAZU Atlas 合成演示服务已删除。它没有进入比赛应用，也没有
进入 MCR 科研训练链。未来若需要产品化 MCR，只允许从冻结预测与评估制品建立新的后端，
不得恢复合成概率冒充真实运行。
