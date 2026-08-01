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

## Live fusion model findings

- 当前 `PredictionService` 只在灾种存在 joblib 模型时尝试 Mirror Earth / Open-Meteo，导致 `heavy-rain` 无条件进入合成数据规则模型。
- `DegradedForecastModel` 已能处理四灾种及实时 API/Tomorrow.io 有限特征，可作为实时融合模型的现有实现起点。
- `RuleBasedForecastModel` 依赖 `IndicatorProvider` 合成指标，应保留给测试，但不再由正式 `PredictionService` 调用。
- 请求中的 `modelId` 目前只是展示元数据，结果应改为记录实际运行模型的 ID/版本/名称。

## Historical replay findings

- 工作台将可选起报时间藏在最后确认步骤，模型选择发生在日期之前，用户无法建立“2025日期 → 历史HGB”的清晰心智模型。
- `MAZU_INDICATORS_DIR` 当前未配置，但本机真实归档位于 `/Volumes/E/气象数据/saudi_region_output/indicators`。
- 归档含 `saudi_indicators_20250101.nc` 至 `saudi_indicators_20251231.nc`，共365个逐日文件。
- HGB 特征日是 `target_date - 1 day`；在24小时时效下等于起报日期，其他时效必须仍由后端通过实际文件存在性判定。
- 已使用2025-06-01吉赞高温+24h直接实测本机归档：成功加载106个指标并运行 `joblib-heatwave`，返回 `tier1_real`和概率0.0012。

## Live fusion rule correction findings

- Open-Meteo 官方文档明确：小时 `precipitation` 是“前一小时”的累计/平均量，不是日累计；当前把目标小时单值写入 `daily_precip` 属于时间尺度错误。官方文档同时支持 `past_days` 返回前一天数据，可用于构造目标时刻之前的完整24小时累计窗口：https://open-meteo.com/en/docs
- 当前 `normalized_severity` 没有截断，CAPE 6000 在配置上限3200之外产生1.65严重度；实时规则应将严重度严格限制在[-1, 1]，避免单一越界值无限放大。
- Tomorrow.io 当前接的是 realtime endpoint，不能把当前时刻的阵风/火险/雷暴概率混入6—72小时目标时刻；未来预测应只使用与目标时刻对齐的小时预报字段。
- 实时融合结果应命名为“风险评分”而非观测校准概率；当前 calibration 是恒等函数，不能赋予频率概率含义。
- 修正规则后的真实 Open-Meteo 冒烟结果（Jazan暴雨、+6h）：CAPE 6000、目标前24h降水0、温度34、湿度66、风速10.1、能见度20.28；CAPE严重度被正确截断为1，贡献0.9，零降水贡献-1.0，最终风险评分0.4013，不再出现旧规则的0.7513越界放大。

## API-compatible live ML findings

- 第三方接口返回的是带有效时刻的小时预报场，不是灾害预测；实时ML应作为数值预报的统计后处理层。
- 2025逐日归档共365个文件，每个文件包含160×220格点和约90个指标/标签；可直接构建格点日训练样本，无需依赖缺失的合并 `mazu_dataset.nc`。
- 归档与Open-Meteo/CMA最终稳定对齐的必需特征为24小时累计降水、24小时平均/最高/最低2m温度、24小时平均10m风速、经纬度和年内日序。CAPE只有293/365日覆盖，因此仅作为可选存储/解释指标，不参与必需ML合同。
- 高温标签 `heatwave_day_flag` 和山洪标签 `flash_flood_risk>=2` 来自现有数据；沙尘暴现有标签由规则构造，只能标记为代理标签；暴雨可用目标日累计降水阈值构建气象事件代理标签，不能称为灾害影响标签。
- 仅一年数据不适合LSTM/Transformer；按时间切分的HistGradientBoosting基线更可控，在线输入由API小时序列聚合成与训练完全同名同单位的特征。
- 部分2025逐日文件缺少 `wind850_speed`；沙尘暴规则代理标签必须按当天实际可用条件权重归一化，且模型元数据必须保留此弱监督事实。
- 训练实际使用363个完整归档日中的按步长抽样格点（另3日缺必需字段并记录跳过），1—6月393,800样本训练，7—12月398,200样本验证。
- 验证集结果：高温AUC 0.9846 / FAR 0.5161；山洪AUC 0.8421 / FAR 0.8166；沙尘暴代理AUC 0.9901 / FAR 0.6236。山洪与沙尘暴空报率仍高，不能表述成生产级高精度灾害模型。
- 强降雨标签与输入中的24小时累计降水同源，验证AUC=1属于阈值关系泄漏，不代表独立预报技巧；前后端模型描述已明确提示这一限制。
- 真实Open-Meteo端到端预测确认API返回的是小时要素；后端聚合并持久化原始JSON（4636字符）和13个派生指标，再运行真实joblib HGB。相同目标小时的第二次预测复用同一快照。

## Real model attribution findings

