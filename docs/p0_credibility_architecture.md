# P0可信度与监测边界

## 1. 模型输出语义

系统当前没有使用独立验证资料拟合的Platt或Isotonic校准制品。因此模型的0到1输出不称为“校准概率”：

- `uncalibrated_event_score`：针对归档提供事件标签的未校准模型事件分数；
- `uncalibrated_proxy_event_score`：针对规则或教师代理标签的未校准代理事件分数；
- `calibrated_hazard_probability`：只保留给未来真正加载校准制品的输出。

API使用`decisionScore`作为风险政策实际消费的数值，并同时返回`scoreSemantics`、`calibrationMethod`和`isCalibrated`。旧SQLite载荷中的`calibratedProbability`在读取时无损映射为`decisionScore`，不会修改历史预测数值。

模型原有的概率间隔启发式改为`ambiguity`，方法固定声明为`heuristic_probability_margin`。它只表示分数接近决策中点的程度，页面和助手不得用±、误差、置信区间或统计不确定性描述。

## 2. 后端监测采集

浏览器不再直接请求Open-Meteo、Mirror Earth或Tomorrow.io，也不再向后端提交任意监测JSON。正式链路为：

```text
后端六小时调度器 / 手动刷新API
  -> 第三方来源请求
  -> 八个区域覆盖校验
  -> 不可变monitor_data_snapshots记录
  -> 前端GET当前时段快照
  -> 前端展示转换
```

后端启动时默认启用六小时调度器，可通过`MAZU_MONITOR_SCHEDULER_ENABLED=false`关闭。调度器启动或服务重启时先检查当前时段快照，不重复请求；同一进程内按来源加锁，避免调度与页面刷新同时回源。CMA和Tomorrow.io密钥只从后端环境变量`MIRROR_EARTH_API_KEY`与`TOMORROW_IO_API_KEY`读取。

监测API：

- `GET /api/v1/monitor/sources`：返回来源是否已在后端配置；
- `GET /api/v1/monitor/snapshots/{source}`：读取当前UTC六小时时段快照；
- `POST /api/v1/monitor/snapshots/{source}/refresh`：由后端强制重新采集并保存新快照。

旧`POST /api/v1/monitor/snapshots`任意写入口和静态`GET /api/v1/monitor/regions`已移除。

## 3. 助手可信边界

助手上下文只包含当前预测实际保存的分数语义、校准状态、启发式模糊度、模型版本、数据层级、来源、Tree SHAP摘要、命中规则、机制名称和历史案例。模板不再生成固定阈值、固定案例或虚构模型组合。

每条助手回答显示`LLM解释`、`本地模板`或`系统提示`来源。LLM与模板文本均按普通React文本节点渲染，只支持受控的粗体分段，不解释输入HTML。
