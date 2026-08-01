# Knowledge Graph Rebuild Plan

## Goal

从当前前端的预测解释与相似案例需求出发，全新设计并实现一套可追溯、可验证、可查询的知识图谱，不继承旧讨论的结论；现有代码与 `reference_code` 只作为输入和可复用资产接受审查。

## Phases

- [x] Phase 1 — 盘点前端、mock、后端、数据与 `reference_code`，明确真实接入契约
- [x] Phase 2 — 调研 SWEET、已有气象/灾害知识图谱与论文证据，形成可引用依据
- [x] Phase 3 — 全新定义领域模型、图谱分层、推理语义、相似案例与溯源契约
- [x] Phase 4 — 实现本体/模式、知识构建管线、种子知识与校验
- [x] Phase 5 — 实现解释、路径推断、相似案例检索 API，并接入前端替换 mock
- [x] Phase 6 — 增加聚焦测试、运行完整适用测试与端到端验证
- [x] Phase 7 — 完成架构/数据建设文档、更新领域词汇并提交 scoped git commit
- [x] Phase 8 — 固定历史 HGB / 实时融合模型边界与输出元数据契约
- [x] Phase 9 — 实现四灾种实时融合路由，将合成规则模型移出正式预测链
- [x] Phase 10 — 补充聚焦测试并运行后端完整测试
- [x] Phase 11 — 审查最终差异并提交 scoped git commit

## Guardrails

- 不把阈值命中或模型相关性表述成已证明的因果关系。
- 当前预测的解释必须区分模型证据、规则/机制知识、观测事实与历史案例。
- 相似案例必须严格早于当前预报起报时刻，并显示相似维度与数据来源。
- 外部本体采用固定版本的映射/裁剪，不无边界导入。
- 不改动或提交用户无关的工作区变化。
- 本轮仅改造预测模型选择与实时融合路由，不扩展到新数据管道或新模型训练。
- 已有 `backend/app/data/models.py` 和 `backend/tests/test_prediction_service.py` 未提交变更与本任务直接相关，只做必要整合，不覆盖其已有意图。

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| `rg` 同时搜索不存在的根目录 `tests` 返回状态 2 | 1 | 后续只搜索仓库实际存在的 `backend/tests`。 |
| 前端图页移除 mock chat context 时遗留了不完整 `useEffect` | 1 | 通过带行号复查定位并删除遗留语句。 |
| 全量 TypeScript 检查发现既有 `MonitorReading` 缺少被风险计算使用的 `precipitation` 字段 | 1 | 补齐接口、实时映射和 8 个 mock 读数，使既有风险代码的类型契约一致。 |
| 在仓库根目录串行运行 npm 校验，因 `package.json` 位于 `frontend/` 而失败 | 1 | 后端测试结果有效；前端命令改在 `frontend/` 工作目录单独执行。 |
| 浏览器端到端测试的 3001 开发端口未在 CORS 白名单，预检返回 400 | 1 | 将 localhost/127.0.0.1:3001 加入开发白名单并重启后端。 |
| 相似案例 UI 将 API 的 `null` 最高温渲染为“°C” | 1 | 类型显式允许 `null`，并用非空检查控制指标显示。 |
| 浏览器控制台发现模型卡片 `<button>` 内嵌展开 `<button>` 的非法 HTML | 1 | 外层改为支持键盘操作的 `role=button` 容器，保留内部独立按钮。 |
| 完整 pytest 发现 Open-Meteo 测试仍构造旧 `current` 响应，而实现已改为目标时刻 `hourly` 响应 | 1 | 将测试夹具固定起报时刻并更新为两时次 hourly 数据，同时验证选中目标时次。 |
| 首次实时融合批量补丁与 `degraded_model.py` 实际文案不完全匹配 | 1 | 改为按实际文件内容分文件小步补丁。 |
| 聚焦测试发现 Mirror Earth provider 返回 `None` | 1 | 移除 `with_overrides` 时漏保留返回语句，补回 `return overrides` 后重跑。 |
| 后端全量测试有 6 个图谱测试依赖旧合成 Tier3 隐式产生预测 | 1 | 为这些服务集成测试显式 mock 实时指标，不恢复正式链的合成回退。 |
| 清理旧名称文档的批量补丁未匹配 `with_overrides` 实际换行 | 1 | 拆成独立小补丁，避免影响已完成的功能代码。 |
| 沙箱内 `git add` 无法写入 `.git/index.lock` | 1 | 按仓库提交要求申请已批准的 git 暂存权限后成功。 |
