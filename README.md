# SonarQube AI Auto-Fix Agent

基于 LangGraph Supervisor 模式的 AI 自动修复代理，自动读取 SonarQube 检测到的 Java 代码问题，利用 LLM + RAG 生成修复补丁，验证修复结果，并自动创建 GitHub Pull Request。

---

## 目录

- [项目概述](#项目概述)
- [架构设计](#架构设计)
- [环境要求](#环境要求)
- [安装与启动](#安装与启动)
- [配置说明](#配置说明)
- [使用方法](#使用方法)
- [工作原理](#工作原理)
- [已知限制](#已知限制)
- [开发与测试](#开发与测试)

---

## 项目概述

本项目实现了一个完整的 AI 代码修复流水线：

1. **自动读取** SonarQube 项目中未解决的 Java 代码问题
2. **检索增强生成（RAG）** — 从 pgvector 向量数据库中召回最相关的 SonarQube 规则文档，辅助 LLM 理解修复方向
3. **LLM 生成补丁** — 使用 LiteLLM 统一接口调用 Claude / Azure GPT-4o 等模型，以 unified diff 格式输出代码修复
4. **自动验证** — 将补丁应用到本地仓库后，回调 SonarQube API 验证问题是否已解决
5. **自动提 PR** — 修复通过验证后，自动推送分支并在 GitHub 上创建 Pull Request

支持断点续跑：每次运行生成唯一 `thread_id`，中断后可凭此 ID 恢复执行。

---

## 架构设计

```
main.py (CLI)
    └── orchestrator/supervisor.py  ← LangGraph StateGraph (Supervisor)
            ├── issue_reader/       ← 从 SonarQube 拉取未解决问题
            ├── remediation/        ← RAG 检索 + LLM 生成 unified diff
            ├── validation/         ← 应用补丁 + 回调 SonarQube 验证
            └── github/             ← 推送分支 + 创建 Pull Request
```

**数据流（LangGraph AgentState）：**

```
START → router → issue_reader → router → remediator → router
     → validator → router → (remediator 最多 max_rounds 轮)
     → github_agent → END
```

**双数据库设计：**

| 数据库                   | 用途                       | 位置                   |
| --------------------- | ------------------------ | -------------------- |
| SQLite                | LangGraph 状态检查点（支持断点续跑）  | `runs/agent_runs.db` |
| PostgreSQL + pgvector | SonarQube 规则向量索引（RAG 检索） | Docker 容器 / 外部服务     |

---

## 环境要求

- Python 3.11+
- Docker（用于启动 PostgreSQL + pgvector）
- 可访问的 SonarQube 实例（含 API Token）
- GitHub Token（需要 `repo` 权限）
- Anthropic API Key 或 Azure OpenAI 配置

---

## 安装与启动

### 1. 克隆仓库并安装依赖

```bash
git clone <your-repo-url>
cd auto-sonarqube-reports-fix

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入各项凭据（详见「配置说明」）
```

### 3. 启动 PostgreSQL + pgvector

```bash
# 首次启动会自动执行 docker/init.sql，创建 pgvector 扩展
docker compose up -d

# 确认容器健康
docker compose ps
```

### 4. 初始化 RAG 向量索引（首次运行前必须执行）

```bash
# 从 SonarQube 拉取全部 Java 规则并写入 pgvector
python -m rag.ingest --sonar-url http://your-sonar-host --token your_token
```

此步骤通常需要 2–5 分钟，取决于规则数量（一般 600+ 条）。完成后无需重复执行，除非 SonarQube 规则库有重大更新。

---

## 配置说明

复制 `.env.example` 为 `.env` 并填写以下字段：

```env
# SonarQube 连接
SONAR_URL=http://sonar.internal          # SonarQube 服务地址
SONAR_TOKEN=your_sonarqube_token         # 用户 Token（需有项目读权限）

# LLM 配置（二选一）
LLM_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-your-key

# Azure OpenAI 替代方案
# LLM_MODEL=azure/gpt-4o
# AZURE_API_KEY=your-azure-key
# AZURE_API_BASE=https://your-instance.openai.azure.com
# AZURE_API_VERSION=2024-02-01

# Embedding 配置
OPENAI_API_KEY=sk-your-key               # 使用 OpenAI embedding 时必填
EMBEDDING_MODEL=openai                   # 或 local（使用 all-MiniLM-L6-v2 离线模型）

# PostgreSQL + pgvector
PGVECTOR_DSN=postgresql://sonarrule:sonarrule@localhost:5432/sonarrule_rag

# GitHub
GITHUB_TOKEN=ghp_your-token             # 需要 repo 权限
GITHUB_REPO=myorg/payment-service        # 格式：org/repo

# 运行参数
MAX_ROUNDS=3                             # 最大修复轮次（超过后强制提 PR）
REPO_LOCAL_PATH=/path/to/local/cloned/repo  # 本地已克隆的目标仓库路径
```

**`EMBEDDING_MODEL` 选项说明：**

| 值        | 模型                     | 维度    | 说明                       |
| -------- | ---------------------- | ----- | ------------------------ |
| `openai` | text-embedding-3-small | 1536d | 需要 `OPENAI_API_KEY`，效果更好 |
| `local`  | all-MiniLM-L6-v2       | 384d  | 完全离线，无需 API Key          |

---

## 使用方法

### 启动新的修复任务

```bash
python main.py run \
  --project com.example:payment-service \
  --branch main \
  --github-repo myorg/payment-service \
  --max-rounds 3
```

输出示例：

```
[agent] thread_id: a1b2c3d4-...  (use --thread-id a1b2c3d4-... to resume)
[agent] Starting run — thread_id=a1b2c3d4-...
[agent] Done. PR: https://github.com/myorg/payment-service/pull/42
```

### 恢复中断的任务

```bash
python main.py resume --thread-id a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 命令行参数说明

| 参数              | 说明                    | 默认值    |
| --------------- | --------------------- | ------ |
| `--project`     | SonarQube 项目 Key      | 必填     |
| `--branch`      | 目标分支                  | `main` |
| `--max-rounds`  | 最大修复轮次                | `3`    |
| `--github-repo` | GitHub 仓库（`org/repo`） | 必填     |
| `--thread-id`   | 指定 thread ID（用于断点续跑）  | 自动生成   |

---

## 工作原理

### Supervisor 路由逻辑

`orchestrator/supervisor.py` 中的 `route()` 函数根据 `AgentState` 当前状态决定下一步执行哪个 Agent：

```
issues 为空 且 issues_fetched=False  →  issue_reader（拉取问题）
issues 为空 且 issues_fetched=True   →  END（无问题，直接结束）
fixes 为空                           →  remediator（生成修复）
validation_result 为 None            →  validator（验证修复）
仍有未解决问题 且 未超过 max_rounds   →  remediator（继续修复）
否则                                 →  github_agent（提 PR）
```

### RAG 检索流程

`rag/retriever.py` 在 Remediation Agent 中被调用：

1. 将 SonarQube 问题的 `rule_id` + `rule_description` 拼接成查询文本
2. 调用 `EmbeddingModel.embed()` 获取向量
3. 在 pgvector 中执行余弦相似度检索，返回 Top-K 规则文档
4. 将检索结果注入 LLM Prompt，提供修复参考

### 断点续跑原理

每次 `supervisor.invoke()` 调用时，LangGraph 通过 `SqliteSaver` 将完整的 `AgentState` 序列化到 `runs/agent_runs.db`。恢复时传入相同 `thread_id`，LangGraph 自动从上次检查点恢复状态，跳过已完成的节点。

---

## 已知限制

- **仅支持 Java 项目** — RAG 向量索引和 issue_reader 均针对 Java 规则设计，其他语言需调整 `rag/ingest.py` 的规则过滤逻辑
- **本地仓库需预先克隆** — `REPO_LOCAL_PATH` 必须指向已克隆好的仓库，Agent 不会自动 clone
- **pgvector 需首次初始化** — 每次重建 Docker 数据卷（`docker compose down -v`）后，需重新执行 `python -m rag.ingest`
- **LLM 生成质量依赖 Prompt** — 对于复杂的多文件修复（如接口变更），当前单文件 diff 策略可能产生不完整的修复
- **SonarQube 扫描延迟** — Validation Agent 依赖 SonarQube 完成扫描后的结果，若 CI 扫描未触发，验证将得到旧数据

---

## 开发与测试

### 运行测试

```bash
# 运行全部单元测试
pytest tests/ -v

# 运行特定模块的测试
pytest tests/test_remediation.py -v
```

所有测试均使用 Mock，无需真实的 SonarQube、PostgreSQL 或 GitHub 连接。`tests/conftest.py` 中预设了所需的环境变量。

### 项目结构

```
.
├── main.py                    # CLI 入口
├── state.py                   # AgentState TypedDict 定义
├── config.py                  # 环境变量读取
├── orchestrator/
│   └── supervisor.py          # LangGraph StateGraph + 路由逻辑
├── agents/
│   ├── issue_reader/          # SonarQube 问题读取
│   ├── remediation/           # RAG + LLM 修复生成
│   ├── validation/            # 补丁验证
│   └── github/                # GitHub PR 创建
├── rag/
│   ├── embeddings.py          # EmbeddingModel（OpenAI / 本地）
│   ├── retriever.py           # pgvector 向量检索
│   └── ingest.py              # 规则库离线初始化脚本
├── db/
│   └── sqlite.py              # LangGraph SQLite 检查点
├── docker/
│   └── init.sql               # PostgreSQL 初始化脚本（启用 pgvector）
├── docker-compose.yml         # PostgreSQL + pgvector 服务定义
├── tests/                     # 单元测试
├── .env.example               # 环境变量模板
└── requirements.txt           # Python 依赖
```

### Docker 常用命令

```bash
# 启动 PostgreSQL
docker compose up -d

# 停止服务（保留数据）
docker compose down

# 彻底清除数据（需重新执行 rag/ingest）
docker compose down -v
```
