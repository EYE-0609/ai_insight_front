# 后端 Agent 组对接协议

## 对接方式

第一版使用 REST JSON。

```text
后端 Agent 组 -> insight_payload -> Insight-front-kg KG 服务 -> graph_payload
```

KG 服务默认地址：

```text
http://localhost:8008
```

## 接口

### GET /health

返回服务状态。

### POST /api/graph/build

输入：

```json
{
  "insight_payload": {}
}
```

输出：

```json
{
  "graph_nodes": [],
  "relation_candidates": [],
  "graph_edges": [],
  "company_edges": [],
  "profile_edges": [],
  "evidence_chunks": [],
  "persistence_meta": {}
}
```

该接口只生成图谱，不写 Neo4j。

### POST /api/graph/persist

输入：

```json
{
  "graph_payload": {}
}
```

输出：带 `persistence_meta` 的 `graph_payload`。

### POST /api/graph/build-and-persist

输入：

```json
{
  "insight_payload": {}
}
```

输出：生成后的 `graph_payload`，并尝试写入 Neo4j。

## insight_payload 必需字段

后端 Agent 组至少需要提供：

```text
task_profile.industry

chain_skeleton[].segment
chain_skeleton[].subsegments
chain_skeleton[].evidence_sources

segment_companies[].segment
segment_companies[].companies[].company_name
segment_companies[].companies[].reason
segment_companies[].companies[].evidence_sources

company_cards[].company_name
company_cards[].segment
company_cards[].subsegment
company_cards[].business_lines
company_cards[].product_lines
company_cards[].core_technologies
company_cards[].field_evidence
company_cards[].relationship_clues
company_cards[].key_sources
company_cards[].evidence_excerpts

source_index[].title
source_index[].url
source_index[].snippet
source_index[].source_grade
```

## 公司关系线索格式

`relationship_clues` 建议使用结构化格式：

```text
目标企业=比亚迪；关系层级=industry_template；关系名称=动力电池供应；方向=本企业->目标企业；证据=宁德时代为比亚迪提供动力电池相关产品。；来源=https://example.com/catl-byd；来源等级=A；解释=宁德时代向比亚迪提供动力电池相关产品
```

如果只给自然语言，公司间关系边可能为空，前端会显示“暂无可视化公司关系”。

## 字段级证据

`field_evidence` 用来支撑画像关系边，建议格式：

```json
{
  "business_lines": [
    {
      "value": "动力电池业务",
      "evidence_text": "宁德时代主营动力电池业务。",
      "source_url": "https://example.com/catl-report",
      "source_title": "宁德时代年度报告",
      "source_grade": "A"
    }
  ]
}
```

## 前端展示条件

- `company_edges` 非空：显示公司关系图。
- `company_edges` 为空：显示空状态。
- `profile_edges` 非空：点击公司节点后展示业务线、产品线、核心技术关系。
- `persistence_meta.status` 展示 Neo4j 入库状态。