- `LiveApiForecastModel` 与 `JoblibForecastModel` 当前都把输入原值写入 `important_features`；前端和图谱却标记为SHAP贡献，构成语义错误。
- 当前开发环境存在SHAP 0.50.0，但 `pyproject.toml` 尚未声明依赖；正式实现必须加入可复现依赖并验证对 sklearn 1.7 HistGradientBoostingClassifier 的解释输出。
- SHAP 0.50.0 的TreeExplainer已实测支持项目两类 HistGradientBoostingClassifier。采用无额外背景数据的 `tree_path_dependent` 模式解释raw margin：实时暴雨样例 `base=-10.312786`、SHAP和 `-0.008445`、模型margin `-10.321232`；历史高温样例同样满足加和一致性。
- 正式API必须同时返回归因方法、输出尺度、基线和模型原始输出；前端以正负方向显示log-odds贡献，不称为概率百分点。
- 历史HGB包含最多27个原始/邻域特征，而现有展示层只识别少量 `INDICATOR_SPECS` 并静默丢弃其余特征；真实归因实现必须保留完整模型特征集合，对未知常模的特征显示实际值但不虚构“正常值”。
- 开发SQLite共有4条旧预测：2条 `live-api-hgb-heavy_rain/live-api-daily-v1` 保存了完整8特征，可用同一制品安全回填；1条 `live-fusion-v1` 与1条 `ensemble-v4` 已无对应制品，不能改用当前HGB解释。
- 回填后两条HGB记录均保存 `tree_shap/raw_log_odds`、8个特征、基线 `-10.312786` 和模型输出 `-10.321232`；两条淘汰模型记录的 `features` 为0并保存明确不可用原因。
- 监测地图当前由三个React hook在页面挂载时直接访问Open-Meteo、Mirror Earth CMA和Tomorrow.io；Open-Meteo另有30分钟定时重复请求，三者都不查询后端数据库。
- 后端 `/monitor/regions` 仍返回静态占位数据；既有 `forecast_data_snapshots` 是按预测目标时刻/特征版本缓存的模型输入，不适合直接充当监测页面多区域、多数据源快照。
- 截图参数通过当前 `PredictionService` 直接运行成功（Riyadh/高温/2025-06-01/24h，概率0.1126），但正在监听8000端口的uvicorn进程返回500；失败来自运行进程而非归档缺失。
- 参考工具明确使用 `target_date-1` 的整日指标预测 `target_date` 风险；当前历史HGB是T+1日模型，而前端错误复用了灾种通用时效列表。
- 运行进程500的精确原因是Riyadh样本 `sst_celsius=NaN`：HGB可处理NaN，但Starlette严格JSON序列化拒绝非有限浮点。API/数据库现在以 `null` 保留缺测语义，模型内部仍使用NaN推理。
- 图谱节点按容器实测宽高布局，但原SVG视口首次固定为900×600；宽屏下节点可能落在视口外，“重置视图”因同步了真实尺寸才让节点出现。
- 图谱节点原先直接按完整标签计算尺寸，长模型名、文献名和机制描述会产生过宽节点；画布标签应有稳定上限，完整文本通过SVG悬停提示和节点详情保留。
- 当前 `PredictionResult.rawIndicators` 已保存模型与机制计算所见的真实输入，实时预测还保存不可变 `forecastSnapshotId/source`；因此无需新建图库或重复抓取数据即可补全来源链。
- 最小正确图模型确定为：`InputSnapshot -PROVIDES-> IndicatorValue -USED_BY-> Model -GENERATED-> Prediction`，Tree SHAP作为 `Prediction -HAS_ATTRIBUTION-> IndicatorValue` 的计算边；同一指标值再通过 `USES/CONSISTENT_WITH` 连接政策规则和机制，避免值节点与归因节点重复膨胀。
- 运行图目前只为模型特征建节点，机制实际读取但模型未使用的 `rh_surface/visibility` 等指标会从图中消失；正式本体2.0.0也未随运行图返回版本或指标IRI。
- 真实历史复核发现 `RealIndicatorProvider` 仍通过旧 `with_overrides` 为归档不存在的T850/H500/地表湿度生成伪随机占位值；新证据链不能把这些值标成ERA5事实，正式历史链必须只保留归档实值及其等值别名。
- 修正后真实Riyadh历史高温仍返回概率0.1126；运行图包含27个归档输入指标、27条PROVIDES/USED_BY/HAS_ATTRIBUTION和1条有真实输入支撑的机制相容边。旧历史记录的机制节点保留一般知识，但个例得分、置信度和相容边全部隐藏。
- 前端关键投影不需要改变后端图谱合同：规则 `USES` 与机制 `CONSISTENT_WITH` 引用的指标必须保留，其余模型输入按 `HAS_ATTRIBUTION.details.contribution` 的绝对值排序取前8；无贡献值排在有效Tree SHAP之后。完整节点和边仍保存在页面内存中，可随时切回完整证据图。

## P0 credibility findings

- 当前所有预测都调用identity `calibrate()`，`calibratedProbability`与原始模型输出相同；历史页仍称其为“校准后概率”，与领域词汇中“校准必须从独立验证资料拟合”的定义冲突。
- 历史HGB和实时API兼容HGB的 `uncertainty` 都由 `0.35 - 0.4 * abs(p-0.5)` 手工生成，只反映分数离0.5多远，不是误差、置信区间或模型方差；必须改名为启发式判别度并保留方法元数据。
- 监测快照目前是数据库优先，但缓存未命中时由浏览器直接请求Open-Meteo/CMA/Tomorrow.io，再通过无鉴权POST把任意JSON写回后端；这不是后端监测采集，页面未打开时也不会产生新快照。
- 助手在Supabase不可用时走关键词模板；模板仍声称概率经过校准、模型是多模型集成、使用ECMWF/GFS，并包含固定吉赞山洪案例与阈值，均可能与当前预测不符。
- 助手把LLM/模板文本经简单粗体正则后交给 `dangerouslySetInnerHTML`，非粗体HTML不会被清理，真实LLM接入后存在内容注入风险。
- 监测后端化采用“后端保存第三方原始响应快照、前端只做既有展示转换”的最小迁移：既避免浏览器持有API密钥和任意写快照，又不在本轮重复实现一套前后端指标映射。Open-Meteo始终可用；CMA/Tomorrow.io配置状态由后端返回。
