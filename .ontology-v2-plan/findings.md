# 解释证据图谱 2.0 审查发现

- 手工图中13条边错误声明 `eligible_for_causal_explanation=true`：
  7条为待边级审核的手工机制映射，6条未核验原始论文措辞。
- SQLite运行库中有1481个 `ExtremeWeatherState` 实例，但其
  `derivedFromIndicator` 边为0。
- `applicableUnder` 的本体值域为 `SpatialContext`，构图实际连接
  `SeasonalContext`。
- SHACL文件没有在物化或构图时执行；现有测试只检查文本关键词。
- 前端手工图与本体/SQLite图使用不同节点、关系和机制词表。
- 山洪、热浪、沙尘的解释目标混用了极端气象状态与灾害有利状态。
- `Orography` 同时承载高程和坡度，但CF映射仅对应 `surface_altitude`。
- 当前SQLite本体已是1.6.0，最近统计构建仍固定于1.5.0；服务未阻止跨版本混用。
