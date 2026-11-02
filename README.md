# 智数问答 · Data-Agent

企业级 NL2SQL 智能数据分析平台。把自然语言问题翻译成可执行的 SQL，在数仓上跑出结果再交回大模型组织成答案。

## 架构

查询链路是一条 LangGraph `StateGraph`，12 个节点：

```
用户提问
   │
   ├─ 关键词抽取 ──┬─ 字段召回（Qdrant 向量）
   │               ├─ 指标召回（Qdrant 向量）
   │               └─ 枚举值召回（ES 倒排）      ← 三路并行召回
   │                        │
   │                 合并检索上下文
   │                        │
   │              过滤表 → 过滤指标 → 补上下文
   │                        │
   │                   生成 SQL
   │                        │
   │              EXPLAIN 校验 ──失败──→ 错误回灌，最小修复 ──┐
   │                        │                              │
   │                        └──────────←───────────────────┘
   │                        │
   └──────────────────── 执行 SQL → 返回结果
```

- **元数据知识库**：MySQL 存表 / 字段 / 指标的结构化元信息，Qdrant 存字段与指标的向量表示，ES 存枚举值倒排索引。三套存储各管一类召回，避免单一向量检索在精确匹配上的短板。
- **SQL 校验**：不直接执行生成的 SQL，先走 `EXPLAIN` 让数据库解析一遍，语法或表名有错就把报错回灌给模型做最小修复。

## 技术栈

| 层级 | 选型 |
|---|---|
| Web | FastAPI、Pydantic |
| 编排 | LangGraph 1.0、LangChain 1.2 |
| 向量库 | Qdrant 1.16 |
| 全文检索 | Elasticsearch 8.19 + IK 分词 |
| 元数据库 | MySQL 8.0、SQLAlchemy 2.0 |
| Embedding | BGE-large-zh-v1.5（1024 维），TEI 部署 |
| LLM | qwen3.7-flash |

## 目录

```
app/
├── agent/          LangGraph 图定义与各节点
├── api/            FastAPI 路由与出入参
├── clients/        MySQL / Qdrant / ES / Embedding 客户端
├── models/         各存储的 ORM 与数据结构
├── repositories/   数据访问层
├── services/       元数据构建与查询服务
└── scripts/        元数据知识库构建脚本
conf/               配置文件（app_config.yaml 不入库）
docker/             依赖服务编排、建表 SQL、ES IK 插件
prompts/            各节点的提示词模板
```

## 快速开始

**1. 起依赖服务**

```bash
cd docker
docker compose up -d
```

会拉起 MySQL(3306)、Elasticsearch(9200)、Kibana(5601)、Qdrant(6333)、TEI Embedding(8081)。MySQL 首次启动自动执行 `docker/mysql/*.sql` 建库建表。

**2. 下载 Embedding 模型**

模型权重 1.3G，未入库，需要自行下载到 `docker/embedding/bge-large-zh-v1.5`：

```bash
huggingface-cli download BAAI/bge-large-zh-v1.5 \
  --local-dir docker/embedding/bge-large-zh-v1.5
```

**3. 配置**

```bash
cp conf/app_config.example.yaml conf/app_config.yaml
```

填入自己的 MySQL 密码和 LLM API Key。

**4. 装依赖并启动**

```bash
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

**5. 构建元数据知识库**（首次运行必做）

```bash
uv run python -m app.scripts.build_meta_knowledge
```

**6. 提问**

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "最近三个月销售额最高的十个门店"}'
```
