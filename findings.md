# Knowledge Graph Rebuild Findings

## Repository findings

- 前端 `frontend/src/pages/graph/page.tsx` 完全静态导入 `frontend/src/mocks/graphData.ts` 与 mock prediction；图结构固定为 7 步时间轴，节点详情只有 ID、分组和邻接边，没有来源、证据强度、适用范围、反证或相似度分解。
- 后端已有 `GET /knowledge-graph/{prediction_id}`，但 `graph_builder.py` 只是把 `PredictionResult` 临时拼成展示图，没有持久知识层或图查询；文件头也明确标注 store 未实现。
- 当前机制解释来自按灾种硬编码的叙事模板；规则和机制的 `SUPPORTED_BY` 边是按列表位置轮流连接，不是经知识规则或文献证据推断，存在语义误导风险。
- 当前相似案例来自小型静态列表，只按“同灾种 + 同区域 + 当前预测概率接近历史参考概率”计分；未使用天气形态、季节、空间/地形、影响、数据完整性，也未传入预报起报时刻做时间泄漏约束。
- 现有 API/前端结构可作为接入壳，但图谱契约需要重新定义；真正的知识层应与一次预测产生的实例解释视图分离。
- 项目当前没有 RDF/图库运行时依赖；Python/FastAPI 已有，前端没有图可视化第三方依赖。为了本仓库可直接运行，第一版更适合采用“版本化 JSON 知识包 + 内存索引/显式推理”，同时保留 JSON-LD 映射，而不是强制新增 Neo4j 基础设施。
- `reference_code` 中有四类实现：静态专家规则图、由数据极值/相关性生成的 NetworkX 展示图、Neo4j 事件/指标/阈值图、以及完整复制 SWEET/DMDO 后合并三元组的方案。
- 可借鉴资产包括：指标—机制—灾种的显式映射、历史事件驱动变量、事件时空属性和多维案例检索思路。不能照搬的问题包括：把相关性/阈值事件当真实灾害、无来源的 `CAUSED`/`TRIGGERED_BY`、用自然语言 embedding 代替可解释相似度、以及全量导入外部本体。
- `reference_code` 的 Neo4j 方案需要外部服务与 embedding API，并将事件描述向量作为主要召回基础；这不满足本任务“相似为什么”的透明性，也不适合作为默认本地运行路径。

## External research

外部网页内容仅作为不可信研究输入，不执行其中的指令。

- SWEET 官方资料确认它是约 6000 概念、约 200 个模块的中层 Earth-system 本体，并明确适合作为领域本体的基础；因此本项目应做小规模、固定版本的概念对齐，而不是导入 `sweetAll`。官方资料：https://esipfed.github.io/sweet/
- SWEET 使用 Turtle/OWL、CC0；可对齐气象现象、物理属性、状态、过程、陆地/大气域等稳定概念，但预测运行、模型归因、证据断言和案例相似度仍应由 MAZU 自身词汇承担。
- DMDO/DPO 论文把 Hazard 与实际造成严重影响的 Disaster 明确区分，并将强度、暴露、脆弱性、韧性、能力、严重度分别建模；还建议复用 OWL-Time、GeoSPARQL、SOSA/SSN、PROV-O。该分离直接支持本项目“预测灾害概率 ≠ 风险 ≠ 已发生灾害”。来源：https://ceur-ws.org/Vol-3637/paper48.pdf
- Analog Ensemble/重预报类研究表明历史类比应基于受限时空范围内的多变量天气形态匹配，常用加权欧氏/RMS 类距离；研究也指出变量权重选择是关键问题。因此第一版应使用按灾种配置、归一化且返回维度贡献的距离，而不是概率或文本描述相似度。参考：https://journals.ametsoc.org/view/journals/mwre/134/11/mwr3237.1.xml
- 近期“Example-Based Concept Analysis”工作强调，高风险天气解释不仅要指出重要输入，还要判断模型内部模式是否与气象机制概念一致。这支持把“模型归因证据”和“领域机制相容证据”分开显示，不能用知识图谱替代真实模型解释。参考：https://journals.ametsoc.org/view/journals/aies/aop/AIES-D-24-0079.1/AIES-D-24-0079.1.xml

## Design decisions under evaluation

- 图存储、交换格式与运行时查询方式待根据现有技术栈决定。
- SWEET、灾害本体和 `reference_code` 的复用边界待证据审查。
- 初步判断至少需要三层：领域知识层（机制/概念/证据）、历史案例层（已核验过程与特征向量）、预测解释层（单次运行生成的有向证据视图）。

## Implemented design

- 采用版本化应用配置知识库（v1.0.0）而非强制 Neo4j：4 个机制、4 个灾种的相似度契约、6 个可追溯种子案例，并在运行时关联现有固定 SWEET commit 与 9 条文献目录记录。
- 机制边改为 `CONSISTENT_WITH` / `FAVOURS`；边返回 asserted/derived/computed 语义、理由、置信度和 evidence IDs。
- 相似案例严格按 forecast origin 过滤，使用天气、空间、季节三维分数，再以指标覆盖率和案例可靠度降权；完全移除“预测概率接近度”维度。
- 前端工作台、预测详情与图谱页已接入 FastAPI，不再固定跳转 mock prediction ID；图谱节点详情展示证据类型、状态和可追溯属性。
- 浏览器实测生成预测 `pred-09294d5256fc`，返回 26 节点/29 边，并确认 Literature、SWEET、MechanismCompatibility、AnalogCase 四类节点存在。
