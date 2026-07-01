# 第一周验证说明

## 验证目标

第一周验证以下链路：

```text
mock insight_payload
-> graph_payload
-> 前端 IndustryGraphView
-> Neo4j 可选入库
```

## 后端测试

```powershell
cd D:\AAA_Favio_2026\AI_exploring\DigitalChina\Insight-front-kg\kg-service
python -m pytest -q
```

通过标准：

- 图谱模块测试通过。
- API 测试通过。
- mock 数据能生成 `company_edges`、`profile_edges`、`evidence_chunks`。

## 前端构建

```powershell
cd D:\AAA_Favio_2026\AI_exploring\DigitalChina\Insight-front-kg\frontend
npm run build
```

通过标准：

- 构建无 TypeScript 错误。
- 页面可访问 `http://localhost:3001`。
- 点击“加载 mock”后能解析样例。
- 点击“生成图谱”后能看到图谱。

## Neo4j 验证

```powershell
cd D:\AAA_Favio_2026\AI_exploring\DigitalChina\Insight-front-kg
docker compose -f docker-compose.neo4j.yml up -d
```

然后配置：

```text
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
GRAPH_AUTO_PERSIST=true
```

点击前端“生成并入库”，观察 `persistence_meta.status`。

## 验证记录模板

```text
验证日期：
验证人：
样例：新能源汽车

KG 服务：
- /health 是否正常：
- /api/graph/build 是否正常：
- graph_nodes 数量：
- company_edges 数量：
- profile_edges 数量：
- evidence_chunks 数量：

前端：
- mock 是否加载：
- 图谱是否显示：
- 公司节点是否可点击：
- 画像关系是否展开：
- 边证据是否显示：

Neo4j：
- 是否启动：
- persistence_meta.status：
- 失败原因：

问题：
- 后端字段缺口：
- 图谱规则问题：
- 前端展示问题：
```
