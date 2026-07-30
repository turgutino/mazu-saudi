# 文献证据与机制断言构建

## 1. 产物与科学边界

该流水线针对一版已经冻结的全球统计图谱，形成独立的文献增强运行：

```text
LaggedAssociationAssertion
  ← interpretsAssociation
MechanismApplicabilityAssertion
  → compatibleWithMechanism → WeatherMechanism
  → supportedByLiteratureEvidence → LiteratureEvidenceRecord
  → groundedByPublication → ScholarlyPublication
```

它不会修改原 `kg_builds/kg_nodes/kg_edges/kg_evidence`，也不会改变统计关系的验证等级。
文献只支持状态组合与机制的物理相容性，不证明原统计关系的精确季节、滞后、Lift、沙特
迁移有效性或生产预测价值。自动生成的机制断言固定为：

```text
review_status = automatic_candidate_human_review_required
eligible_for_causal_explanation = false
eligible_for_prediction_experiment = false
eligible_for_production_prediction = false
```

## 2. 文献清单

版本化清单位于 `ontology/literature_sources.json`，首批包含9篇中东或沙特相关研究：

- Active Red Sea Trough与极端降水；
- 位涡、IVT与中东极端降水；
- 2023年中东大气河及沙特西部地形增强；
- 红海和地形对沙特降雨的敏感性试验；
- 沙特降雨极值、深对流和地形背景；
- 沙特极端高温与大尺度环流；
- 沙特夏季气温、环流和海温背景；
- 夏季Shamal风与沙尘；
- Zagros山脉与夏季Shamal风。

脚本只访问清单中明确声明的 HTTPS 地址，不进行开放式网络搜索或自动追踪网页链接。
新增文献必须先更新清单、限定允许映射的受控机制，并经过代码审核。

## 3. 文本快照

自动获取出版物页面：

```bash
PYTHONPATH=src conda run -n ml python scripts/build_literature_evidence.py \
  --fetch \
  --dry-run
```

`--fetch` 表示在检查或构图前尝试获取清单地址，不代表绕过出版商访问限制。建议首次获取
始终与 `--dry-run` 一起使用，这样只检查下载结果，不调用大模型。如果省略
`--dry-run` 且没有任何可用快照，脚本会以结构化 JSON 输出每篇文献的具体下载错误和
人工保存目录，而不是只抛出笼统的“没有快照”异常。

出版商可能返回 `403`、`429`，或只提供摘要。脚本不会绕过访问控制或付费墙；失败会逐篇
记录并继续处理其他来源。此时应通过合法访问方式在浏览器中保存可访问的 HTML、TXT 或
PDF，并按 `source_id` 命名后放入：

```text
runtime/literature/documents/
  devries2013_arst.html
  francis2024_ar_rapids.pdf
  ...
```

保存的文件不进入 Git。每次运行记录原文件 SHA-256、规范化文本 SHA-256、媒体类型和
本地路径。PDF解析需要可选的 `pypdf`，或者系统已安装 `pdftotext`；也可以优先保存
出版商 HTML。

运行前检查可用快照和候选统计关系：

```bash
PYTHONPATH=src conda run -n ml python scripts/build_literature_evidence.py \
  --dry-run
```

当前默认读取最近一版统计图中的所有：

```text
relation_role = lagged_cross_indicator
validation_stage ∈ {
  statistical_evidence,
  candidate_for_saudi_evaluation
}
```

状态持续、测量一致性、同日共现等诊断关系不交给大模型解释。

## 4. 智谱调用

实现遵循智谱官方聊天补全和结构化输出接口：

- `POST https://open.bigmodel.cn/api/paas/v4/chat/completions`
- 默认模型 `glm-5.2`
- `response_format={"type":"json_object"}`
- API Key只从环境变量读取
- 对429和服务端错误进行有限重试
- 按提示词内容寻址缓存，避免重复付费调用

不要把 Key 粘贴进代码、清单、文档、命令参数或聊天记录。zsh中可以静默输入：

```bash
read -s "ZHIPU_API_KEY?智谱 API Key: "
export ZHIPU_API_KEY
echo
```

正式执行：

```bash
PYTHONPATH=src conda run -n ml python scripts/build_literature_evidence.py \
  --model glm-5.2
```

完成后清除当前 shell 中的变量：

```bash
unset ZHIPU_API_KEY
```

如需选择特定统计构建，可增加：

```text
--build-id kg-...
```

## 5. 确定性质量门

模型只提出候选 JSON。入库前必须同时满足：

1. `candidate_key` 属于本次冻结的跨指标滞后关系列表；
2. `mechanism_iri` 属于本体受控机制，并位于该篇文献的允许机制白名单；
3. `evidence_quote` 经空白规范化后仍是输入文本块的连续精确子串；
4. 证据记录保存实际字符块定位、文本块 SHA 和模型响应 SHA；
5. 只有 `stance=supports` 的记录生成机制适用性断言；
6. 限制性和反向证据保留为文献证据记录，但不生成正向机制断言；
7. 文献断言不继承统计关系的预测实验资格。

页面 `/knowledge-graph` 默认仍显示统计关系。切换“审计结构”并打开“证据链”，可以沿着
统计断言查看机理断言、原文证据、出版物和文献增强运行。

## 6. SQLite与审计文件

文献层写入同一个SQLite文件中的独立表：

| 表 | 内容 |
|---|---|
| `kg_literature_runs` | 统计构建、本体、文献清单、模型、提示词和计数 |
| `kg_literature_nodes` | 增强运行、出版物、原文证据和机制适用性断言 |
| `kg_literature_edges` | 与统计断言、状态、环境、机制、证据及来源的连接 |

运行审计写入：

```text
runtime/literature/runs/<run_id>.json
```

响应缓存位于：

```text
runtime/literature/response_cache/
```

缓存和审计文件不保存 API Key。它们保留模型输出和原文证据，仍应按研究数据资产管理，
不要直接公开分发受版权限制的全文快照。
