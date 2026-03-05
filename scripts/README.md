# 本地大模型配置脚本

本目录包含用于快速配置本地大模型的脚本工具。

## 📝 脚本说明

### Windows 用户

使用 PowerShell 脚本：`setup-ollama.ps1`

```powershell
# 在 PowerShell 中运行
.\scripts\setup-ollama.ps1
```

### Linux/Mac 用户

使用 Bash 脚本：`setup-ollama.sh`

```bash
# 添加执行权限
chmod +x scripts/setup-ollama.sh

# 运行脚本
./scripts/setup-ollama.sh
```

## 🚀 功能特性

这些脚本将帮助您：

1. ✅ 检查 Ollama 安装状态（Linux/Mac 还会自动安装）
2. ✅ 交互式选择要下载的模型
3. ✅ 自动下载聊天模型和 Embedding 模型
4. ✅ 测试模型是否正常工作
5. ✅ 提供配置建议
6. ✅ 检查服务状态

## 📦 可选模型

### 聊天模型

| 模型 | 参数量 | 显存需求 | 适用场景 |
|------|--------|---------|---------|
| qwen2.5:7b | 7B | ~4GB | 推荐，性能均衡 |
| qwen2.5:14b | 14B | ~8GB | 效果更好 |
| llama3.1:8b | 8B | ~5GB | Meta Llama 系列 |
| deepseek-r1:7b | 7B | ~4GB | DeepSeek 推理模型 |

### Embedding 模型

| 模型 | 维度 | 适用场景 |
|------|-----|---------|
| bge-m3 | 1024 | 推荐，中英文混合 |
| nomic-embed-text | 768 | 英文优先 |

## 🔧 手动配置

如果您不想使用脚本，也可以手动配置：

1. 安装 Ollama：https://ollama.com
2. 下载模型：`ollama pull qwen2.5:7b`
3. 修改配置文件 `saves/config/base.yaml`

详细说明请参考：[本地大模型配置指南](../docs/本地大模型配置指南.md)

## ⚠️ 注意事项

- 模型下载需要一定时间，请确保网络稳定
- 不同模型有不同的硬件要求，请根据您的设备选择合适的模型
- Windows 用户可能需要以管理员身份运行脚本
- 如果下载速度慢，可以配置 Hugging Face 镜像

## 🐛 常见问题

### 下载速度慢？

配置国内镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### PowerShell 脚本无法运行？

可能需要设置执行策略：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Ollama 服务未运行？

```bash
# 启动 Ollama 服务
ollama serve
```

## 📚 更多资源

- [完整配置指南](../docs/本地大模型配置指南.md)
- [Ollama 官方文档](https://github.com/ollama/ollama)
- [模型库](https://ollama.com/library)
