---
description: 项目部署完整流程指南
---

# Smart Water 项目部署流程

> **部署场景**: 将项目部署到远程服务器，使用服务器上已有的 vLLM 本地大模型，不使用任何在线 API。

## 部署前确认清单

在开始部署前，请先与服务器管理员确认以下信息：

| 确认项 | 示例值 | 你的配置 |
|--------|--------|----------|
| vLLM Chat 模型地址 | `http://localhost:8001` | ________ |
| vLLM Embedding 模型地址 | `http://localhost:8002` | ________ |
| vLLM Reranker 模型地址 | `http://localhost:8003` | ________ |
| Chat 模型名称 | `qwen3:32b` 或 `/models/Qwen3-32B` | ________ |
| Embedding 模型名称 | `Qwen3-Embedding-8B` | ________ |
| Reranker 模型名称 | `Qwen3-Reranker-8B` | ________ |

验证 vLLM 服务是否可用：
```bash
# 在服务器上执行
curl http://localhost:8001/v1/models
curl http://localhost:8002/v1/models
curl http://localhost:8003/v1/models
```

## 快速部署步骤（TL;DR）

```bash
# 1. 验证服务器 vLLM 服务可用
curl http://localhost:8001/v1/models

# 2. 克隆/上传项目代码

# 3. 配置环境
cp .env.template .env
cp examples/config-vllm-local.yaml saves/config/base.yaml
# 编辑 base.yaml 确认模型名称与服务器一致

# 4. 启动服务
docker compose up --build -d

# 5. 访问系统
# 前端: http://localhost:5173
# API:  http://localhost:5050/docs
```

---

## 1. 系统要求

### 必需软件
- **Docker Desktop** (Windows/macOS) 或 **Docker Engine** (Linux)
  - 版本要求: 20.10+
  - 下载: https://www.docker.com/products/docker-desktop
- **Docker Compose** v2.0+



## 1.5 vLLM 本地大模型部署（服务器 GPU 环境）

如果使用服务器本地部署的 vLLM 大模型，需要先启动 vLLM 服务。

### 1.5.1 vLLM 服务架构

本项目需要启动 **3 个 vLLM 服务**：

| 服务类型 | 端口 | 模型示例 | 用途 |
|---------|------|---------|------|
| Chat 模型 | 8001 | Qwen3-32B | 对话生成 |
| Embedding 模型 | 8002 | Qwen3-Embedding-0.6B | 文本向量化 |
| Reranker 模型 | 8003 | Qwen3-Reranker-0.6B | 检索结果重排序 |

### 1.手动启动 vLLM 服务

```bash
docker run --name qwen3_32b \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e VLLM_WORKER_MULTIPROC_METHOD=spawn \
  -e VLLM_ATTENTION_BACKEND=XFORMERS \
  -v /data/Qwen3-32B:/models/Qwen3-32B \
  -p 8001:8000 \
  --shm-size=200g \
  --ipc=host \
  --gpus all \
  --restart unless-stopped \
  vllm/vllm-openai:v0.10.2 \
  --model /models/Qwen3-32B \
  --tensor-parallel-size 8 \
  --gpu-memory-utilization 0.5 \
  --dtype float16 \
  --host 0.0.0.0 \
  --port 8000 \
  --max-model-len 15000


docker run --name qwen3_Rerank --gpus all -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True -e VLLM_WORKER_MULTIPROC_METHOD=spawn -e VLLM_ATTENTION_BACKEND=XFORMERS -v /data/Qwen3_Rerank:/models/Qwen3_Rerank -p 8003:8000 --shm-size=100g --ipc=host --restart unless-stopped vllm/vllm-openai:v0.10.2 --model /models/Qwen3_Rerank --gpu-memory-utilization 0.5 --tensor-parallel-size 8 --runner pooling --host 0.0.0.0 --port 8000 --max-model-len 20480

docker run --name qwen3_ embedding --gpus all -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True -e VLLM_WORKER_MULTIPROC_METHOD=spawn -e VLLM_ATTENTION_BACKEND=XFORMERS -v /data/Qwen3_Embedding:/models/Qwen3_Embedding -p 8002:8000 --shm-size=100g --ipc=host --restart unless-stopped vllm/vllm-openai:v0.10.2 --model /models/Qwen3_Embedding --tensor-parallel-size 8 --task embed --host 0.0.0.0 --port 8000 --gpu-memory-utilization 0.5 --max-model-len 12288
```

### 2.验证 vLLM 服务
```bash
# 检查 Chat 模型
curl http://localhost:8001/v1/models

# 测试对话
curl http://localhost:8001/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model": "qwen3:32b", "messages": [{"role": "user", "content": "你好"}]}'

# 检查 Embedding 模型
curl http://localhost:8002/v1/models
```

### 配置项目使用 vLLM（关键步骤）

**步骤一：复制 vLLM 配置模板**
```bash
# 在服务器项目目录执行
cp examples/config-vllm-local.yaml saves/config/base.yaml
```

**步骤二：根据服务器实际情况修改** `saves/config/base.yaml`：
```yaml
# 使用服务器本地 vLLM 模型
default_model: vllm//models/Qwen3-32B   # 根据服务器实际模型名称修改
fast_model: vllm//models/Qwen3-32B
embed_model: vllm/Qwen3_Embedding
reranker: vllm/Qwen3_Rerank
enable_reranker: true
```

**步骤三：确认模型配置端口**
检查 `src/config/static/models.yaml` 中的 vLLM 端口配置：
```yaml
vllm:
  base_url: http://localhost:8001/v1    # Chat 模型端口
  
# Embedding 模型
vllm/Qwen3_Embedding:
  base_url: http://localhost:8002/v1/embeddings
  
# Reranker 模型  
vllm/Qwen3_Rerank:
  base_url: http://localhost:8003/v1/rerank
```

