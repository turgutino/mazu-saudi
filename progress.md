# Knowledge Graph Rebuild Progress

## 2026-08-01

- 启动全新知识图谱设计与实现任务。
- 读取 `planning-with-files` 与 `domain-modeling` 技能要求。
- 确认根目录已有遗留 `CONTEXT.md`，后续只在新模型术语稳定后做增量修订。
- 当前阶段：Phase 1，仓库与接入契约盘点。
- 已确认当前前端图页仍完全依赖 mock；后端虽有图 endpoint，但只做展示对象拼装。
- 已识别两项必须替换的遗留逻辑：机制边的轮流连接、仅用概率接近度的静态相似案例。
- 完成 `reference_code` 第一轮审查：确定只借鉴数据字段与显式关系，不复制其静态图/Neo4j/全本体导入架构。
- 完成第一轮外部研究：SWEET 采用固定版本裁剪对齐；风险语义参考 DMDO/DPO；案例检索采用多变量 analog 距离；模型归因与机制相容证据严格分层。
- 实现知识库加载与一致性校验、机制相容性推理、三维相似案例检索和富图谱 API 契约。
- 接通工作台创建预测 → 预测详情 → 解释图谱的真实 FastAPI 链路，移除这条用户路径中的固定 mock ID。
- 新增 5 项知识库专项测试；最终完整 pytest 74 项通过。
- 前端 type-check、ESLint 与 production build 全部通过。
- 应用浏览器端到端验证通过；修复测试中发现的 3001 CORS、null 指标渲染和嵌套按钮错误。
- 已发现并隔离其他并发工作区改动，提交时只暂存本任务文件/片段。
- 启动实时融合模型改造：保留 2025 历史 HGB 模型，将现有退化模型升级为四灾种实时融合模型，正式链路移除合成指标规则模型。
- 当前阶段：Phase 8，核对模型元数据、路由与 API 契约。
- Phase 8/9 完成：实时模型身份改为 `live-fusion-v1`；四灾种统一尝试 CMA/Open-Meteo + Tomorrow.io；服务结果记录实际运行模型元数据；正式链移除 `RuleBasedForecastModel`。
- 实时 provider 改为只返回真实 API 字段，不再用伪随机指标补齐缺失值。
- 当前阶段：Phase 10，运行聚焦和完整验证。
- Phase 10 完成：实时融合聚焦测试 47 项通过；后端完整 pytest 103 项通过；前端 type-check、ESLint 与 production build 通过。
- 当前阶段：Phase 11，最终差异审查与提交。
- Phase 11 完成：`git diff --check` 通过，变更范围只包含实时融合模型、provider 真实字段契约、模型注册表和相关测试/进度文档。
- 启动双模式工作台改造：实时预测使用实时融合，2025历史回放使用归档指标和对应HGB。
- 已确认根因：前端日期入口太晚，后端 `MAZU_INDICATORS_DIR` 未设置；本机2025归档实际完整存在。
- 当前阶段：Phase 12，固定双模式契约。
- Phase 12/13 完成：API请求新增 `predictionMode`；`historical`强制HGB+归档且禁止静默降级，`live`强制实时融合。
- 后端在无环境变量时自动发现本机归档目录；空环境变量可显式禁用。
- 后端聚焦测试41项通过，并完成真实2025 NetCDF + HGB推理实测。
- Phase 14 完成：工作台新增“实时预测 / 2025历史回放”首步骤；历史日期提前选择，并按预报时效检查实际特征日；模型步骤只展示当前模式真正运行的一个模型。
- Phase 15 完成：后端完整 pytest 107 项通过；前端 type-check、ESLint 与 production build 全部通过。
- 浏览器实测通过：历史模式中暴雨禁用，极端高温正确展示自有 HistGradientBoosting 模型；实时模式中暴雨可选且只展示实时多源融合模型。
- 真实归档推理验证：Jazan / extreme-heat / 2025-06-01 / 24小时成功读取106项指标并运行 `joblib-heatwave`，模型层级为 `tier1_real`。
