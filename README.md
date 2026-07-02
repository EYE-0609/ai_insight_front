# Insight-front-kg

独立运行的知识图谱和图谱前端工作台。

目标链路：

```text
后端 Agent 组输出 insight_payload
-> KG 服务生成 graph_payload
-> 可选写入 Neo4j
-> 前端图谱结果区展示
```

## 目录结构

```text
frontend/     Next.js 图谱工作台
kg-service/   FastAPI 图谱服务
samples/      mock insight_payload 样例
docs/         接口协议和联调说明
```

## 第一周需求

第一周执行清单见：

```text
docs/第一周需求列表.md
```

## 启动 KG 服务

```powershell
cd D:\AAA_Favio_2026\AI_exploring\DigitalChina\Insight-front-kg\kg-service
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8008 --reload
```

健康检查：

```text
http://localhost:8008/health
```

## 启动前端

```powershell
cd D:\AAA_Favio_2026\AI_exploring\DigitalChina\Insight-front-kg\frontend
npm install
npm run dev
```

访问：

```text
http://localhost:3001
```

## Neo4j 可选入库

```powershell
cd D:\AAA_Favio_2026\AI_exploring\DigitalChina\Insight-front-kg
docker compose -f docker-compose.neo4j.yml up -d
```

环境变量：

```text
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
GRAPH_AUTO_PERSIST=true
```

Neo4j Browser:

```text
http://localhost:7474
```

## 第一周验收

- mock `insight_payload` 能生成 `graph_payload`。
- `company_edges.length > 0`。
- `profile_edges.length > 0`。
- 前端能显示公司关系图。
- 点击公司节点能展开画像关系。
- 点击关系边能看到证据和来源。
- Neo4j 成功、跳过或失败都能通过 `persistence_meta` 记录。

## 当前已验证

在 `industry_insight` conda 环境中已验证：

```text
kg-service: python -m pytest -q
结果：34 passed

mock 样例生成结果：
graph_nodes=43
company_edges=2
profile_edges=18
evidence_chunks=27

frontend: npm run build
结果：Next.js production build passed
```

本地服务默认地址：

```text
KG 服务：http://localhost:8008
前端：http://localhost:3001
Neo4j Browser：http://localhost:7474
```