> 💡 **提示**: 如果服务器 vLLM 使用的端口不同，需要修改 `models.yaml` 中的端口号

### 1.5.5 Docker 容器访问 vLLM 服务

如果主服务运行在 Docker 中，需要确保容器能访问宿主机的 vLLM 服务：

**方式一：设置 HOST_IP 环境变量**
在 `.env` 文件中添加：
```env
# 宿主机 IP 地址（vLLM 服务所在地址）
HOST_IP=192.168.1.100
```

**方式二：修改模型配置 base_url**
在 `src/config/static/models.yaml` 中修改 vLLM 的 base_url：
```yaml
vllm:
  base_url: http://host.docker.internal:8001/v1
```

> 💡 **提示**: `host.docker.internal` 在 Docker Desktop 中可直接使用，Linux 需添加 `--add-host=host.docker.internal:host-gateway`

---

## 2. 环境配置

### 2.1 复制环境变量模板
```powershell
# Windows PowerShell
Copy-Item .env.template .env
```

```bash
# Linux/macOS
cp .env.template .env
```

### 2.2 编辑 `.env` 文件配置（纯本地模式）

> ⚠️ **重要**: 使用本地 vLLM 模型时，**无需配置任何在线 API Key**！

```env
# ========== 本地模型配置（无需 API Key）==========
# 所有在线 API Key 留空即可
SILICONFLOW_API_KEY=
OPENAI_API_KEY=
ZHIPUAI_API_KEY=
DASHSCOPE_API_KEY=
DEEPSEEK_API_KEY=

# ========== 超级管理员账户 ==========
YUXI_SUPER_ADMIN_NAME=admin
YUXI_SUPER_ADMIN_PASSWORD=your_secure_password

# ========== 数据库配置（使用 Docker 内置服务）==========
# 使用 Docker Compose 内置的 Neo4j，无需修改
NEO4J_URI=bolt://graph:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=0123456789

# ========== 模型目录（可选）==========
MODEL_DIR=./models
SAVE_DIR=./saves
```

---

## 3. 部署命令

### 直接使用 Docker Compose
```bash
# 基础部署（核心服务）
docker compose up --build -d

# 完整部署（包含 GPU 服务，如mineru服务）
docker compose --profile all up --build -d

# 停止服务
docker compose down

# 查看日志
docker compose logs -f --tail=100
```

---

## 4. 服务架构

项目包含以下 Docker 服务:

| 服务名 | 描述 | 端口 | 依赖 |
|--------|------|------|------|
| **api** | 后端 API 服务 (FastAPI) | 5050 | milvus, minio |
| **web** | 前端服务 (Vue3 + Vite) | 5173 | api |
| **graph** | 知识图谱数据库 (Neo4j) | 7474, 7687 | - |
| **milvus** | 向量数据库 | 19530, 9091 | etcd, minio |
| **etcd** | Milvus 元数据存储 | - | - |
| **minio** | 对象存储 | 9000, 9001 | - |
| **mineru** | GPU OCR 服务 (可选) | 30000 | NVIDIA GPU |
| **paddlex** | GPU 文档处理 (可选) | 8080 | NVIDIA GPU |

---

## 5. 访问地址

部署成功后可访问以下服务:

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5173 |
| API 文档 (Swagger) | http://localhost:5050/docs |
| Neo4j 浏览器 | http://localhost:7474 |
| MinIO 控制台 | http://localhost:9001 |
| Milvus 健康检查 | http://localhost:9091/healthz |

---

## 6. 常见问题排查

### 6.1 首次启动慢
- 首次启动需要下载 Docker 镜像和初始化数据库
- 预计耗时: 5-10 分钟
- 使用 `.\deploy.ps1 status` 或 `./deploy.sh status` 检查服务状态

### 6.2 服务健康检查失败
```bash
# 查看具体服务日志
docker compose logs api
docker compose logs milvus
docker compose logs graph
```

### 6.3 端口冲突
检查是否有其他服务占用了以下端口: `5050`, `5173`, `7474`, `7687`, `9000`, `9001`, `19530`

```powershell
# Windows 检查端口占用
netstat -ano | findstr :5050
```

```bash
# Linux/macOS 检查端口占用
lsof -i :5050
```

### 6.4 GPU 服务启动失败
确保已安装 NVIDIA 驱动和 nvidia-container-toolkit:
```bash
# 验证 NVIDIA 支持
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

### 6.5 内存不足
减少同时运行的服务，或增加 Docker Desktop 的内存限制:
- Windows/macOS: 在 Docker Desktop Settings > Resources 中调整

---

## 7. 数据持久化

数据卷位于 `docker/volumes/` 目录:

| 目录 | 说明 |
|------|------|
| `docker/volumes/neo4j/` | Neo4j 数据和日志 |
| `docker/volumes/milvus/` | Milvus 向量数据 |
| `docker/volumes/milvus/minio/` | MinIO 对象存储 |
| `docker/volumes/paddlex/` | PaddleX 模型缓存 |

> ⚠️ **警告**: 运行 `clean` 命令会永久删除以上所有数据！

---

## 8. 生产环境部署建议

1. **使用外部数据库**: 配置 `.env` 使用外部 Neo4j、MySQL
2. **配置反向代理**: 使用 Nginx 做负载均衡和 HTTPS
3. **资源限制**: 在 `docker-compose.yml` 中添加 `deploy.resources.limits`
4. **日志管理**: 配置日志轮转，避免磁盘占用过高
5. **备份策略**: 定期备份 `docker/volumes/` 目录

---

## 9. 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker compose up --build -d

```
